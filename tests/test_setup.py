"""Tests for integration setup and unload."""

from __future__ import annotations

import pytest
from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    FanEntityFeature,
)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.components.number import ATTR_MAX, ATTR_MIN, ATTR_MODE, ATTR_STEP
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_failover.const import (
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DOMAIN,
    NAME,
    SUBENTRY_TYPE_FAILOVER,
)


@pytest.mark.asyncio
async def test_setup_and_unload_entry(hass) -> None:
    """A config entry can be set up and unloaded."""

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
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Kitchen Switch",
                "unique_id": "unique-setup",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "unique-setup" in hass.data[DOMAIN]
    registry_entry = er.async_get(hass).async_get("switch.kitchen_switch")
    assert registry_entry is not None
    assert registry_entry.config_subentry_id == subentry.subentry_id

    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_setup_light_entity_exposes_light_state(hass) -> None:
    """A light failover entity exposes the Home Assistant light contract."""

    hass.states.async_set(
        "light.one",
        "on",
        {
            ATTR_BRIGHTNESS: 120,
            ATTR_COLOR_MODE: ColorMode.BRIGHTNESS,
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS],
        },
    )
    hass.states.async_set(
        "light.two",
        "off",
        {
            ATTR_COLOR_MODE: None,
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS],
        },
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
                    CONF_SOURCES: ["light.one", "light.two"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Living Room Light",
                "unique_id": "unique-light-setup",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("light.living_room_light")
    assert state is not None
    assert state.state == "on"
    assert state.attributes[ATTR_BRIGHTNESS] == 120
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.BRIGHTNESS
    assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]

    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: "light.living_room_light", ATTR_BRIGHTNESS: 200},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_setup_light_entity_keeps_native_light_attributes(hass) -> None:
    """A light failover entity lets Home Assistant derive native attributes."""

    hass.states.async_set(
        "light.one",
        "off",
        {
            ATTR_BRIGHTNESS: 120,
            ATTR_COLOR_MODE: ColorMode.BRIGHTNESS,
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS],
        },
    )
    hass.states.async_set(
        "light.two",
        STATE_UNAVAILABLE,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS],
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Bedroom Light",
                    CONF_DOMAIN: "light",
                    CONF_SOURCES: ["light.one", "light.two"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Bedroom Light",
                "unique_id": "unique-light-native-attrs",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("light.bedroom_light")
    assert state is not None
    assert state.state == "off"
    assert state.attributes[ATTR_COLOR_MODE] is None
    assert state.attributes[ATTR_BRIGHTNESS] is None


@pytest.mark.asyncio
async def test_setup_light_entity_without_available_source(hass) -> None:
    """A light failover entity can be added before any source is available."""

    hass.states.async_set("light.one", STATE_UNAVAILABLE)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Unavailable Light",
                    CONF_DOMAIN: "light",
                    CONF_SOURCES: ["light.one"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Unavailable Light",
                "unique_id": "unique-light-unavailable",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("light.unavailable_light")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    active_source = hass.states.get("sensor.unavailable_light_active_source")
    assert active_source is not None
    assert active_source.state == STATE_UNKNOWN

    degraded = hass.states.get("binary_sensor.unavailable_light_degraded")
    assert degraded is not None
    assert degraded.state != STATE_UNAVAILABLE

    clear_failures = hass.states.get("button.unavailable_light_clear_failures")
    assert clear_failures is not None
    assert clear_failures.state != STATE_UNAVAILABLE


@pytest.mark.asyncio
async def test_setup_fan_entity_exposes_native_fan_attributes(hass) -> None:
    """A fan failover entity exposes attributes through FanEntity."""

    supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.DIRECTION
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.PRESET_MODE
    )
    hass.states.async_set(
        "fan.one",
        "on",
        {
            ATTR_DIRECTION: "forward",
            ATTR_OSCILLATING: True,
            ATTR_PERCENTAGE: 42,
            ATTR_PERCENTAGE_STEP: 7,
            ATTR_PRESET_MODE: "auto",
            ATTR_PRESET_MODES: ["auto", "sleep"],
            ATTR_SUPPORTED_FEATURES: supported_features,
        },
    )
    hass.states.async_set(
        "fan.two",
        STATE_UNAVAILABLE,
        {
            ATTR_PRESET_MODES: ["auto", "sleep"],
            ATTR_SUPPORTED_FEATURES: supported_features,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Ceiling Fan",
                    CONF_DOMAIN: "fan",
                    CONF_SOURCES: ["fan.one", "fan.two"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Ceiling Fan",
                "unique_id": "unique-fan-native-attrs",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("fan.ceiling_fan")
    assert state is not None
    assert state.state == "on"
    assert state.attributes[ATTR_DIRECTION] == "forward"
    assert state.attributes[ATTR_OSCILLATING] is True
    assert state.attributes[ATTR_PERCENTAGE] == 42
    assert state.attributes[ATTR_PERCENTAGE_STEP] == 7
    assert state.attributes[ATTR_PRESET_MODE] == "auto"
    assert state.attributes[ATTR_PRESET_MODES] == ["auto", "sleep"]


@pytest.mark.asyncio
async def test_setup_number_entity_exposes_number_contract(hass) -> None:
    """A number failover entity exposes the Home Assistant number contract."""

    hass.states.async_set(
        "number.one",
        "16",
        {
            ATTR_MIN: 0,
            ATTR_MAX: 32,
            ATTR_STEP: 1,
            ATTR_MODE: "slider",
        },
    )
    hass.states.async_set(
        "number.two",
        "8",
        {
            ATTR_MIN: 0,
            ATTR_MAX: 32,
            ATTR_STEP: 1,
            ATTR_MODE: "slider",
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Charging Amps",
                    CONF_DOMAIN: "number",
                    CONF_SOURCES: ["number.one", "number.two"],
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Charging Amps",
                "unique_id": "unique-number-setup",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("number.charging_amps")
    assert state is not None
    assert state.state == "16.0"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 32
    assert state.attributes[ATTR_STEP] == 1
    assert state.attributes[ATTR_MODE] == "slider"

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: "number.charging_amps", "value": 20},
        blocking=True,
    )
