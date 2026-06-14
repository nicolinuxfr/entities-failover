"""Tests for config flow validation."""

from __future__ import annotations

import pytest
from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_failover.config_flow import (
    ADVANCED_SECTION,
    EntityFailoverConfigFlow,
    EntityFailoverOptionsFlow,
    _options_schema,
    _user_schema,
    _validate_sources,
)
from custom_components.entity_failover.const import (
    CONF_AVAILABILITY_STRATEGY,
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_MAX_ATTEMPTS,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_validate_refuses_single_source(hass) -> None:
    """A failover entity needs at least two sources."""

    assert _validate_sources(hass, "switch", ["switch.one"], None) == "too_few_sources"


@pytest.mark.asyncio
async def test_validate_refuses_duplicates(hass) -> None:
    """A source cannot be selected twice."""

    assert (
        _validate_sources(hass, "switch", ["switch.one", "switch.one"], None)
        == "duplicate_sources"
    )


@pytest.mark.asyncio
async def test_validate_refuses_mixed_domains(hass) -> None:
    """All sources must match the selected domain."""

    assert (
        _validate_sources(hass, "switch", ["switch.one", "light.two"], None)
        == "mixed_domains"
    )


@pytest.mark.asyncio
async def test_validate_refuses_unsupported_domain(hass) -> None:
    """All sources must use a supported domain."""

    assert (
        _validate_sources(
            hass, "automation", ["automation.one", "automation.two"], None
        )
        == "unsupported_domain"
    )


def test_source_selectors_default_to_empty_lists() -> None:
    """Multiple entity selectors must never receive None as a default."""

    assert _user_schema()({})[CONF_SOURCES] == []
    assert _options_schema()({})[CONF_SOURCES] == []


def test_advanced_settings_are_collapsed() -> None:
    """Advanced settings live in a collapsed section."""

    section = _user_schema().schema[ADVANCED_SECTION]

    assert isinstance(section, data_entry_flow.section)
    assert section.options["collapsed"] is True


@pytest.mark.asyncio
async def test_config_flow_creates_entry(hass) -> None:
    """The UI flow creates a config entry from a single form."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")

    flow = EntityFailoverConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    result = await flow.async_step_user()
    assert result["type"] == "form"

    result = await flow.async_step_user(
        {
            "name": "Kitchen Switch",
            CONF_SOURCES: ["switch.one", "switch.two"],
            "availability_strategy": "simple",
            "recovery_stability": 30,
            "failure_cooldown": 60,
            "feature_policy": "intersection",
            ADVANCED_SECTION: {
                "command_validation": "service_call",
                "confirmation_timeout": 10,
                "max_attempts": 3,
            },
        },
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Kitchen Switch"
    assert result["data"][CONF_DOMAIN] == "switch"
    assert result["data"][CONF_COMMAND_VALIDATION] == "service_call"


@pytest.mark.asyncio
async def test_config_flow_manager_creates_entry_from_single_form(hass) -> None:
    """Home Assistant's flow manager validates the one-screen schema."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"
    assert result["last_step"] is True

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Kitchen Switch",
            CONF_SOURCES: ["switch.one", "switch.two"],
            CONF_AVAILABILITY_STRATEGY: "simple",
            CONF_RECOVERY_STABILITY: 30,
            CONF_FAILURE_COOLDOWN: 60,
            CONF_FEATURE_POLICY: "intersection",
            ADVANCED_SECTION: {
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 10,
                CONF_MAX_ATTEMPTS: 3,
            },
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_DOMAIN] == "switch"


@pytest.mark.asyncio
async def test_options_flow_updates_entry_from_single_form(hass) -> None:
    """The options flow updates behavior from a single form."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen Switch",
        unique_id="unique-options",
        data={
            "name": "Kitchen Switch",
            CONF_DOMAIN: "switch",
            CONF_SOURCES: ["switch.one", "switch.two"],
            CONF_AVAILABILITY_STRATEGY: "simple",
            CONF_COMMAND_VALIDATION: "service_call",
            CONF_CONFIRMATION_TIMEOUT: 10,
            CONF_FAILURE_COOLDOWN: 60,
            CONF_RECOVERY_STABILITY: 30,
            CONF_MAX_ATTEMPTS: 3,
            CONF_FEATURE_POLICY: "intersection",
        },
    )
    entry.add_to_hass(hass)
    flow = EntityFailoverOptionsFlow(entry)
    flow.hass = hass

    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await flow.async_step_init(
        {
            CONF_SOURCES: ["switch.one", "switch.two"],
            CONF_AVAILABILITY_STRATEGY: "simple",
            CONF_RECOVERY_STABILITY: 15,
            CONF_FAILURE_COOLDOWN: 45,
            CONF_FEATURE_POLICY: "active_source",
            ADVANCED_SECTION: {
                CONF_COMMAND_VALIDATION: "none",
                CONF_CONFIRMATION_TIMEOUT: 5,
                CONF_MAX_ATTEMPTS: 2,
            },
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_RECOVERY_STABILITY] == 15
    assert result["data"][CONF_COMMAND_VALIDATION] == "none"


def test_options_schema_uses_existing_defaults() -> None:
    """Existing options appear as defaults in the single form."""

    data = _options_schema(
        {
            CONF_SOURCES: ["switch.one", "switch.two"],
            CONF_AVAILABILITY_STRATEGY: "simple",
            CONF_RECOVERY_STABILITY: 15,
            CONF_FAILURE_COOLDOWN: 45,
            CONF_FEATURE_POLICY: "active_source",
            CONF_COMMAND_VALIDATION: "none",
            CONF_CONFIRMATION_TIMEOUT: 5,
            CONF_MAX_ATTEMPTS: 2,
        }
    )({})

    assert data[CONF_SOURCES] == ["switch.one", "switch.two"]
    assert data[CONF_FEATURE_POLICY] == "active_source"
    assert data[ADVANCED_SECTION][CONF_COMMAND_VALIDATION] == "none"
