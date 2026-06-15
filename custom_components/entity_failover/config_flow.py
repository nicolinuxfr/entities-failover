"""Config flow for Entity Failover."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .adapters import adapter_for_domain
from .const import (
    AVAILABILITY_STRATEGIES,
    COMMAND_VALIDATION_MODES,
    CONF_AVAILABILITY_STRATEGY,
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_MAX_ATTEMPTS,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DEFAULT_AVAILABILITY_STRATEGY,
    DEFAULT_COMMAND_VALIDATION,
    DEFAULT_CONFIRMATION_TIMEOUT,
    DEFAULT_FAILURE_COOLDOWN,
    DEFAULT_FEATURE_POLICY,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_RECOVERY_STABILITY,
    DOMAIN,
    FEATURE_POLICIES,
    NAME,
    SUBENTRY_TYPE_FAILOVER,
    SUPPORTED_DOMAINS,
)
from .helpers import entity_domain, normalize_sources

ADVANCED_SECTION = "advanced"


class EntityFailoverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Entity Failover config flow."""

    VERSION = 2

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: config_entries.ConfigEntry,
    ) -> dict[str, type[config_entries.ConfigSubentryFlow]]:
        """Return subentries supported by this handler."""

        return {SUBENTRY_TYPE_FAILOVER: EntityFailoverSubentryFlow}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create the service entry."""

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=NAME,
            data={},
        )


class EntityFailoverSubentryFlow(config_entries.ConfigSubentryFlow):
    """Handle failover entity subentry flows."""

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.SubentryFlowResult:
        """Create a failover entity subentry."""

        errors: dict[str, str] = {}
        if user_input is not None:
            sources = normalize_sources(user_input[CONF_SOURCES])
            domain = entity_domain(sources[0]) if sources else ""
            error = _validate_sources(self.hass, domain, sources, self._entry_id)
            if error is None:
                subentry = _subentry_data_from_user_input(user_input, domain, sources)
                return self.async_create_entry(
                    title=subentry["title"],
                    data=subentry["data"],
                    unique_id=subentry["unique_id"],
                )
            errors[CONF_SOURCES] = error

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
            last_step=True,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.SubentryFlowResult:
        """Reconfigure a failover entity subentry."""

        subentry = self._get_reconfigure_subentry()
        defaults = _subentry_schema_defaults(subentry)
        errors: dict[str, str] = {}
        if user_input is not None:
            sources = normalize_sources(user_input[CONF_SOURCES])
            domain = entity_domain(sources[0]) if sources else ""
            error = _validate_sources(
                self.hass,
                domain,
                sources,
                self._entry_id,
                subentry.subentry_id,
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(user_input[CONF_NAME]),
                    data=_failover_data_from_user_input(user_input, domain, sources),
                    reload_even_if_entry_is_unchanged=False,
                )
            errors[CONF_SOURCES] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(_schema_defaults(defaults, user_input)),
            errors=errors,
            last_step=True,
        )


def _schema_defaults(
    defaults: Mapping[str, Any],
    user_input: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return form defaults after an invalid submission."""

    if user_input is None:
        return dict(defaults)
    return {**defaults, **user_input}


