"""Tests for generic domain-specific entity failover contracts."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.components.air_quality import (
    ATTR_PM_2_5,
    AirQualityEntity,
)
from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.calendar import CalendarEntity
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.cover import CoverEntity
from homeassistant.components.date import DateEntity
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.humidifier import HumidifierEntity
from homeassistant.components.image import ImageEntity
from homeassistant.components.lawn_mower import LawnMowerEntity
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
    LightEntity,
)
from homeassistant.components.lock import LockEntity
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_STEP,
    NumberEntity,
)
from homeassistant.components.remote import RemoteEntity
from homeassistant.components.scene import Scene
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.siren import SirenEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.text import TextEntity
from homeassistant.components.time import TimeEntity
from homeassistant.components.todo import TodoListEntity
from homeassistant.components.update import UpdateEntity
from homeassistant.components.vacuum import StateVacuumEntity
from homeassistant.components.valve import ValveEntity
from homeassistant.components.water_heater import WaterHeaterEntity
from homeassistant.components.weather import WeatherEntity
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_failover.adapters import adapter_for_domain
from custom_components.entity_failover.const import (
    COMMANDABLE_DOMAINS,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DOMAIN,
    NAME,
    READ_ONLY_DOMAINS,
    SPECIALIZED_DOMAINS,
    SUBENTRY_TYPE_FAILOVER,
    SUPPORTED_DOMAINS,
)
from custom_components.entity_failover.entities.base import FailoverEntityMixin
from custom_components.entity_failover.entities.domain_contracts import (
    FailoverGenericMainEntity,
)
from custom_components.entity_failover.entities.domains import DOMAIN_ENTITY_CLASSES

ATTR_AIR_QUALITY_INDEX = "air_quality_index"

EXPECTED_NATIVE_ENTITY_CLASSES = {
    "air_quality": AirQualityEntity,
    "alarm_control_panel": AlarmControlPanelEntity,
    "binary_sensor": BinarySensorEntity,
    "button": ButtonEntity,
    "calendar": CalendarEntity,
    "climate": ClimateEntity,
    "cover": CoverEntity,
    "date": DateEntity,
    "datetime": DateTimeEntity,
    "device_tracker": TrackerEntity,
    "fan": FanEntity,
    "humidifier": HumidifierEntity,
    "image": ImageEntity,
    "lawn_mower": LawnMowerEntity,
    "light": LightEntity,
    "lock": LockEntity,
    "media_player": MediaPlayerEntity,
    "number": NumberEntity,
    "remote": RemoteEntity,
    "scene": Scene,
    "select": SelectEntity,
    "sensor": SensorEntity,
    "siren": SirenEntity,
    "switch": SwitchEntity,
    "text": TextEntity,
    "time": TimeEntity,
    "todo": TodoListEntity,
    "update": UpdateEntity,
    "vacuum": StateVacuumEntity,
    "valve": ValveEntity,
    "water_heater": WaterHeaterEntity,
    "weather": WeatherEntity,
}


def _expected_native_entity_class(domain: str) -> type[object]:
    """Return the native HA entity class for a domain."""

    _skip_missing_domain_dependencies(domain)
    if domain == "camera":
        return import_module("homeassistant.components.camera").Camera
    return EXPECTED_NATIVE_ENTITY_CLASSES[domain]


def _skip_missing_domain_dependencies(domain: str) -> None:
    """Skip tests for HA platforms whose optional dependencies are absent."""

    if domain == "camera":
        pytest.importorskip(
            "turbojpeg",
            reason="Home Assistant camera support requires turbojpeg",
        )


def _entry_for_domain(domain: str, attrs: dict[str, object]) -> MockConfigEntry:
    name = f"Smoke {domain.replace('_', ' ').title()}"
    return MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=f"entry-{domain}",
        data={},
        subentries_data=[
            {
                "data": {
                    "name": name,
                    CONF_DOMAIN: domain,
                    CONF_SOURCES: [f"{domain}.one", f"{domain}.two"],
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": name,
                "unique_id": f"unique-{domain}",
            }
        ],
        version=2,
    )


def _source_attrs_for_domain(domain: str) -> dict[str, object]:
    base: dict[str, object] = {ATTR_SUPPORTED_FEATURES: 0}
    return base | {
        "air_quality": {ATTR_AIR_QUALITY_INDEX: 42, ATTR_PM_2_5: 12.5},
        "binary_sensor": {ATTR_DEVICE_CLASS: "motion"},
        "climate": {
            "hvac_modes": ["off", "heat"],
            "temperature_unit": UnitOfTemperature.CELSIUS,
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
        "cover": {"current_position": 50},
        "device_tracker": {"source_type": "router"},
        "fan": {
            "percentage": 50,
            "percentage_step": 10,
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.SET_SPEED,
        },
        "humidifier": {"available_modes": ["normal"]},
        "light": {
            ATTR_BRIGHTNESS: 100,
            ATTR_COLOR_MODE: ColorMode.BRIGHTNESS,
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS],
        },
        "media_player": {
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SHUFFLE_SET,
        },
        "number": {ATTR_MIN: 0, ATTR_MAX: 100, ATTR_STEP: 1, ATTR_MODE: "auto"},
        "select": {"options": ["one", "two"], "current_option": "one"},
        "sensor": {
            ATTR_DEVICE_CLASS: "temperature",
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
        },
        "text": {"min": 0, "max": 255, "mode": "text"},
        "weather": {"temperature_unit": UnitOfTemperature.CELSIUS},
        "water_heater": {
            "operation_list": ["off", "eco"],
            "operation_mode": "eco",
            "temperature_unit": UnitOfTemperature.CELSIUS,
        },
    }.get(domain, base)


def _source_state_for_domain(domain: str) -> str:
    return {
        "alarm_control_panel": "disarmed",
        "binary_sensor": "off",
        "button": "unknown",
        "calendar": "off",
        "camera": "idle",
        "climate": "heat",
        "cover": "open",
        "device_tracker": "home",
        "fan": "on",
        "humidifier": "on",
        "image": "2026-06-17T12:00:00+00:00",
        "lawn_mower": "docked",
        "light": "on",
        "lock": "locked",
        "media_player": "idle",
        "remote": "on",
        "scene": "2026-06-17T12:00:00+00:00",
        "siren": "off",
        "switch": "on",
        "todo": "0",
        "update": "off",
        "vacuum": "docked",
        "valve": "open",
        "water_heater": "eco",
        "weather": "sunny",
    }.get(domain, "1")


def test_every_supported_domain_has_native_entity() -> None:
    """Every supported domain must map to its native Home Assistant contract."""

    assert sorted(DOMAIN_ENTITY_CLASSES) == SUPPORTED_DOMAINS
    for domain in SUPPORTED_DOMAINS:
        if domain == "camera" and find_spec("turbojpeg") is None:
            continue
        entity_cls = DOMAIN_ENTITY_CLASSES[domain]
        assert entity_cls is not FailoverGenericMainEntity
        assert issubclass(entity_cls, _expected_native_entity_class(domain))


@pytest.mark.parametrize("domain", COMMANDABLE_DOMAINS)
def test_commandable_route_methods_override_native_contract(domain: str) -> None:
    """Commandable services must be handled by failover route mixins."""

    entity_cls = DOMAIN_ENTITY_CLASSES[domain]
    native_cls = _expected_native_entity_class(domain)
    native_index = entity_cls.mro().index(native_cls)
    failover_route_mro = entity_cls.mro()[:native_index]

    for method_name in adapter_for_domain(domain).services:
        assert any(method_name in cls.__dict__ for cls in failover_route_mro), (
            f"{domain}.{method_name} is not implemented before {native_cls.__name__}"
        )


def test_limited_domains_are_explicitly_read_only() -> None:
    """Specialized/heavy domains are supported as read-only mirrors for now."""

    for domain in READ_ONLY_DOMAINS + SPECIALIZED_DOMAINS:
        assert adapter_for_domain(domain).read_only
    for domain in COMMANDABLE_DOMAINS:
        assert not adapter_for_domain(domain).read_only


@pytest.mark.parametrize("domain", SUPPORTED_DOMAINS)
@pytest.mark.asyncio
async def test_supported_domain_can_be_set_up(hass: HomeAssistant, domain: str) -> None:
    """Every advertised domain can create a native failover entity."""

    _skip_missing_domain_dependencies(domain)
    attrs = _source_attrs_for_domain(domain)
    hass.states.async_set(f"{domain}.one", _source_state_for_domain(domain), attrs)
    hass.states.async_set(f"{domain}.two", _source_state_for_domain(domain), attrs)
    entry = _entry_for_domain(domain, attrs)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.smoke_{domain}")
    assert state is not None
    if domain != "button":
        assert state.attributes["forwarded_entity_id"] == f"{domain}.one"

    assert await hass.config_entries.async_unload(entry.entry_id)


def test_active_attribute_fallback_preserves_falsy_values(hass: HomeAssistant) -> None:
    """Active source attributes only fall back when the active value is absent."""

    hass.states.async_set(
        "sensor.primary",
        "ok",
        {"false_value": False, "zero_value": 0, "empty_value": []},
    )
    hass.states.async_set(
        "sensor.backup",
        "ok",
        {"false_value": True, "zero_value": 10, "empty_value": ["backup"]},
    )
    manager = SimpleNamespace(
        active_state=hass.states.get("sensor.primary"),
        config=SimpleNamespace(
            unique_id="dummy",
            name="Dummy",
            sources=("sensor.primary", "sensor.backup"),
        ),
        hass=hass,
    )
    entity = FailoverEntityMixin(manager)

    assert entity._active_or_source_attribute("false_value") is False
    assert entity._active_or_source_attribute("zero_value") == 0
    assert entity._active_or_source_attribute("empty_value") == []


@pytest.mark.asyncio
async def test_air_quality_uses_native_property_names(hass: HomeAssistant) -> None:
    """Air quality values are exposed through AirQualityEntity native attrs."""

    hass.states.async_set(
        "air_quality.one",
        "12.5",
        {
            ATTR_AIR_QUALITY_INDEX: 42,
            ATTR_PM_2_5: 12.5,
            "carbon_dioxide": 500,
        },
    )
    hass.states.async_set(
        "air_quality.two",
        "10",
        {
            ATTR_AIR_QUALITY_INDEX: 42,
            ATTR_PM_2_5: 10,
            "carbon_dioxide": 500,
        },
    )
    entry = _entry_for_domain(
        "air_quality",
        {ATTR_AIR_QUALITY_INDEX: 42, ATTR_PM_2_5: 12.5},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("air_quality.smoke_air_quality")
    assert state is not None
    assert state.state == "12.5"
    assert state.attributes[ATTR_AIR_QUALITY_INDEX] == 42
    assert state.attributes["carbon_dioxide"] == 500

    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_media_player_shuffle_service_uses_ha_method_name(
    hass: HomeAssistant,
) -> None:
    """media_player.shuffle_set must route through async_set_shuffle."""

    calls: list[dict[str, object]] = []
    original_async_call = hass.services.async_call

    async def mock_async_call(self, domain, service, service_data, *args, **kwargs):
        if (
            domain == "media_player"
            and service == "shuffle_set"
            and service_data.get(ATTR_ENTITY_ID) == "media_player.one"
        ):
            calls.append(dict(service_data))
            return None
        return await original_async_call(domain, service, service_data, *args, **kwargs)

    attrs = {
        ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SHUFFLE_SET,
    }
    hass.states.async_set("media_player.one", "idle", attrs)
    hass.states.async_set("media_player.two", "idle", attrs)
    entry = _entry_for_domain("media_player", attrs)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
        await hass.services.async_call(
            "media_player",
            "shuffle_set",
            {ATTR_ENTITY_ID: "media_player.smoke_media_player", "shuffle": True},
            blocking=True,
        )

    assert calls == [
        {
            ATTR_ENTITY_ID: "media_player.one",
            "shuffle": True,
        }
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_number_state_confirmation(hass: HomeAssistant) -> None:
    """NumberEntity set_value confirms through entity state, not value attr."""

    original_async_call = hass.services.async_call

    async def mock_async_call(self, domain, service, service_data, *args, **kwargs):
        if domain == "number" and service == "set_value":
            entity_id = service_data.get("entity_id")
            if entity_id in ["number.one", "number.two"]:
                hass.states.async_set(entity_id, str(float(service_data["value"])))
                return None
        return await original_async_call(domain, service, service_data, *args, **kwargs)

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
        hass.states.async_set("number.one", "12.0", {ATTR_MIN: 0, ATTR_MAX: 20})
        hass.states.async_set("number.two", "12.0", {ATTR_MIN: 0, ATTR_MAX: 20})

        entry = MockConfigEntry(
            domain=DOMAIN,
            title=NAME,
            unique_id=DOMAIN,
            data={},
            subentries_data=[
                {
                    "data": {
                        "name": "Test Number",
                        CONF_DOMAIN: "number",
                        CONF_SOURCES: ["number.one", "number.two"],
                        CONF_FAILURE_COOLDOWN: 60,
                        CONF_RECOVERY_STABILITY: 30,
                        CONF_FEATURE_POLICY: "intersection",
                    },
                    "subentry_type": SUBENTRY_TYPE_FAILOVER,
                    "title": "Test Number",
                    "unique_id": "unique-test-number",
                }
            ],
            version=2,
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.test_number", "value": 15},
            blocking=True,
        )

        manager = hass.data[DOMAIN]["unique-test-number"]
        assert manager.last_command_result is not None
        assert manager.last_command_result.success

        assert await hass.config_entries.async_unload(entry.entry_id)
