"""Domain adapters for Entity Failover."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError

from .const import SUPPORTED_DOMAINS
from .helpers import state_supported_features

CONFIRM_UNSUPPORTED = object()


@dataclass(slots=True, frozen=True)
class ConfirmationRule:
    """State confirmation rule for one service."""

    states: tuple[str, ...] = ()
    attribute: str | None = None
    data_key: str | None = None
    state_value: bool = False
    tolerance: float = 0.0
    opposite: bool = False
    unsupported: bool = False


@dataclass(slots=True)
class DomainAdapter:
    """Declarative behavior for one Home Assistant domain."""

    domain: str
    services: Mapping[str, str] = field(default_factory=dict)
    read_only: bool = False
    feature_attribute: str = "supported_features"
    compatibility_attributes: tuple[str, ...] = ()
    passthrough_attributes: tuple[str, ...] = ()
    confirmation: Mapping[str, ConfirmationRule] = field(default_factory=dict)

    def supports_service(self, service: str) -> bool:
        """Return whether the adapter knows how to route a service."""

        return service in self.services.values() or service in self.services

    def service_name(self, method_name: str) -> str:
        """Return the service name for a platform method."""

        return self.services.get(method_name, method_name)

    def supported_features(self, state: State | None) -> int:
        """Return supported features from a source state."""

        return state_supported_features(state)

    def source_supports_features(self, state: State | None, features: int) -> bool:
        """Return whether a source supports all requested features."""

        if features == 0:
            return True
        return bool(self.supported_features(state) & features == features)

    def validate_sources(self, hass: HomeAssistant, sources: list[str]) -> str | None:
        """Validate compatibility between configured sources."""

        states = [hass.states.get(source) for source in sources]
        for attr in self.compatibility_attributes:
            values = {
                state.attributes.get(attr)
                for state in states
                if state is not None and state.attributes.get(attr) is not None
            }
            normalized = {
                tuple(value) if isinstance(value, list) else value for value in values
            }
            if len(normalized) > 1:
                return f"incompatible_{attr}"
        return None

    def expected_result(  # noqa: PLR0911
        self,
        service: str,
        before: State | None,
        data: Mapping[str, Any],
    ) -> ConfirmationRule | object:
        """Return a confirmation rule for a service call."""

        rule = self.confirmation.get(service)
        if rule is None or rule.unsupported:
            return CONFIRM_UNSUPPORTED
        if rule.opposite and before is not None:
            if before.state == "on":
                return ConfirmationRule(states=("off",))
            if before.state == "off":
                return ConfirmationRule(states=("on",))
            return CONFIRM_UNSUPPORTED
        if service == "set_cover_position" and "position" in data:
            return ConfirmationRule(
                attribute="current_position",
                tolerance=2.0,
            )
        if service == "set_percentage" and "percentage" in data:
            return ConfirmationRule(
                attribute="percentage",
                tolerance=2.0,
            )
        if service == "set_preset_mode" and "preset_mode" in data:
            return ConfirmationRule(attribute="preset_mode")
        if service == "set_value" and "value" in data:
            if self.domain == "number":
                return ConfirmationRule(
                    data_key="value",
                    state_value=True,
                    tolerance=0.001,
                )
            return ConfirmationRule(attribute="value", tolerance=0.001)
        if service in {"select_option", "set_preset_mode"}:
            return ConfirmationRule(attribute="current_option")
        return rule

    def confirmation_matches(  # noqa: PLR0911
        self,
        rule: ConfirmationRule,
        state: State | None,
        data: Mapping[str, Any],
    ) -> bool:
        """Return whether a state satisfies a confirmation rule."""

        if state is None:
            return False
        if rule.states and state.state in rule.states:
            return True
        if rule.state_value:
            actual = state.state
        elif rule.attribute is not None:
            actual = state.attributes.get(rule.attribute)
        else:
            return False

        expected = data.get(rule.data_key) if rule.data_key is not None else None
        if expected is None and rule.attribute is not None:
            expected = data.get(_expected_data_key(rule.attribute))
        if expected is None and rule.attribute is not None:
            expected = data.get(rule.attribute)
        if expected is None:
            return actual is not None
        if actual is None:
            return False
        if rule.tolerance:
            try:
                return abs(float(actual) - float(expected)) <= rule.tolerance
            except (TypeError, ValueError):
                pass
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return abs(float(actual) - float(expected)) <= rule.tolerance
        return actual == expected

    def unsupported_service_error(
        self, service: str, source: str
    ) -> HomeAssistantError:
        """Build a clear unsupported service error."""

        message = (
            f"{source} does not support {self.domain}.{service} "
            "for this failover entity"
        )
        return HomeAssistantError(message)


def _expected_data_key(attribute: str) -> str:
    """Map common state attributes to service data keys."""

    return {
        "current_position": "position",
        "percentage": "percentage",
        "preset_mode": "preset_mode",
        "current_option": "option",
        "value": "value",
    }.get(attribute, attribute)


def _adapter(
    domain: str,
    services: Mapping[str, str] | None = None,
    *,
    read_only: bool = False,
    compatibility_attributes: tuple[str, ...] = (),
    passthrough_attributes: tuple[str, ...] = (),
    confirmation: Mapping[str, ConfirmationRule] | None = None,
) -> DomainAdapter:
    return DomainAdapter(
        domain=domain,
        services=services or {},
        read_only=read_only,
        compatibility_attributes=compatibility_attributes,
        passthrough_attributes=passthrough_attributes,
        confirmation=confirmation or {},
    )


ADAPTERS: dict[str, DomainAdapter] = {
    "alarm_control_panel": _adapter(
        "alarm_control_panel",
        {
            "async_alarm_disarm": "alarm_disarm",
            "async_alarm_arm_home": "alarm_arm_home",
            "async_alarm_arm_away": "alarm_arm_away",
            "async_alarm_arm_night": "alarm_arm_night",
            "async_alarm_arm_vacation": "alarm_arm_vacation",
            "async_alarm_arm_custom_bypass": "alarm_arm_custom_bypass",
            "async_alarm_trigger": "alarm_trigger",
        },
        passthrough_attributes=("code_format", "changed_by"),
    ),
    "air_quality": _adapter("air_quality", read_only=True),
    "binary_sensor": _adapter(
        "binary_sensor",
        read_only=True,
        compatibility_attributes=("device_class",),
        passthrough_attributes=("device_class",),
    ),
    "button": _adapter("button", {"async_press": "press"}),
    "calendar": _adapter("calendar", read_only=True),
    "camera": _adapter("camera", read_only=True),
    "climate": _adapter(
        "climate",
        {
            "async_set_temperature": "set_temperature",
            "async_set_hvac_mode": "set_hvac_mode",
            "async_set_preset_mode": "set_preset_mode",
            "async_set_fan_mode": "set_fan_mode",
            "async_set_humidity": "set_humidity",
            "async_set_swing_mode": "set_swing_mode",
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
        },
        passthrough_attributes=(
            "current_temperature",
            "temperature",
            "target_temp_high",
            "target_temp_low",
            "hvac_modes",
            "hvac_action",
            "preset_mode",
            "preset_modes",
            "fan_mode",
            "fan_modes",
            "swing_mode",
            "swing_modes",
            "current_humidity",
            "target_humidity",
        ),
    ),
    "cover": _adapter(
        "cover",
        {
            "async_open_cover": "open_cover",
            "async_close_cover": "close_cover",
            "async_stop_cover": "stop_cover",
            "async_set_cover_position": "set_cover_position",
            "async_open_cover_tilt": "open_cover_tilt",
            "async_close_cover_tilt": "close_cover_tilt",
            "async_stop_cover_tilt": "stop_cover_tilt",
            "async_set_cover_tilt_position": "set_cover_tilt_position",
        },
        passthrough_attributes=(
            "current_position",
            "current_tilt_position",
            "device_class",
        ),
        confirmation={
            "open_cover": ConfirmationRule(states=("open", "opening")),
            "close_cover": ConfirmationRule(states=("closed", "closing")),
            "stop_cover": ConfirmationRule(unsupported=True),
            "set_cover_position": ConfirmationRule(
                attribute="current_position", tolerance=2.0
            ),
        },
    ),
    "date": _adapter(
        "date", {"async_set_value": "set_value"}, passthrough_attributes=("date",)
    ),
    "datetime": _adapter(
        "datetime",
        {"async_set_value": "set_value"},
        passthrough_attributes=("datetime",),
    ),
    "device_tracker": _adapter(
        "device_tracker",
        read_only=True,
        passthrough_attributes=("source_type", "latitude", "longitude", "gps_accuracy"),
    ),
    "fan": _adapter(
        "fan",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
            "async_set_percentage": "set_percentage",
            "async_increase_speed": "increase_speed",
            "async_decrease_speed": "decrease_speed",
            "async_oscillate": "oscillate",
            "async_set_direction": "set_direction",
            "async_set_preset_mode": "set_preset_mode",
        },
        passthrough_attributes=(
            "percentage",
            "percentage_step",
            "preset_mode",
            "preset_modes",
            "oscillating",
            "direction",
        ),
        confirmation={
            "turn_on": ConfirmationRule(states=("on",)),
            "turn_off": ConfirmationRule(states=("off",)),
            "toggle": ConfirmationRule(opposite=True),
            "set_percentage": ConfirmationRule(attribute="percentage", tolerance=2.0),
            "set_preset_mode": ConfirmationRule(attribute="preset_mode"),
            "oscillate": ConfirmationRule(unsupported=True),
            "set_direction": ConfirmationRule(unsupported=True),
            "increase_speed": ConfirmationRule(unsupported=True),
            "decrease_speed": ConfirmationRule(unsupported=True),
        },
    ),
    "humidifier": _adapter(
        "humidifier",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_set_humidity": "set_humidity",
            "async_set_mode": "set_mode",
        },
    ),
    "image": _adapter("image", read_only=True),
    "lawn_mower": _adapter(
        "lawn_mower",
        {
            "async_start_mowing": "start_mowing",
            "async_pause": "pause",
            "async_dock": "dock",
        },
    ),
    "light": _adapter(
        "light",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
        },
        passthrough_attributes=(
            "brightness",
            "color_mode",
            "supported_color_modes",
            "color_temp_kelvin",
            "hs_color",
            "rgb_color",
            "xy_color",
            "effect",
            "effect_list",
        ),
        confirmation={
            "turn_on": ConfirmationRule(states=("on",)),
            "turn_off": ConfirmationRule(states=("off",)),
            "toggle": ConfirmationRule(opposite=True),
        },
    ),
    "lock": _adapter(
        "lock",
        {
            "async_lock": "lock",
            "async_unlock": "unlock",
            "async_open": "open",
        },
        confirmation={
            "lock": ConfirmationRule(states=("locked", "locking")),
            "unlock": ConfirmationRule(states=("unlocked", "unlocking")),
            "open": ConfirmationRule(states=("open", "opening", "unlocked")),
        },
    ),
    "media_player": _adapter(
        "media_player",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
            "async_media_play": "media_play",
            "async_media_pause": "media_pause",
            "async_media_stop": "media_stop",
            "async_media_next_track": "media_next_track",
            "async_media_previous_track": "media_previous_track",
            "async_set_volume_level": "volume_set",
            "async_mute_volume": "volume_mute",
            "async_select_source": "select_source",
            "async_select_sound_mode": "select_sound_mode",
            "async_play_media": "play_media",
            "async_clear_playlist": "clear_playlist",
            "async_shuffle_set": "shuffle_set",
            "async_repeat_set": "repeat_set",
        },
        passthrough_attributes=(
            "media_title",
            "media_artist",
            "media_album_name",
            "media_content_type",
            "volume_level",
            "is_volume_muted",
            "source",
            "source_list",
            "sound_mode",
            "sound_mode_list",
        ),
    ),
    "number": _adapter(
        "number",
        {"async_set_native_value": "set_value"},
        passthrough_attributes=("min", "max", "step", "mode", "unit_of_measurement"),
        confirmation={
            "set_value": ConfirmationRule(
                data_key="value",
                state_value=True,
                tolerance=0.001,
            )
        },
    ),
    "remote": _adapter(
        "remote",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
            "async_send_command": "send_command",
            "async_learn_command": "learn_command",
            "async_delete_command": "delete_command",
        },
    ),
    "scene": _adapter("scene", {"async_activate": "turn_on"}),
    "select": _adapter(
        "select",
        {"async_select_option": "select_option"},
        passthrough_attributes=("options", "current_option"),
        confirmation={"select_option": ConfirmationRule(attribute="current_option")},
    ),
    "sensor": _adapter(
        "sensor",
        read_only=True,
        compatibility_attributes=("device_class", "state_class", "unit_of_measurement"),
        passthrough_attributes=(
            "device_class",
            "state_class",
            "unit_of_measurement",
            "suggested_display_precision",
            "options",
        ),
    ),
    "siren": _adapter(
        "siren",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
        },
        confirmation={
            "turn_on": ConfirmationRule(states=("on",)),
            "turn_off": ConfirmationRule(states=("off",)),
            "toggle": ConfirmationRule(opposite=True),
        },
    ),
    "switch": _adapter(
        "switch",
        {
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
            "async_toggle": "toggle",
        },
        confirmation={
            "turn_on": ConfirmationRule(states=("on",)),
            "turn_off": ConfirmationRule(states=("off",)),
            "toggle": ConfirmationRule(opposite=True),
        },
    ),
    "text": _adapter(
        "text",
        {"async_set_value": "set_value"},
        passthrough_attributes=("min", "max", "mode", "pattern"),
    ),
    "time": _adapter(
        "time", {"async_set_value": "set_value"}, passthrough_attributes=("time",)
    ),
    "todo": _adapter("todo", read_only=True),
    "update": _adapter(
        "update",
        {
            "async_install": "install",
            "async_skip": "skip",
            "async_clear_skipped": "clear_skipped",
        },
        passthrough_attributes=(
            "installed_version",
            "latest_version",
            "release_summary",
        ),
    ),
    "vacuum": _adapter(
        "vacuum",
        {
            "async_start": "start",
            "async_pause": "pause",
            "async_stop": "stop",
            "async_return_to_base": "return_to_base",
            "async_clean_spot": "clean_spot",
            "async_locate": "locate",
            "async_set_fan_speed": "set_fan_speed",
            "async_send_command": "send_command",
        },
        passthrough_attributes=("battery_level", "fan_speed", "fan_speed_list"),
    ),
    "valve": _adapter(
        "valve",
        {
            "async_open_valve": "open_valve",
            "async_close_valve": "close_valve",
            "async_set_valve_position": "set_valve_position",
            "async_stop_valve": "stop_valve",
        },
        passthrough_attributes=("current_position", "device_class"),
    ),
    "water_heater": _adapter(
        "water_heater",
        {
            "async_set_temperature": "set_temperature",
            "async_set_operation_mode": "set_operation_mode",
            "async_set_away_mode": "set_away_mode",
            "async_turn_on": "turn_on",
            "async_turn_off": "turn_off",
        },
        passthrough_attributes=(
            "current_temperature",
            "temperature",
            "target_temp_high",
            "target_temp_low",
            "operation_mode",
            "operation_list",
            "away_mode",
        ),
    ),
    "weather": _adapter(
        "weather",
        read_only=True,
        passthrough_attributes=(
            "temperature",
            "temperature_unit",
            "humidity",
            "pressure",
            "pressure_unit",
            "wind_speed",
            "wind_speed_unit",
            "wind_bearing",
            "condition",
        ),
    ),
}

missing = sorted(set(SUPPORTED_DOMAINS) - set(ADAPTERS))
if missing:
    raise RuntimeError(f"Missing Entity Failover adapters: {missing}")


def adapter_for_domain(domain: str) -> DomainAdapter:
    """Return the adapter for a supported domain."""

    try:
        return ADAPTERS[domain]
    except KeyError as err:
        raise HomeAssistantError(
            f"Unsupported Entity Failover domain: {domain}"
        ) from err