def _subentry_schema_defaults(
    subentry: config_entries.ConfigSubentry,
) -> dict[str, Any]:
    """Return schema defaults from a subentry."""

    return {CONF_NAME: subentry.title, **subentry.data}


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return the one-step failover entity schema."""

    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
        vol.Required(
            CONF_SOURCES,
            default=list(defaults.get(CONF_SOURCES, [])),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                filter=selector.EntityFilterSelectorConfig(domain=SUPPORTED_DOMAINS),
                multiple=True,
                reorder=True,
            )
        ),
    }
    schema.update(_general_schema_fields(defaults))
    schema[
        vol.Optional(
            ADVANCED_SECTION,
            default=_advanced_defaults(defaults),
        )
    ] = data_entry_flow.section(
        vol.Schema(_advanced_schema_fields(_advanced_defaults(defaults))),
        {"collapsed": True},
    )
    return vol.Schema(schema)


def _general_schema_fields(
    defaults: Mapping[str, Any] | None = None,
) -> dict[Any, Any]:
    """Return general settings schema fields."""

    defaults = defaults or {}
    return {
        vol.Required(
            CONF_AVAILABILITY_STRATEGY,
            default=defaults.get(
                CONF_AVAILABILITY_STRATEGY, DEFAULT_AVAILABILITY_STRATEGY
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=AVAILABILITY_STRATEGIES)
        ),
        vol.Required(
            CONF_RECOVERY_STABILITY,
            default=defaults.get(CONF_RECOVERY_STABILITY, DEFAULT_RECOVERY_STABILITY),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=3600,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Required(
            CONF_FAILURE_COOLDOWN,
            default=defaults.get(CONF_FAILURE_COOLDOWN, DEFAULT_FAILURE_COOLDOWN),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=3600,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Required(
            CONF_FEATURE_POLICY,
            default=defaults.get(CONF_FEATURE_POLICY, DEFAULT_FEATURE_POLICY),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=FEATURE_POLICIES)
        ),
    }


def _advanced_schema_fields(
    defaults: Mapping[str, Any] | None = None,
) -> dict[Any, Any]:
    """Return advanced settings schema fields."""

    defaults = defaults or {}
    return {
        vol.Required(
            CONF_COMMAND_VALIDATION,
            default=defaults.get(CONF_COMMAND_VALIDATION, DEFAULT_COMMAND_VALIDATION),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=COMMAND_VALIDATION_MODES)
        ),
        vol.Required(
            CONF_CONFIRMATION_TIMEOUT,
            default=defaults.get(
                CONF_CONFIRMATION_TIMEOUT, DEFAULT_CONFIRMATION_TIMEOUT
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=120,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Required(
            CONF_MAX_ATTEMPTS,
            default=defaults.get(CONF_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=10,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }


def _advanced_defaults(defaults: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return advanced section defaults."""

    defaults = defaults or {}
    section_defaults = defaults.get(ADVANCED_SECTION)
    if isinstance(section_defaults, Mapping):
        defaults = {**defaults, **section_defaults}
    return {
        CONF_COMMAND_VALIDATION: defaults.get(
            CONF_COMMAND_VALIDATION, DEFAULT_COMMAND_VALIDATION
        ),
        CONF_CONFIRMATION_TIMEOUT: defaults.get(
            CONF_CONFIRMATION_TIMEOUT, DEFAULT_CONFIRMATION_TIMEOUT
        ),
        CONF_MAX_ATTEMPTS: defaults.get(CONF_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
    }


def _advanced_user_input(user_input: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return advanced settings from flattened or sectioned user input."""

    section_input = user_input.get(ADVANCED_SECTION)
    if isinstance(section_input, Mapping):
        return section_input
    return user_input


def _subentry_data_from_user_input(
    user_input: Mapping[str, Any],
    domain: str,
    sources: list[str],
) -> config_entries.ConfigSubentryData:
    """Return config subentry data from form input."""

    return {
        "title": str(user_input[CONF_NAME]),
        "data": _failover_data_from_user_input(user_input, domain, sources),
        "subentry_type": SUBENTRY_TYPE_FAILOVER,
        "unique_id": str(uuid4()),
    }


def _failover_data_from_user_input(
    user_input: Mapping[str, Any],
    domain: str,
    sources: list[str],
) -> dict[str, Any]:
    """Return failover settings from form input."""

    advanced = _advanced_user_input(user_input)
    return {
        CONF_NAME: str(user_input[CONF_NAME]),
        CONF_DOMAIN: domain,
        CONF_SOURCES: sources,
        CONF_AVAILABILITY_STRATEGY: user_input.get(
            CONF_AVAILABILITY_STRATEGY, DEFAULT_AVAILABILITY_STRATEGY
        ),
        CONF_COMMAND_VALIDATION: advanced.get(
            CONF_COMMAND_VALIDATION, DEFAULT_COMMAND_VALIDATION
        ),
        CONF_CONFIRMATION_TIMEOUT: advanced.get(
            CONF_CONFIRMATION_TIMEOUT, DEFAULT_CONFIRMATION_TIMEOUT
        ),
        CONF_FAILURE_COOLDOWN: user_input.get(
            CONF_FAILURE_COOLDOWN, DEFAULT_FAILURE_COOLDOWN
        ),
        CONF_RECOVERY_STABILITY: user_input.get(
            CONF_RECOVERY_STABILITY, DEFAULT_RECOVERY_STABILITY
        ),
        CONF_MAX_ATTEMPTS: advanced.get(CONF_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
        CONF_FEATURE_POLICY: user_input.get(
            CONF_FEATURE_POLICY, DEFAULT_FEATURE_POLICY
        ),
    }


def _validate_sources(  # noqa: PLR0911
    hass: HomeAssistant,
    domain: str,
    sources: list[str],
    current_entry_id: str | None,
    current_subentry_id: str | None = None,
) -> str | None:
    """Validate source entity ids."""

    if len(sources) < 2:
        return "too_few_sources"
    if domain not in SUPPORTED_DOMAINS:
        return "unsupported_domain"
    if len(set(sources)) != len(sources):
        return "duplicate_sources"
    if any(entity_domain(source) != domain for source in sources):
        return "mixed_domains"
    registry = er.async_get(hass)
    for source in sources:
        registry_entry = registry.async_get(source)
        if (
            registry_entry is not None
            and registry_entry.platform == DOMAIN
            and registry_entry.config_entry_id == current_entry_id
            and registry_entry.config_subentry_id == current_subentry_id
        ):
            return "self_reference"
    if (
        current_entry_id
        and current_subentry_id
        and _would_create_cycle(hass, sources, current_entry_id, current_subentry_id)
    ):
        return "circular_dependency"
    compatibility_error = adapter_for_domain(domain).validate_sources(hass, sources)
    if compatibility_error is not None:
        return compatibility_error
    return None


def _would_create_cycle(
    hass: HomeAssistant,
    sources: list[str],
    current_entry_id: str,
    current_subentry_id: str,
) -> bool:
    """Return whether selected sources would create an Entity Failover cycle."""

    registry = er.async_get(hass)
    entries_by_id = {
        entry.entry_id: entry for entry in hass.config_entries.async_entries(DOMAIN)
    }
    stack: list[tuple[str, str | None]] = []
    for source in sources:
        registry_entry = registry.async_get(source)
        if registry_entry is not None and registry_entry.platform == DOMAIN:
            config_entry_id = registry_entry.config_entry_id
            if config_entry_id is not None:
                stack.append((config_entry_id, registry_entry.config_subentry_id))
    seen: set[tuple[str, str | None]] = set()
    while stack:
        entry_id, subentry_id = stack.pop()
        if entry_id == current_entry_id and subentry_id == current_subentry_id:
            return True
        if (entry_id, subentry_id) in seen:
            continue
        seen.add((entry_id, subentry_id))
        entry = entries_by_id.get(entry_id)
        if entry is None:
            continue
        if subentry_id not in entry.subentries:
            continue
        source_ids = entry.subentries[subentry_id].data.get(CONF_SOURCES, [])
        for source in source_ids:
            registry_entry = registry.async_get(source)
            if registry_entry is not None and registry_entry.platform == DOMAIN:
                config_entry_id = registry_entry.config_entry_id
                if config_entry_id is not None:
                    stack.append((config_entry_id, registry_entry.config_subentry_id))
    return False
