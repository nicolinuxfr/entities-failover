"""Tests for config flow validation."""

from __future__ import annotations

import pytest
from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_failover.config_flow import (
    ADVANCED_SECTION,
    EntityFailoverConfigFlow,
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
    NAME,
    SUBENTRY_TYPE_FAILOVER,
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


def test_advanced_settings_are_collapsed() -> None:
    """Advanced settings live in a collapsed section."""

    section = _user_schema().schema[ADVANCED_SECTION]

    assert isinstance(section, data_entry_flow.section)
    assert section.options["collapsed"] is True


@pytest.mark.asyncio
async def test_config_flow_creates_entry(hass) -> None:
    """The UI flow creates the service entry."""

    flow = EntityFailoverConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    result = await flow.async_step_user()

    assert result["type"] == "create_entry"
    assert result["title"] == NAME
    assert result["data"] == {}
    assert list(result["subentries"]) == []


@pytest.mark.asyncio
async def test_config_flow_manager_creates_entry_from_single_form(hass) -> None:
    """Home Assistant's flow manager creates a service entry."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.title == NAME
    assert len(entry.subentries) == 0
    assert SUBENTRY_TYPE_FAILOVER in entry.supported_subentry_types


@pytest.mark.asyncio
async def test_subentry_flow_adds_failover_from_integration_page(hass) -> None:
    """The integration page can add failover entities as subentries."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        version=2,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_FAILOVER),
        context={"source": "user"},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["last_step"] is True

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Kitchen Switch",
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
    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Kitchen Switch"
    assert result["data"][CONF_RECOVERY_STABILITY] == 15
    assert result["data"][CONF_COMMAND_VALIDATION] == "none"


@pytest.mark.asyncio
async def test_subentry_flow_reconfigures_failover(hass) -> None:
    """Existing failover subentries can be reconfigured."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
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
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Kitchen Switch",
                "unique_id": "unique-subentry",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_FAILOVER),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Updated Switch",
            CONF_SOURCES: ["switch.one", "switch.two"],
            CONF_AVAILABILITY_STRATEGY: "simple",
            CONF_RECOVERY_STABILITY: 20,
            CONF_FAILURE_COOLDOWN: 40,
            CONF_FEATURE_POLICY: "active_source",
            ADVANCED_SECTION: {
                CONF_COMMAND_VALIDATION: "none",
                CONF_CONFIRMATION_TIMEOUT: 5,
                CONF_MAX_ATTEMPTS: 2,
            },
        },
    )

    assert result["type"] == "abort"
    updated = entry.subentries[subentry.subentry_id]
    assert updated.title == "Updated Switch"
    assert updated.data[CONF_FEATURE_POLICY] == "active_source"
