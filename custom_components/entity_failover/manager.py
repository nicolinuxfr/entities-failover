"""Runtime failover manager."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    Event,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .adapters import (
    CONFIRM_UNSUPPORTED,
    ConfirmationRule,
    DomainAdapter,
    adapter_for_domain,
)
from .const import (
    ATTR_ACTIVE_SOURCE,
    ATTR_AVAILABLE_SOURCES,
    ATTR_DEGRADED,
    ATTR_EXCLUDED_SOURCES,
    ATTR_FAILOVER_ACTIVE,
    ATTR_NOMINAL_SOURCE,
    ATTR_PRIORITY_INDEX,
    ATTR_SOURCES_DESYNCHRONIZED,
    ATTR_STATE_SOURCE,
    COMMAND_CONFIRMATION_TIMEOUT,
    CONF_LEARNING_ENABLED,
    CONF_SOURCES,
    DOMAIN,
    ISSUE_ALL_SOURCES_UNAVAILABLE,
    LEARNING_SAMPLE_COUNT,
)
from .helpers import friendly_name, state_available
from .learning import LearningState, LearningStore
from .model import (
    CommandResult,
    FailoverConfig,
    ManagerDiagnostics,
    SourceHealth,
)

_LOGGER = logging.getLogger(__name__)
UpdateCallback = Callable[[], None]


class FailoverManager:
    """Manage source selection, health and command routing for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: FailoverConfig,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the manager."""

        self.hass = hass
        self.config = config
        self._entry = entry
        self.adapter: DomainAdapter = adapter_for_domain(config.domain)
        self.active_source: str | None = None
        self.state_source: str | None = None
        self.main_entity_id: str | None = None
        self.last_failover: datetime | None = None
        self.last_command_result: CommandResult | None = None
        self._health: dict[str, SourceHealth] = {
            source: SourceHealth(source) for source in config.sources
        }
        self._unsub: list[CALLBACK_TYPE] = []
        self._callbacks: list[UpdateCallback] = []
        self._lock = asyncio.Lock()
        self._unloaded = False
        self._pending_recovery_source: str | None = None
        self._cancel_recovery: CALLBACK_TYPE | None = None
        self._cooldown_unsubs: dict[str, CALLBACK_TYPE] = {}
        self._repairs_issue_active = False
        self._cancel_repairs_timer: CALLBACK_TYPE | None = None
        self._pending_confirmation_rule: ConfirmationRule | None = None
        self._pending_confirmation_data: dict[str, Any] = {}
        self._pending_confirmation_until: datetime | None = None
        self._hidden_sources: set[str] = set()
        self._learning_store = LearningStore(hass, config.unique_id)
        self._learning = LearningState.empty(config.sources)

    @property
    def active_state(self) -> State | None:
        """Return the state source state."""

        source = self.effective_state_source
        if source is None:
            return None
        return self.hass.states.get(source)

    @property
    def effective_state_source(self) -> str | None:
        """Return the source currently used to mirror state."""

        return self.state_source or self.active_source

    @property
    def sources_desynchronized(self) -> bool:
        """Return whether command and state sources currently differ."""

        return (
            self.active_source is not None
            and self.state_source is not None
            and self.state_source != self.active_source
        )

    @property
    def available(self) -> bool:
        """Return whether any source is active."""

        return self.active_source is not None

    @property
    def active_priority_index(self) -> int | None:
        """Return active source priority index."""

        if self.active_source is None:
            return None
        return self.config.sources.index(self.active_source)

    @property
    def degraded(self) -> bool:
        """Return whether the failover entity is degraded."""

        active_index = self.active_priority_index
        return (active_index is not None and active_index > 0) or bool(
            self.excluded_sources
        )

    @property
    def nominal_source(self) -> str | None:
        """Return the source expected by the current selection policy."""

        if not self.config.sources:
            return None
        return self.config.sources[0]

    @property
    def learning_status(self) -> str:
        """Return the current learning lifecycle state."""

        if not self.config.learning_enabled:
            return "inactive"
        completed = [
            source for source in self.config.sources if self._learning.complete(source)
        ]
        if len(completed) == len(self.config.sources):
            return "complete"
        if completed:
            return "partial"
        return "learning"

    @property
    def learning_progress(self) -> dict[str, int]:
        """Return successful sample counts by source."""

        return {
            source: len(self._learning.samples[source])
            for source in self.config.sources
        }

    @property
    def learned_latencies(self) -> dict[str, float]:
        """Return learned median latency by completed source."""

        return {
            source: latency
            for source in self.config.sources
            if (latency := self._learning.median_latency(source)) is not None
        }

    @property
    def learning_pending_sources(self) -> list[str]:
        """Return sources that still need successful samples."""

        return [
            source
            for source in self.config.sources
            if not self._learning.complete(source)
        ]

    @property
    def failover_active(self) -> bool:
        """Return whether routing has moved away from the nominal source."""

        nominal = self.nominal_source
        return nominal is not None and not self._is_source_operational(nominal)

    @property
    def available_sources(self) -> list[str]:
        """Return currently available source ids."""

        return [
            source
            for source in self.config.sources
            if self._is_source_operational(source)
        ]

    @property
    def excluded_sources(self) -> list[str]:
        """Return currently excluded source ids."""

        now = dt_util.utcnow()
        return [
            source
            for source, health in self._health.items()
            if health.excluded_until is not None and health.excluded_until > now
        ]

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes for the main entity."""

        return {
            ATTR_ACTIVE_SOURCE: self.active_source,
            ATTR_STATE_SOURCE: self.effective_state_source,
            ATTR_SOURCES_DESYNCHRONIZED: self.sources_desynchronized,
            ATTR_PRIORITY_INDEX: self.active_priority_index,
            ATTR_NOMINAL_SOURCE: self.nominal_source,
            ATTR_DEGRADED: self.degraded,
            ATTR_FAILOVER_ACTIVE: self.failover_active,
            ATTR_AVAILABLE_SOURCES: self.available_sources,
            ATTR_EXCLUDED_SOURCES: self.excluded_sources,
        }

    async def async_start(self) -> None:
        """Start tracking source states."""

        if self.config.learning_enabled:
            self._learning = await self._learning_store.async_load(self.config.sources)
        else:
            await self._learning_store.async_remove()
        self._hide_sources()
        self._refresh_health()
        self.active_source = self._best_operational_source()
        self.state_source = None
        self._unsub.append(
            async_track_state_change_event(
                self.hass,
                list(self.config.sources),
                self._async_source_state_changed,
            )
        )
        self._handle_repairs_state()
        self._notify()
        _LOGGER.debug(
            "Initialized failover manager for %s with active source %s",
            self.config.entry_id,
            self.active_source,
        )

    async def async_unload(self) -> None:
        """Unload manager resources."""

        self._unloaded = True
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()
        self._callbacks.clear()
        self._cancel_recovery_timer()
        for unsub in self._cooldown_unsubs.values():
            unsub()
        self._cooldown_unsubs.clear()
        if self._cancel_repairs_timer is not None:
            self._cancel_repairs_timer()
            self._cancel_repairs_timer = None
        if self._repairs_issue_active:
            ir.async_delete_issue(self.hass, DOMAIN, self._repairs_issue_id)
            self._repairs_issue_active = False
        self._restore_hidden_sources()

    def async_add_update_listener(self, callback_func: UpdateCallback) -> CALLBACK_TYPE:
        """Register an entity update callback."""

        self._callbacks.append(callback_func)

        @callback
        def _remove() -> None:
            if callback_func in self._callbacks:
                self._callbacks.remove(callback_func)

        return _remove

    @callback
    def _hide_sources(self) -> None:
        """Hide source entities in the entity registry when configured."""

        if not self.config.hide_sources:
            return
        registry = er.async_get(self.hass)
        for source in self.config.sources:
            registry_entry = registry.async_get(source)
            if registry_entry is None or registry_entry.hidden_by is not None:
                continue
            registry.async_update_entity(
                source,
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )
            self._hidden_sources.add(source)

    @callback
    def _restore_hidden_sources(self) -> None:
        """Restore source visibility for entities hidden by this manager."""

        if not self._hidden_sources:
            return
        registry = er.async_get(self.hass)
        for source in self._hidden_sources:
            registry_entry = registry.async_get(source)
            if (
                registry_entry is not None
                and registry_entry.hidden_by == er.RegistryEntryHider.INTEGRATION
            ):
                registry.async_update_entity(source, hidden_by=None)
        self._hidden_sources.clear()

    @callback
    def _notify(self) -> None:
        """Notify attached entities."""

        if self._unloaded:
            return
        for callback_func in list(self._callbacks):
            callback_func()

    @callback
    def _async_source_state_changed(self, event: Event[Any]) -> None:
        """Handle a source state change."""

        entity_id = event.data.get("entity_id")
        if entity_id not in self._health:
            return
        old_active = self.active_source
        self._refresh_health()
        self._select_after_state_change(old_active)
        self._select_state_source_after_state_change(entity_id)
        self._select_state_source_after_recent_confirmation(entity_id)
        self._handle_repairs_state()
        if self.active_source != old_active:
            self._record_failover(old_active, self.active_source)
        self._notify()

    def _refresh_health(self) -> None:
        """Refresh health from Home Assistant state machine."""

        now = dt_util.utcnow()
        for source in self.config.sources:
            state = self.hass.states.get(source)
            health = self._health[source]
            health.exists = state is not None
            health.available = state_available(state)
            if health.excluded_until is not None and health.excluded_until <= now:
                health.excluded_until = None

    def _select_after_state_change(self, old_active: str | None) -> None:
        """Apply selection rules after a state change."""

        if old_active is not None and not self._is_source_operational(old_active):
            self._cancel_recovery_timer()
            self.active_source = self._best_operational_source()
            self.state_source = None
            return

        best = self._best_operational_source()
        if best is None:
            self._cancel_recovery_timer()
            self.active_source = None
            self.state_source = None
            return

        if self.active_source is None:
            self.active_source = best
            self.state_source = None
            return

        best_index = self.config.sources.index(best)
        active_index = self.config.sources.index(self.active_source)
        if best_index < active_index:
            self._schedule_recovery(best)
            return

        if best == self.active_source:
            self._cancel_recovery_timer()

    def _best_operational_source(self) -> str | None:
        """Return the best operational source according to selection policy."""

        operational = [s for s in self.config.sources if self._is_source_operational(s)]
        if not operational:
            return None

        return operational[0]

    def _is_source_operational(self, source: str) -> bool:
        """Return whether a source can be used."""

        health = self._health[source]
        return (
            health.exists and health.available and source not in self.excluded_sources
        )

    def _schedule_recovery(self, source: str) -> None:
        """Schedule recovery to a higher-priority source."""

        if (
            self._pending_recovery_source == source
            and self._cancel_recovery is not None
        ):
            return
        self._cancel_recovery_timer()
        self._pending_recovery_source = source

        @callback
        def _recover(_now: datetime) -> None:
            self._pending_recovery_source = None
            self._cancel_recovery = None
            self._refresh_health()
            if not self._is_source_operational(source):
                self._notify()
                return
            old_active = self.active_source
            self.active_source = source
            self.state_source = None
            self._record_failover(old_active, source)
            self._handle_repairs_state()
            self._notify()

        self._cancel_recovery = async_call_later(
            self.hass,
            self.config.recovery_stability,
            _recover,
        )
        _LOGGER.debug(
            "Scheduled recovery for %s to %s in %.1fs",
            self.config.entry_id,
            source,
            self.config.recovery_stability,
        )

    def _cancel_recovery_timer(self) -> None:
        """Cancel pending recovery."""

        if self._cancel_recovery is not None:
            self._cancel_recovery()
        self._cancel_recovery = None
        self._pending_recovery_source = None

    def _record_failover(self, old: str | None, new: str | None) -> None:
        """Record and log a real failover."""

        if old == new:
            return
        self.last_failover = dt_util.utcnow()
        _LOGGER.info(
            "Entity Failover %s switched source from %s to %s",
            self.config.name,
            old,
            new,
        )

    async def async_clear_failures(self) -> None:
        """Clear temporary source exclusions and recalculate active source."""

        for source, health in self._health.items():
            health.excluded_until = None
            health.last_error = None
            unsub = self._cooldown_unsubs.pop(source, None)
            if unsub is not None:
                unsub()
        old_active = self.active_source
        self._refresh_health()
        self.active_source = self._best_operational_source()
        self.state_source = None
        if self.active_source != old_active:
            self._record_failover(old_active, self.active_source)
        self._handle_repairs_state()
        self._notify()

    async def async_call_service(
        self,
        service: str,
        data: Mapping[str, Any] | None = None,
        *,
        context: Context | None = None,
        required_features: int = 0,
    ) -> None:
        """Route a service call to the active source with retry behavior."""

        if self.adapter.read_only:
            raise HomeAssistantError(f"{self.config.domain} is read-only")

        async with self._lock:
            await self._async_call_service_locked(
                service,
                data or {},
                context=context,
                required_features=required_features,
            )

    async def _async_call_service_locked(
        self,
        service: str,
        data: Mapping[str, Any],
        *,
        context: Context | None,
        required_features: int,
    ) -> None:
        attempts = 0
        last_error: Exception | None = None
        tried: set[str] = set()
        while attempts < len(self.config.sources):
            self._refresh_health()
            source = self._select_command_source(tried, required_features)
            if source is None:
                break
            attempts += 1
            tried.add(source)
            before = self.hass.states.get(source)
            expected = self.adapter.expected_result(service, before, data)
            try:
                _LOGGER.debug(
                    "Entity Failover %s routing %s.%s to %s (attempt %d)",
                    self.config.name,
                    self.config.domain,
                    service,
                    source,
                    attempts,
                )
                start_time = dt_util.utcnow()
                await self._async_call_source(
                    source,
                    service,
                    data,
                    context,
                    blocking=self._should_wait_for_service_completion(expected),
                )
                if self._should_confirm_command(expected):
                    if not await self._async_confirm(
                        source,
                        expected,
                        data,
                    ):
                        raise HomeAssistantError(
                            f"{source} did not confirm {self.config.domain}.{service}"
                        )
                latency = (dt_util.utcnow() - start_time).total_seconds()
                await self._async_record_learning_sample(source, latency)
                self.last_command_result = CommandResult(
                    service=service,
                    source=source,
                    success=True,
                    attempts=attempts,
                    when=dt_util.utcnow(),
                )
                self._remember_recent_confirmation(expected, data)
                self._select_state_source_after_successful_command(
                    source,
                    expected,
                )
                old_active = self.active_source
                self._refresh_health()
                self._select_after_state_change(old_active)
                if self.active_source != old_active:
                    self._record_failover(old_active, self.active_source)
                _LOGGER.debug(
                    "Entity Failover %s completed %s.%s on %s (attempt %d)",
                    self.config.name,
                    self.config.domain,
                    service,
                    source,
                    attempts,
                )
                self._notify()
                return
            except Exception as err:
                last_error = err
                self._clear_recent_confirmation()
                self._exclude_source(source, err)
                old_active = self.active_source
                self.active_source = self._best_operational_source()
                self.state_source = None
                if self.active_source != old_active:
                    self._record_failover(old_active, self.active_source)
                _LOGGER.warning(
                    "Source %s failed for %s.%s, retrying if possible: %s",
                    source,
                    self.config.domain,
                    service,
                    err,
                )

        error = HomeAssistantError(
            f"All attempts failed for {self.config.domain}.{service}: {last_error}"
        )
        self.last_command_result = CommandResult(
            service=service,
            source=None,
            success=False,
            attempts=attempts,
            error=str(error),
            when=dt_util.utcnow(),
        )
        self._clear_recent_confirmation()
        self._notify()
        _LOGGER.error("%s", error)
        raise error

    def _should_wait_for_service_completion(
        self,
        expected: ConfirmationRule | object,
    ) -> bool:
        """Return whether the underlying HA service call should be blocking."""

        return self._should_confirm_command(expected) or self.config.learning_enabled

    def _should_confirm_command(
        self,
        expected: ConfirmationRule | object,
    ) -> bool:
        """Return whether a command has enough state signal to verify it."""

        return isinstance(expected, ConfirmationRule)

    def _select_command_source(
        self,
        tried: set[str],
        required_features: int,
    ) -> str | None:
        """Select a source for command routing."""

        if self.config.learning_enabled:
            candidates = [
                source
                for source in self.config.sources
                if source not in tried
                and not self._learning.complete(source)
                and self._is_source_operational(source)
                and self.adapter.source_supports_features(
                    self.hass.states.get(source),
                    required_features,
                )
            ]
            if candidates:
                return min(
                    candidates,
                    key=lambda source: (
                        len(self._learning.samples[source]),
                        self.config.sources.index(source),
                    ),
                )

        ordered: list[str] = []
        if self.active_source is not None:
            ordered.append(self.active_source)
        ordered.extend(
            source for source in self.config.sources if source not in ordered
        )
        for source in ordered:
            if source in tried or not self._is_source_operational(source):
                continue
            state = self.hass.states.get(source)
            if not self.adapter.source_supports_features(state, required_features):
                continue
            return source
        return None

    async def _async_record_learning_sample(
        self,
        source: str,
        latency: float,
    ) -> None:
        """Persist a successful sample and apply a learned order when ready."""

        if not self.config.learning_enabled or self._learning.complete(source):
            return
        self._learning.add_sample(source, latency)
        await self._learning_store.async_save(self._learning)
        _LOGGER.debug(
            "Entity Failover %s learned latency %.3fs for %s (%d/%d)",
            self.config.name,
            latency,
            source,
            len(self._learning.samples[source]),
            LEARNING_SAMPLE_COUNT,
        )
        await self._async_apply_learned_order_if_ready()

    async def _async_apply_learned_order_if_ready(self) -> None:
        """Persist learned priority once every available source is measured."""

        operational = [
            source
            for source in self.config.sources
            if self._is_source_operational(source)
        ]
        if not operational or any(
            not self._learning.complete(source) for source in operational
        ):
            return

        original_index = {
            source: index for index, source in enumerate(self.config.sources)
        }
        measured = [
            source for source in self.config.sources if self._learning.complete(source)
        ]
        measured.sort(
            key=lambda source: (
                self._learning.median_latency(source),
                original_index[source],
            )
        )
        unmeasured = [
            source
            for source in self.config.sources
            if not self._learning.complete(source)
        ]
        learned_order = [*measured, *unmeasured]
        complete = not unmeasured

        if self._entry is None or self.config.subentry_id is None:
            return
        subentry = self._entry.subentries.get(self.config.subentry_id)
        if subentry is None:
            return

        data = dict(subentry.data)
        order_changed = list(data.get(CONF_SOURCES, [])) != learned_order
        data[CONF_SOURCES] = learned_order
        if complete:
            data[CONF_LEARNING_ENABLED] = False
        if not order_changed and not complete:
            return

        if complete:
            await self._learning_store.async_remove()
        self.hass.config_entries.async_update_subentry(
            entry=self._entry,
            subentry=subentry,
            data=data,
        )

    async def _async_call_source(
        self,
        source: str,
        service: str,
        data: Mapping[str, Any],
        context: Context | None,
        *,
        blocking: bool,
    ) -> None:
        """Call a service on a source entity."""

        call_data = dict(data)
        call_data[ATTR_ENTITY_ID] = source
        await self.hass.services.async_call(
            self.config.domain,
            service,
            call_data,
            blocking=blocking,
            context=context,
        )

    async def _async_confirm(
        self,
        source: str,
        expected: ConfirmationRule | object,
        data: Mapping[str, Any],
    ) -> bool:
        """Confirm a command result if a reliable rule exists."""

        if expected is CONFIRM_UNSUPPORTED:
            return True
        if not isinstance(expected, ConfirmationRule):
            return True
        matched_source = self._source_matching_confirmation(expected, data)
        if matched_source is not None:
            self._set_state_source_from_confirmation(source, matched_source)
            return True

        future: asyncio.Future[bool] = self.hass.loop.create_future()

        @callback
        def _state_changed(event: Event[Any]) -> None:
            changed_source = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if self.adapter.confirmation_matches(expected, new_state, data):
                if isinstance(changed_source, str):
                    self._set_state_source_from_confirmation(source, changed_source)
                if not future.done():
                    future.set_result(True)

        unsub_state = async_track_state_change_event(
            self.hass, list(self.config.sources), _state_changed
        )

        @callback
        def _timeout(_now: datetime) -> None:
            if not future.done():
                matched_source = self._source_matching_confirmation(expected, data)
                if matched_source is not None:
                    self._set_state_source_from_confirmation(source, matched_source)
                    future.set_result(True)
                    return
                future.set_result(False)

        unsub_timeout = async_call_later(
            self.hass,
            COMMAND_CONFIRMATION_TIMEOUT,
            _timeout,
        )
        try:
            return await future
        finally:
            unsub_state()
            unsub_timeout()

    def _select_state_source_after_successful_command(
        self,
        command_source: str,
        expected: ConfirmationRule | object,
    ) -> None:
        """Select a mirrored state source after a successful service call."""

        if not isinstance(expected, ConfirmationRule):
            return
        matched_source = self._source_matching_confirmation(
            expected,
            self._pending_confirmation_data,
        )
        if matched_source is None:
            return
        self._set_state_source_from_confirmation(command_source, matched_source)

    def _remember_recent_confirmation(
        self,
        expected: ConfirmationRule | object,
        data: Mapping[str, Any],
    ) -> None:
        """Remember a successful command briefly for delayed peer state updates."""

        if not isinstance(expected, ConfirmationRule):
            self._clear_recent_confirmation()
            return
        self._pending_confirmation_rule = expected
        self._pending_confirmation_data = dict(data)
        self._pending_confirmation_until = dt_util.utcnow() + timedelta(
            seconds=COMMAND_CONFIRMATION_TIMEOUT
        )

    def _clear_recent_confirmation(self) -> None:
        """Clear delayed confirmation tracking."""

        self._pending_confirmation_rule = None
        self._pending_confirmation_data = {}
        self._pending_confirmation_until = None

    def _select_state_source_after_recent_confirmation(
        self,
        changed_source: str,
    ) -> None:
        """Use delayed source updates from a recent successful command."""

        rule = self._pending_confirmation_rule
        if rule is None or self._pending_confirmation_until is None:
            return
        if self._pending_confirmation_until <= dt_util.utcnow():
            self._clear_recent_confirmation()
            return
        if not self._is_source_operational(changed_source):
            return
        state = self.hass.states.get(changed_source)
        if not self.adapter.confirmation_matches(
            rule,
            state,
            self._pending_confirmation_data,
        ):
            if changed_source == self.active_source:
                self._clear_recent_confirmation()
            return
        command_source = self.active_source or changed_source
        self._set_state_source_from_confirmation(command_source, changed_source)
        if changed_source == self.active_source:
            self._clear_recent_confirmation()

    def _source_matching_confirmation(
        self,
        expected: ConfirmationRule,
        data: Mapping[str, Any],
    ) -> str | None:
        """Return the first operational source matching an expected state."""

        for source in self.config.sources:
            if not self._is_source_operational(source):
                continue
            state = self.hass.states.get(source)
            if self.adapter.confirmation_matches(expected, state, data):
                return source
        return None

    def _set_state_source_from_confirmation(
        self,
        command_source: str,
        matched_source: str,
    ) -> None:
        """Mirror state from a confirming source while commands keep priority."""

        old_state_source = self.state_source
        self.state_source = None if matched_source == command_source else matched_source
        if self.state_source != old_state_source:
            _LOGGER.debug(
                "Entity Failover %s using %s as state source while command "
                "source is %s",
                self.config.name,
                self.effective_state_source,
                command_source,
            )

    def _select_state_source_after_state_change(self, changed_source: str) -> None:
        """Return state mirroring to the command source when it catches up."""

        if self.state_source is None:
            return
        if not self._is_source_operational(self.state_source):
            self.state_source = None
            self._clear_recent_confirmation()
            return
        if changed_source != self.active_source:
            return
        active_state = self.hass.states.get(self.active_source)
        state_source_state = self.hass.states.get(self.state_source)
        if (
            active_state is not None
            and state_source_state is not None
            and active_state.state == state_source_state.state
        ):
            _LOGGER.debug(
                "Entity Failover %s returned state source to command source %s",
                self.config.name,
                self.active_source,
            )
            self.state_source = None
            self._clear_recent_confirmation()

    def _exclude_source(self, source: str, err: Exception) -> None:
        """Temporarily exclude a failed source."""

        health = self._health[source]
        health.last_error = str(err)
        health.excluded_until = dt_util.utcnow() + timedelta(
            seconds=self.config.failure_cooldown
        )
        old_unsub = self._cooldown_unsubs.pop(source, None)
        if old_unsub is not None:
            old_unsub()

        @callback
        def _clear(_now: datetime) -> None:
            self._cooldown_unsubs.pop(source, None)
            health.excluded_until = None
            self._refresh_health()
            old_active = self.active_source
            self._select_after_state_change(old_active)
            self._select_state_source_after_state_change(source)
            if self.active_source != old_active:
                self._record_failover(old_active, self.active_source)
            self._handle_repairs_state()
            self._notify()

        self._cooldown_unsubs[source] = async_call_later(
            self.hass,
            self.config.failure_cooldown,
            _clear,
        )

    def _handle_repairs_state(self) -> None:
        """Create or delete the all-sources-unavailable Repairs issue."""

        if self._unloaded:
            return
        issue_id = self._repairs_issue_id
        if self.active_source is not None:
            if self._cancel_repairs_timer is not None:
                self._cancel_repairs_timer()
                self._cancel_repairs_timer = None
            if self._repairs_issue_active:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
                self._repairs_issue_active = False
            return

        if self._repairs_issue_active or self._cancel_repairs_timer is not None:
            return

        if self.config.repairs_delay <= 0:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            self._repairs_issue_active = False
            return

        @callback
        def _create_issue(_now: datetime) -> None:
            self._cancel_repairs_timer = None
            self._refresh_health()
            if (
                self.active_source is not None
                or self._best_operational_source() is not None
            ):
                return
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                is_persistent=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_ALL_SOURCES_UNAVAILABLE,
                translation_placeholders={
                    "name": self.config.name,
                    "sources": ", ".join(self.config.sources),
                },
            )
            self._repairs_issue_active = True

        self._cancel_repairs_timer = async_call_later(
            self.hass,
            self.config.repairs_delay,
            _create_issue,
        )

    @property
    def _repairs_issue_id(self) -> str:
        """Return the issue id for this config entry."""

        return f"{ISSUE_ALL_SOURCES_UNAVAILABLE}_{self.config.entry_id}"

    def diagnostics(self) -> ManagerDiagnostics:
        """Return diagnostics for this manager."""

        return ManagerDiagnostics(
            entry=self.config.as_dict(),
            active_source=self.active_source,
            state_source=self.effective_state_source,
            sources_desynchronized=self.sources_desynchronized,
            source_health={
                source: health.as_dict() for source, health in self._health.items()
            },
            temporary_exclusions={
                source: health.excluded_until.isoformat()
                for source, health in self._health.items()
                if health.excluded_until is not None
            },
            pending_recovery=self._pending_recovery_source,
            last_failover=self.last_failover.isoformat()
            if self.last_failover
            else None,
            last_command_result=self.last_command_result.as_dict()
            if self.last_command_result
            else None,
            repairs_issue_active=self._repairs_issue_active,
            extra={
                "active_source_name": friendly_name(self.hass, self.active_source),
                "state_source_name": friendly_name(
                    self.hass,
                    self.effective_state_source,
                ),
                "learning_status": self.learning_status,
                "learning_progress": self.learning_progress,
                "learning_target": LEARNING_SAMPLE_COUNT,
                "learned_median_latency": self.learned_latencies,
                "learning_pending_sources": self.learning_pending_sources,
            },
        )
