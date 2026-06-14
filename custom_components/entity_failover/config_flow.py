"""Config flow for Entity Failover."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
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
    SUPPORTED_DOMAINS,
)
from .helpers import entity_domain, normalize_sources


class EntityFailoverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Entity Failover config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""

        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EntityFailoverOptionsFlow:
        """Return the options flow."""

        return EntityFailoverOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Collect name and domain."""

        errors: dict[str, str] = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sources()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_sources(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Collect ordered source entity ids."""

        errors: dict[str, str] = {}
        domain = self._data[CONF_DOMAIN]
        if user_input is not None:
            sources = normalize_sources(user_input[CONF_SOURCES])
            error = _validate_sources(self.hass, domain, sources, None)
            if error is None:
                self._data[CONF_SOURCES] = sources
                return await self.async_step_general()
            errors[CONF_SOURCES] = error

        return self.async_show_form(
            step_id="sources",
            data_schema=_sources_schema(domain),
            errors=errors,
        )

    async def async_step_general(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Collect general behavior settings."""

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_advanced()

        return self.async_show_form(
            step_id="general",
            data_schema=_general_schema(),
        )

    async def async_step_advanced(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Collect advanced command settings and create the entry."""

        if user_input is not None:
            self._data.update(user_input)
            unique_id = str(uuid4())
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data={
                    CONF_NAME: self._data[CONF_NAME],
                    CONF_DOMAIN: self._data[CONF_DOMAIN],
                    CONF_SOURCES: self._data[CONF_SOURCES],
                    CONF_AVAILABILITY_STRATEGY: self._data[CONF_AVAILABILITY_STRATEGY],
                    CONF_COMMAND_VALIDATION: self._data[CONF_COMMAND_VALIDATION],
                    CONF_CONFIRMATION_TIMEOUT: self._data[CONF_CONFIRMATION_TIMEOUT],
                    CONF_FAILURE_COOLDOWN: self._data[CONF_FAILURE_COOLDOWN],
                    CONF_RECOVERY_STABILITY: self._data[CONF_RECOVERY_STABILITY],
                    CONF_MAX_ATTEMPTS: self._data[CONF_MAX_ATTEMPTS],
                    CONF_FEATURE_POLICY: self._data[CONF_FEATURE_POLICY],
                },
            )

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(),
        )


class EntityFailoverOptionsFlow(config_entries.OptionsFlow):
    """Handle Entity Failover options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

        self._entry = config_entry
        self._data: dict[str, Any] = {**config_entry.data, **config_entry.options}

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Start options flow."""

        return await self.async_step_sources(user_input)

    async def async_step_sources(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Update ordered sources."""

        errors: dict[str, str] = {}
        domain = self._data[CONF_DOMAIN]
        if user_input is not None:
            sources = normalize_sources(user_input[CONF_SOURCES])
            error = _validate_sources(self.hass, domain, sources, self._entry.entry_id)
            if error is None:
                self._data[CONF_SOURCES] = sources
                return await self.async_step_general()
            errors[CONF_SOURCES] = error

        return self.async_show_form(
            step_id="sources",
            data_schema=_sources_schema(domain, self._data[CONF_SOURCES]),
            errors=errors,
        )

    async def async_step_general(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Update general options."""

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_advanced()

        return self.async_show_form(
            step_id="general",
            data_schema=_general_schema(self._data),
        )

    async def async_step_advanced(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Update advanced options."""

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="",
                data={
                    CONF_SOURCES: self._data[CONF_SOURCES],
                    CONF_AVAILABILITY_STRATEGY: self._data[CONF_AVAILABILITY_STRATEGY],
                    CONF_COMMAND_VALIDATION: self._data[CONF_COMMAND_VALIDATION],
                    CONF_CONFIRMATION_TIMEOUT: self._data[CONF_CONFIRMATION_TIMEOUT],
                    CONF_FAILURE_COOLDOWN: self._data[CONF_FAILURE_COOLDOWN],
                    CONF_RECOVERY_STABILITY: self._data[CONF_RECOVERY_STABILITY],
                    CONF_MAX_ATTEMPTS: self._data[CONF_MAX_ATTEMPTS],
                    CONF_FEATURE_POLICY: self._data[CONF_FEATURE_POLICY],
                },
            )

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(self._data),
        )


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return the first-step schema."""

    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(
                CONF_DOMAIN,
                default=defaults.get(CONF_DOMAIN, "switch"),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SUPPORTED_DOMAINS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    sort=True,
                )
            ),
        }
    )


def _sources_schema(domain: str, default: list[str] | None = None) -> vol.Schema:
    """Return the sources schema."""

    entity_filter = selector.EntityFilterSelectorConfig(domain=domain)
    return vol.Schema(
        {
            vol.Required(CONF_SOURCES, default=default): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    filter=entity_filter,
                    multiple=True,
                    reorder=True,
                )
            )
        }
    )


def _general_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return general settings schema."""

    defaults = defaults or {}
    return vol.Schema(
        {
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
                default=defaults.get(
                    CONF_RECOVERY_STABILITY, DEFAULT_RECOVERY_STABILITY
                ),
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
    )


def _advanced_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return advanced settings schema."""

    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_COMMAND_VALIDATION,
                default=defaults.get(
                    CONF_COMMAND_VALIDATION, DEFAULT_COMMAND_VALIDATION
                ),
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
    )


def _validate_sources(  # noqa: PLR0911
    hass: HomeAssistant,
    domain: str,
    sources: list[str],
    current_entry_id: str | None,
) -> str | None:
    """Validate source entity ids."""

    if len(sources) < 2:
        return "too_few_sources"
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
        ):
            return "self_reference"
    if current_entry_id and _would_create_cycle(hass, sources, current_entry_id):
        return "circular_dependency"
    compatibility_error = adapter_for_domain(domain).validate_sources(hass, sources)
    if compatibility_error is not None:
        return compatibility_error
    return None


def _would_create_cycle(
    hass: HomeAssistant,
    sources: list[str],
    current_entry_id: str,
) -> bool:
    """Return whether selected sources would create an Entity Failover cycle."""

    registry = er.async_get(hass)
    entries_by_id = {
        entry.entry_id: entry for entry in hass.config_entries.async_entries(DOMAIN)
    }
    stack: list[str] = []
    for source in sources:
        registry_entry = registry.async_get(source)
        if registry_entry is not None and registry_entry.platform == DOMAIN:
            config_entry_id = registry_entry.config_entry_id
            if config_entry_id is not None:
                stack.append(config_entry_id)
    seen: set[str] = set()
    while stack:
        entry_id = stack.pop()
        if entry_id == current_entry_id:
            return True
        if entry_id in seen:
            continue
        seen.add(entry_id)
        entry = entries_by_id.get(entry_id)
        if entry is None:
            continue
        for source in entry.data.get(CONF_SOURCES, []):
            registry_entry = registry.async_get(source)
            if registry_entry is not None and registry_entry.platform == DOMAIN:
                config_entry_id = registry_entry.config_entry_id
                if config_entry_id is not None:
                    stack.append(config_entry_id)
    return False
