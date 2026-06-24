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
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_HIDE_SOURCES,
    CONF_RECOVERY_STABILITY,
    CONF_REPAIRS_DELAY,
    CONF_SELECTION_POLICY,
    CONF_SOURCES,
    DEFAULT_REPAIRS_DELAY,
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


@pytest.mark.asyncio
async def test_validate_allows_lights_with_different_color_modes(hass) -> None:
    """Light sources may expose different color capabilities."""

    hass.states.async_set(
        "light.matter",
        "on",
        {"supported_color_modes": ["color_temp"]},
    )
    hass.states.async_set(
        "light.cloud",
        "off",
        {"supported_color_modes": ["onoff"]},
    )

    assert (
        _validate_sources(hass, "light", ["light.matter", "light.cloud"], None) is None
    )


@pytest.mark.asyncio
async def test_validate_allows_covers_with_different_supported_features(hass) -> None:
    """Cover sources may expose different command capabilities."""

    hass.states.async_set(
        "cover.somfy",
        "closed",
        {"device_class": "shutter", "supported_features": 15},
    )
    hass.states.async_set(
        "cover.homekit",
        "closed",
        {"device_class": "shutter", "supported_features": 11},
    )

    assert (
        _validate_sources(
            hass,
            "cover",
            ["cover.somfy", "cover.homekit"],
            None,
        )
        is None
    )


def test_source_selectors_default_to_empty_lists() -> None:
    """Multiple entity selectors must never receive None as a default."""

    assert _user_schema()({})[CONF_SOURCES] == []


def test_advanced_settings_are_collapsed() -> None:
    """Advanced settings live in a collapsed section."""

    section = _user_schema().schema[ADVANCED_SECTION]

    assert isinstance(section, data_entry_flow.section)
    assert section.options["collapsed"] is True


def test_advanced_settings_hold_technical_choices() -> None:
    """Technical routing choices are kept out of the main form."""

    schema = _user_schema()
    section = schema.schema[ADVANCED_SECTION]

    assert CONF_FEATURE_POLICY not in schema.schema
    assert CONF_FEATURE_POLICY in section.schema.schema
    assert CONF_REPAIRS_DELAY in section.schema.schema


def test_repairs_delay_defaults_to_disabled() -> None:
    """Repairs alerts are opt-in while diagnostics remain available."""

    section = _user_schema().schema[ADVANCED_SECTION]

    assert section.schema({})[CONF_REPAIRS_DELAY] == DEFAULT_REPAIRS_DELAY


def test_advanced_selectors_use_translatable_labels() -> None:
    """Advanced selectors expose translation keys instead of raw values."""

    section = _user_schema().schema[ADVANCED_SECTION]
    feature_policy = section.schema.schema[CONF_FEATURE_POLICY]
    command_validation = section.schema.schema[CONF_COMMAND_VALIDATION]

    assert feature_policy.config["translation_key"] == CONF_FEATURE_POLICY
    assert command_validation.config["translation_key"] == CONF_COMMAND_VALIDATION
    assert command_validation.config["options"] == [
        "service_call",
        "state_confirmation",
    ]


@pytest.mark.asyncio
async def test_config_flow_creates_entry(hass) -> None:
    """The UI flow creates the service entry with a first failover subentry."""

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
            CONF_RECOVERY_STABILITY: 30,
            CONF_FAILURE_COOLDOWN: 60,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "intersection",
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 10,
                CONF_REPAIRS_DELAY: 0,
            },
        },
    )
    assert result["type"] == "create_entry"
    assert result["title"] == NAME
    assert result["data"] == {}
    subentry = next(iter(result["subentries"]))
    assert subentry["title"] == "Kitchen Switch"
    assert subentry["subentry_type"] == SUBENTRY_TYPE_FAILOVER
    assert subentry["data"][CONF_DOMAIN] == "switch"
    assert subentry["data"][CONF_SELECTION_POLICY] == "static_priority"
    assert set(subentry["data"]) == {
        "name",
        CONF_DOMAIN,
        CONF_SOURCES,
        CONF_COMMAND_VALIDATION,
        CONF_CONFIRMATION_TIMEOUT,
        CONF_FAILURE_COOLDOWN,
        CONF_RECOVERY_STABILITY,
        CONF_FEATURE_POLICY,
        CONF_HIDE_SOURCES,
        CONF_REPAIRS_DELAY,
        CONF_SELECTION_POLICY,
    }


