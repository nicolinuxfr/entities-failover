"""Climate domain contract."""

from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.humidifier import (
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)

from ..base import FailoverEntityMixin
from ..routes import ClimateRouteMixin, HumidifierRouteMixin, WaterHeaterRouteMixin
from .common import ToggleFailoverEntity


class FailoverClimateEntity(ClimateRouteMixin, FailoverEntityMixin, ClimateEntity):
    """Main failover entity for climate."""

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""

        return (
            self._active_or_source_attribute("temperature_unit")
            or self.hass.config.units.temperature_unit
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""

        return self._float_attribute("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""

        return self._float_attribute("temperature")

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature."""

        return self._float_attribute("target_temp_high")

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature."""

        return self._float_attribute("target_temp_low")

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return hvac operation ie. heat, cool, mode."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        try:
            return HVACMode(state_val)
        except ValueError:
            return state_val

    @property
    def hvac_modes(self) -> list[HVACMode] | list[str]:
        """Return the list of available hvac operation modes."""

        modes = self._active_or_source_attribute("hvac_modes") or []
        res = []
        for mode in modes:
            try:
                res.append(HVACMode(mode))
            except ValueError:
                res.append(mode)
        return res

    @property
    def hvac_action(self) -> HVACAction | str | None:
        """Return the current running hvac action."""

        val = self._active_attribute("hvac_action")
        if val is None:
            return None
        try:
            return HVACAction(val)
        except ValueError:
            return val

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""

        return self._string_attribute("preset_mode")

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""

        return self._list_attribute("preset_modes")

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""

        return self._string_attribute("fan_mode")

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""

        return self._list_attribute("fan_modes")

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting."""

        return self._string_attribute("swing_mode")

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes."""

        return self._list_attribute("swing_modes")

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the horizontal swing setting."""

        return self._string_attribute("swing_horizontal_mode")

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the list of available horizontal swing modes."""

        return self._list_attribute("swing_horizontal_modes")

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""

        return self._int_attribute("current_humidity")

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""

        return self._int_attribute("target_humidity")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""

        value = self._float_attribute("min_temp")
        return value if value is not None else super().min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""

        value = self._float_attribute("max_temp")
        return value if value is not None else super().max_temp

    @property
    def min_humidity(self) -> int:
        """Return the minimum humidity."""

        value = self._int_attribute("min_humidity")
        return value if value is not None else super().min_humidity

    @property
    def max_humidity(self) -> int:
        """Return the maximum humidity."""

        value = self._int_attribute("max_humidity")
        return value if value is not None else super().max_humidity

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""

        return ClimateEntityFeature(super().supported_features)


class FailoverWaterHeaterEntity(
    WaterHeaterRouteMixin, FailoverEntityMixin, WaterHeaterEntity
):
    """Main failover entity for water heater."""

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""

        return (
            self._active_or_source_attribute("temperature_unit")
            or self.hass.config.units.temperature_unit
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""

        return self._float_attribute("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""

        return self._float_attribute("temperature")

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature."""

        return self._float_attribute("target_temp_high")

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature."""

        return self._float_attribute("target_temp_low")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""

        value = self._float_attribute("min_temp")
        return value if value is not None else super().min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""

        value = self._float_attribute("max_temp")
        return value if value is not None else super().max_temp

    @property
    def current_operation(self) -> str | None:
        """Return current operation ie. heat, cool, idle."""

        return self._string_attribute("operation_mode") or self._native_state_value()

    @property
    def operation_list(self) -> list[str] | None:
        """Return the list of available operation modes."""

        return self._list_attribute("operation_list")

    @property
    def is_away_mode_on(self) -> bool | None:
        """Return true if away mode is on."""

        return self._bool_attribute("away_mode")

    @property
    def supported_features(self) -> WaterHeaterEntityFeature:
        """Return the list of supported features."""

        return WaterHeaterEntityFeature(super().supported_features)


class FailoverHumidifierEntity(
    HumidifierRouteMixin, ToggleFailoverEntity, HumidifierEntity
):
    """Main failover entity for humidifier."""

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""

        return self._int_attribute("target_humidity")

    @property
    def max_humidity(self) -> int:
        """Return the maximum humidity."""

        value = self._int_attribute("max_humidity")
        return value if value is not None else super().max_humidity

    @property
    def min_humidity(self) -> int:
        """Return the minimum humidity."""

        value = self._int_attribute("min_humidity")
        return value if value is not None else super().min_humidity

    @property
    def mode(self) -> str | None:
        """Return the current mode."""

        return self._string_attribute("mode")

    @property
    def available_modes(self) -> list[str] | None:
        """Return a list of available modes."""

        return self._list_attribute("available_modes")

    @property
    def supported_features(self) -> HumidifierEntityFeature:
        """Return the list of supported features."""

        return HumidifierEntityFeature(super().supported_features)
