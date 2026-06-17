"""Runtime failover manager."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any

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
    ATTR_PRIORITY_INDEX,
    DEFAULT_REPAIRS_DELAY,
    DOMAIN,
    ISSUE_ALL_SOURCES_UNAVAILABLE,
)
from .helpers import friendly_name, state_available
from .model import (
    CommandResult,
    CommandValidation,
    FailoverConfig,
    ManagerDiagnostics,
    SourceHealth,
)

_LOGGER = logging.getLogger(__name__)
UpdateCallback = Callable[[], None]


class FailoverManager:
    """Manage source selection, health and command routing for one config entry."""

    def __init__(self, hass: HomeAssistant, config: FailoverConfig) -> None:
        """Initialize the manager."""

        self.hass = hass
        self.config = config
        self.adapter: DomainAdapter = adapter_for_domain(config.domain)
        self.active_source: str | None = None
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

    @property
    def active_state(self) -> State | None:
        """Return the active source state."""

        if self.active_source is None:
            return None
        return self.hass.states.get(self.active_source)

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
            ATTR_PRIORITY_INDEX: self.active_priority_index,
            ATTR_DEGRADED: self.degraded,
            ATTR_AVAILABLE_SOURCES: self.available_sources,
            ATTR_EXCLUDED_SOURCES: self.excluded_sources,
        }

    async def async_start(self) -> None:
        """Start tracking source states."""

        self._refresh_health()
        self.active_source = self._best_operational_source()
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

    def async_add_update_listener(self, callback_func: UpdateCallback) -> CALLBACK_TYPE:
        """Register an entity update callback."""

        self._callbacks.append(callback_func)

        @callback
        def _remove() -> None:
            if callback_func in self._callbacks:
                self._callbacks.remove(callback_func)

        return _remove

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
            return

        best = self._best_operational_source()
        if best is None:
            self._cancel_recovery_timer()
            self.active_source = None
            return

        if self.active_source is None:
            self.active_source = best
            return

        best_index = self.config.sources.index(best)
        active_index = self.config.sources.index(self.active_source)
        if best_index < active_index:
            self._schedule_recovery(best)
            return

        if best == self.active_source:
            self._cancel_recovery_timer()

    def _best_operational_source(self) -> str | None:
        """Return the highest-priority operational source."""

        for source in self.config.sources:
            if self._is_source_operational(source):
                return source
        return None

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
            try:
                _LOGGER.debug(
                    "Entity Failover %s routing %s.%s to %s (attempt %d)",
                    self.config.name,
                    self.config.domain,
                    service,
                    source,
                    attempts,
                )
                await self._async_call_source(source, service, data, context)
                if (
                    self.config.command_validation
                    == CommandValidation.STATE_CONFIRMATION
                ):
                    if not await self._async_confirm(source, service, before, data):
                        raise HomeAssistantError(
                            f"{source} did not confirm {self.config.domain}.{service}"
                        )
                self.last_command_result = CommandResult(
                    service=service,
                    source=source,
                    success=True,
                    attempts=attempts,
                    when=dt_util.utcnow(),
                )
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
                self._exclude_source(source, err)
                old_active = self.active_source
                self.active_source = self._best_operational_source()
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
        self._notify()
        _LOGGER.error("%s", error)
        raise error

    def _select_command_source(
        self,
        tried: set[str],
        required_features: int,
    ) -> str | None:
        """Select a source for command routing."""

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

    async def _async_call_source(
        self,
        source: str,
        service: str,
        data: Mapping[str, Any],
        context: Context | None,
    ) -> None:
        """Call a service on a source entity."""

        call_data = dict(data)
        call_data[ATTR_ENTITY_ID] = source
        await self.hass.services.async_call(
            self.config.domain,
            service,
            call_data,
            blocking=True,
            context=context,
        )

    async def _async_confirm(
        self,
        source: str,
        service: str,
        before: State | None,
        data: Mapping[str, Any],
    ) -> bool:
        """Confirm a command result if a reliable rule exists."""

        expected = self.adapter.expected_result(service, before, data)
        if expected is CONFIRM_UNSUPPORTED:
            return True
        if not isinstance(expected, ConfirmationRule):
            return True
        state = self.hass.states.get(source)
        if self.adapter.confirmation_matches(expected, state, data):
            return True

        future: asyncio.Future[bool] = self.hass.loop.create_future()

        @callback
        def _state_changed(event: Event[Any]) -> None:
            new_state = event.data.get("new_state")
            if self.adapter.confirmation_matches(expected, new_state, data):
                if not future.done():
                    future.set_result(True)

        unsub_state = async_track_state_change_event(
            self.hass, [source], _state_changed
        )

        @callback
        def _timeout(_now: datetime) -> None:
            if not future.done():
                future.set_result(False)

        unsub_timeout = async_call_later(
            self.hass,
            self.config.confirmation_timeout,
            _timeout,
        )
        try:
            return await future
        finally:
            unsub_state()
            unsub_timeout()

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
            DEFAULT_REPAIRS_DELAY,
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
            },
        )