@pytest.mark.asyncio
async def test_config_flow_manager_creates_entry_from_single_form(hass) -> None:
    """Home Assistant's flow manager creates a service entry with a subentry."""

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
            CONF_RECOVERY_STABILITY: 30,
            CONF_FAILURE_COOLDOWN: 60,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "intersection",
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 10,
                CONF_REPAIRS_DELAY: 0,
            },
        },
    )

    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.title == NAME
    assert len(entry.subentries) == 1
    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Kitchen Switch"
    assert subentry.data[CONF_DOMAIN] == "switch"
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
            CONF_RECOVERY_STABILITY: 15,
            CONF_FAILURE_COOLDOWN: 45,
            CONF_HIDE_SOURCES: True,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "active_source",
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 5,
                CONF_REPAIRS_DELAY: 1200,
            },
        },
    )

    assert result["type"] == "create_entry"
    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Kitchen Switch"
    assert result["data"][CONF_RECOVERY_STABILITY] == 15
    assert result["data"][CONF_HIDE_SOURCES] is True
    assert result["data"][CONF_COMMAND_VALIDATION] == "service_call"
    assert result["data"][CONF_REPAIRS_DELAY] == 1200


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
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                    CONF_REPAIRS_DELAY: 0,
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
            CONF_RECOVERY_STABILITY: 20,
            CONF_FAILURE_COOLDOWN: 40,
            CONF_HIDE_SOURCES: True,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "active_source",
                CONF_COMMAND_VALIDATION: "state_confirmation",
                CONF_CONFIRMATION_TIMEOUT: 5,
                CONF_REPAIRS_DELAY: 600,
            },
        },
    )

    assert result["type"] == "abort"
    updated = entry.subentries[subentry.subentry_id]
    assert updated.title == "Updated Switch"
    assert updated.data[CONF_HIDE_SOURCES] is True
    assert updated.data[CONF_FEATURE_POLICY] == "active_source"
    assert updated.data[CONF_REPAIRS_DELAY] == 600


@pytest.mark.asyncio
async def test_subentry_flow_reorders_sources_with_update_listener(hass) -> None:
    """Reordering sources works after the integration entry has been set up."""

    hass.states.async_set("light.one", "on", {"supported_color_modes": ["brightness"]})
    hass.states.async_set("light.two", "off", {"supported_color_modes": ["brightness"]})
    hass.states.async_set(
        "light.three", "off", {"supported_color_modes": ["brightness"]}
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Living Room Light",
                    CONF_DOMAIN: "light",
                    CONF_SOURCES: ["light.one", "light.two", "light.three"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                    CONF_REPAIRS_DELAY: DEFAULT_REPAIRS_DELAY,
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Living Room Light",
                "unique_id": "unique-light-subentry",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))

    async def _update_listener(*_) -> None:
        pass

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_FAILOVER),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["type"] == "form"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Living Room Light",
            CONF_SOURCES: ["light.three", "light.one", "light.two"],
            CONF_RECOVERY_STABILITY: 30,
            CONF_FAILURE_COOLDOWN: 60,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "intersection",
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 10,
                CONF_REPAIRS_DELAY: DEFAULT_REPAIRS_DELAY,
            },
        },
    )

    assert result["type"] == "abort"
    updated = entry.subentries[subentry.subentry_id]
    assert updated.data[CONF_SOURCES] == ["light.three", "light.one", "light.two"]


@pytest.mark.asyncio
async def test_config_flow_supports_lowest_latency_policy(hass) -> None:
    """The config flow allows selecting lowest_latency selection policy."""

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
            CONF_SELECTION_POLICY: "lowest_latency",
            CONF_RECOVERY_STABILITY: 30,
            CONF_FAILURE_COOLDOWN: 60,
            ADVANCED_SECTION: {
                CONF_FEATURE_POLICY: "intersection",
                CONF_COMMAND_VALIDATION: "service_call",
                CONF_CONFIRMATION_TIMEOUT: 10,
                CONF_REPAIRS_DELAY: 0,
            },
        },
    )
    assert result["type"] == "create_entry"
    subentry = next(iter(result["subentries"]))
    assert subentry["data"][CONF_SELECTION_POLICY] == "lowest_latency"
