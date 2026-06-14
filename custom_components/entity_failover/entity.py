"""Entity classes shared by Entity Failover platforms."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import (
    ATTR_ACTIVE_SOURCE,
    ATTR_FORWARDED_ENTITY_ID,
    ATTR_SOURCE_COUNT,
    DOMAIN,
    NAME,
)
from .helpers import friendly_name
from .manager import FailoverManager


class FailoverEntityMixin(Entity):
    """Base behavior for all failover entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, manager: FailoverManager, *, suffix: str | None = None) -> None:
        """Initialize a failover entity."""

        self.manager = manager
        self._suffix = suffix
        self._attr_unique_id = (
            f"{manager.config.unique_id}_{suffix}"
            if suffix
            else manager.config.unique_id
        )
        self._attr_name = suffix.replace("_", " ").title() if suffix else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.config.unique_id)},
            name=manager.config.name,
            manufacturer=NAME,
            entry_type="service",
        )

    async def async_added_to_hass(self) -> None:
        """Register update listener."""

        if self._suffix is None:
            self.manager.main_entity_id = self.entity_id
        self.async_on_remove(
            self.manager.async_add_update_listener(self._handle_manager_update)
        )

    @callback
    def _handle_manager_update(self) -> None:
        """Write HA state after manager changes."""

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return self.manager.available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return safe diagnostic and standard passthrough attributes."""

        attrs = dict(self.manager.state_attributes)
        active_state = self.manager.active_state
        if active_state is None:
            return attrs
        attrs[ATTR_FORWARDED_ENTITY_ID] = active_state.entity_id
        for key in self.manager.adapter.passthrough_attributes:
            if key in active_state.attributes:
                attrs[key] = active_state.attributes[key]
        return attrs

    @property
    def supported_features(self) -> int:
        """Return supported features according to the selected policy."""

        if self.manager.config.feature_policy == "active_source":
            return self.manager.adapter.supported_features(self.manager.active_state)
        states = [
            self.manager.hass.states.get(source)
            for source in self.manager.config.sources
        ]
        if not states:
            return 0
        result = self.manager.adapter.supported_features(states[0])
        for state in states[1:]:
            result &= self.manager.adapter.supported_features(state)
        return result

    @property
    def state(self) -> str | None:
        """Mirror the active source state."""

        active_state = self.manager.active_state
        return active_state.state if active_state is not None else None

    async def _async_route(
        self,
        service: str,
        data: Mapping[str, Any] | None = None,
        *,
        context: Context | None = None,
        required_features: int = 0,
    ) -> None:
        """Route a service call through the manager."""

        payload = dict(data or {})
        payload.pop(ATTR_ENTITY_ID, None)
        await self.manager.async_call_service(
            service,
            payload,
            context=context,
            required_features=required_features,
        )


class FailoverMainEntity(FailoverEntityMixin):
    """Generic main failover entity."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Route turn_on."""

        await self._async_route("turn_on", kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Route turn_off."""

        await self._async_route("turn_off", kwargs)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Route toggle."""

        await self._async_route("toggle", kwargs)

    async def async_press(self) -> None:
        """Route button press."""

        await self._async_route("press")

    async def async_lock(self, **kwargs: Any) -> None:
        """Route lock."""

        await self._async_route("lock", kwargs)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Route unlock."""

        await self._async_route("unlock", kwargs)

    async def async_open(self, **kwargs: Any) -> None:
        """Route open."""

        await self._async_route("open", kwargs)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Route open_cover."""

        await self._async_route("open_cover", kwargs)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Route close_cover."""

        await self._async_route("close_cover", kwargs)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Route stop_cover."""

        await self._async_route("stop_cover", kwargs)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Route set_cover_position."""

        await self._async_route("set_cover_position", kwargs)

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Route open_cover_tilt."""

        await self._async_route("open_cover_tilt", kwargs)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Route close_cover_tilt."""

        await self._async_route("close_cover_tilt", kwargs)

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Route stop_cover_tilt."""

        await self._async_route("stop_cover_tilt", kwargs)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Route set_cover_tilt_position."""

        await self._async_route("set_cover_tilt_position", kwargs)

    async def async_set_percentage(self, percentage: int) -> None:
        """Route fan set_percentage."""

        await self._async_route("set_percentage", {"percentage": percentage})

    async def async_increase_speed(self, **kwargs: Any) -> None:
        """Route fan increase_speed."""

        await self._async_route("increase_speed", kwargs)

    async def async_decrease_speed(self, **kwargs: Any) -> None:
        """Route fan decrease_speed."""

        await self._async_route("decrease_speed", kwargs)

    async def async_oscillate(self, oscillating: bool) -> None:
        """Route fan oscillate."""

        await self._async_route("oscillate", {"oscillating": oscillating})

    async def async_set_direction(self, direction: str) -> None:
        """Route fan set_direction."""

        await self._async_route("set_direction", {"direction": direction})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Route preset mode."""

        await self._async_route("set_preset_mode", {"preset_mode": preset_mode})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Route set_temperature."""

        await self._async_route("set_temperature", kwargs)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Route climate set_hvac_mode."""

        await self._async_route("set_hvac_mode", {"hvac_mode": hvac_mode})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Route climate set_fan_mode."""

        await self._async_route("set_fan_mode", {"fan_mode": fan_mode})

    async def async_set_humidity(self, humidity: int) -> None:
        """Route set_humidity."""

        await self._async_route("set_humidity", {"humidity": humidity})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Route climate set_swing_mode."""

        await self._async_route("set_swing_mode", {"swing_mode": swing_mode})

    async def async_set_mode(self, mode: str) -> None:
        """Route humidifier set_mode."""

        await self._async_route("set_mode", {"mode": mode})

    async def async_set_native_value(self, value: Any) -> None:
        """Route number/text/date/time set_value."""

        await self._async_route("set_value", {"value": value})

    async def async_set_value(self, value: Any) -> None:
        """Route set_value."""

        await self._async_route("set_value", {"value": value})

    async def async_select_option(self, option: str) -> None:
        """Route select_option."""

        await self._async_route("select_option", {"option": option})

    async def async_activate(self, **kwargs: Any) -> None:
        """Route scene activation."""

        await self._async_route("turn_on", kwargs)

    async def async_media_play(self) -> None:
        """Route media_play."""

        await self._async_route("media_play")

    async def async_media_pause(self) -> None:
        """Route media_pause."""

        await self._async_route("media_pause")

    async def async_media_stop(self) -> None:
        """Route media_stop."""

        await self._async_route("media_stop")

    async def async_media_next_track(self) -> None:
        """Route media_next_track."""

        await self._async_route("media_next_track")

    async def async_media_previous_track(self) -> None:
        """Route media_previous_track."""

        await self._async_route("media_previous_track")

    async def async_set_volume_level(self, volume: float) -> None:
        """Route volume_set."""

        await self._async_route("volume_set", {"volume_level": volume})

    async def async_mute_volume(self, mute: bool) -> None:
        """Route volume_mute."""

        await self._async_route("volume_mute", {"is_volume_muted": mute})

    async def async_select_source(self, source: str) -> None:
        """Route media player source selection."""

        await self._async_route("select_source", {"source": source})

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Route media player sound mode selection."""

        await self._async_route("select_sound_mode", {"sound_mode": sound_mode})

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Route play_media."""

        data = {
            "media_content_type": media_type,
            "media_content_id": media_id,
            **kwargs,
        }
        await self._async_route("play_media", data)

    async def async_clear_playlist(self) -> None:
        """Route clear_playlist."""

        await self._async_route("clear_playlist")

    async def async_shuffle_set(self, shuffle: bool) -> None:
        """Route shuffle_set."""

        await self._async_route("shuffle_set", {"shuffle": shuffle})

    async def async_repeat_set(self, repeat: str) -> None:
        """Route repeat_set."""

        await self._async_route("repeat_set", {"repeat": repeat})

    async def async_start(self) -> None:
        """Route vacuum start."""

        await self._async_route("start")

    async def async_pause(self) -> None:
        """Route pause."""

        await self._async_route("pause")

    async def async_stop(self, **kwargs: Any) -> None:
        """Route stop."""

        await self._async_route("stop", kwargs)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Route return_to_base."""

        await self._async_route("return_to_base", kwargs)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Route clean_spot."""

        await self._async_route("clean_spot", kwargs)

    async def async_locate(self, **kwargs: Any) -> None:
        """Route locate."""

        await self._async_route("locate", kwargs)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Route vacuum fan speed."""

        await self._async_route("set_fan_speed", {"fan_speed": fan_speed, **kwargs})

    async def async_send_command(self, command: str, **kwargs: Any) -> None:
        """Route send_command."""

        await self._async_route("send_command", {"command": command, **kwargs})

    async def async_learn_command(self, **kwargs: Any) -> None:
        """Route learn_command."""

        await self._async_route("learn_command", kwargs)

    async def async_delete_command(self, **kwargs: Any) -> None:
        """Route delete_command."""

        await self._async_route("delete_command", kwargs)

    async def async_start_mowing(self) -> None:
        """Route lawn mower start_mowing."""

        await self._async_route("start_mowing")

    async def async_dock(self) -> None:
        """Route dock."""

        await self._async_route("dock")

    async def async_install(
        self, version: str | None = None, backup: bool | None = None
    ) -> None:
        """Route update install."""

        data = {}
        if version is not None:
            data["version"] = version
        if backup is not None:
            data["backup"] = backup
        await self._async_route("install", data)

    async def async_skip(self) -> None:
        """Route update skip."""

        await self._async_route("skip")

    async def async_clear_skipped(self) -> None:
        """Route update clear_skipped."""

        await self._async_route("clear_skipped")

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Route open_valve."""

        await self._async_route("open_valve", kwargs)

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Route close_valve."""

        await self._async_route("close_valve", kwargs)

    async def async_set_valve_position(self, **kwargs: Any) -> None:
        """Route set_valve_position."""

        await self._async_route("set_valve_position", kwargs)

    async def async_stop_valve(self, **kwargs: Any) -> None:
        """Route stop_valve."""

        await self._async_route("stop_valve", kwargs)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Route water_heater set_operation_mode."""

        await self._async_route(
            "set_operation_mode", {"operation_mode": operation_mode}
        )

    async def async_set_away_mode(self, away_mode: bool) -> None:
        """Route water_heater set_away_mode."""

        await self._async_route("set_away_mode", {"away_mode": away_mode})

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Route alarm disarm."""

        await self._async_route("alarm_disarm", {"code": code} if code else {})

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Route alarm_arm_home."""

        await self._async_route("alarm_arm_home", {"code": code} if code else {})

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Route alarm_arm_away."""

        await self._async_route("alarm_arm_away", {"code": code} if code else {})

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Route alarm_arm_night."""

        await self._async_route("alarm_arm_night", {"code": code} if code else {})

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        """Route alarm_arm_vacation."""

        await self._async_route("alarm_arm_vacation", {"code": code} if code else {})

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Route alarm_arm_custom_bypass."""

        await self._async_route(
            "alarm_arm_custom_bypass", {"code": code} if code else {}
        )

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Route alarm_trigger."""

        await self._async_route("alarm_trigger", {"code": code} if code else {})


class FailoverActiveSourceSensor(FailoverEntityMixin):
    """Diagnostic sensor exposing the active source entity id."""

    _attr_icon = "mdi:source-branch"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the sensor."""

        super().__init__(manager, suffix="active_source")

    @property
    def native_value(self) -> str | None:
        """Return active source id."""

        return self.manager.active_source

    @property
    def state(self) -> str | None:
        """Return active source id for generic entity platforms."""

        return self.native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return active source metadata."""

        return {
            ATTR_ACTIVE_SOURCE: self.manager.active_source,
            "active_source_name": friendly_name(
                self.manager.hass,
                self.manager.active_source,
            ),
            ATTR_SOURCE_COUNT: len(self.manager.config.sources),
        }


class FailoverDegradedBinarySensor(FailoverEntityMixin):
    """Diagnostic binary sensor exposing degraded status."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the binary sensor."""

        super().__init__(manager, suffix="degraded")

    @property
    def is_on(self) -> bool:
        """Return whether the entity is degraded."""

        return self.manager.degraded

    @property
    def state(self) -> str:
        """Return binary state for generic entity platforms."""

        return "on" if self.is_on else "off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return degradation detail."""

        return self.manager.state_attributes


class FailoverClearFailuresButton(FailoverEntityMixin):
    """Button that clears temporary source failures."""

    _attr_icon = "mdi:refresh-alert"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the button."""

        super().__init__(manager, suffix="clear_failures")

    async def async_press(self) -> None:
        """Clear temporary source exclusions."""

        await self.manager.async_clear_failures()
