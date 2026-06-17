"""Sensor-based read-only domain contracts."""

from __future__ import annotations

from homeassistant.components.air_quality import AirQualityEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)

from ..base import FailoverEntityMixin


class FailoverSensorEntity(FailoverEntityMixin, SensorEntity):
    """Main failover entity for sensor."""

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""

        return self._native_state_value()

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""

        return self._string_attribute("unit_of_measurement")

    @property
    def device_class(self) -> str | None:
        """Return the device class."""

        return self._string_attribute("device_class")

    @property
    def state_class(self) -> str | None:
        """Return the state class."""

        return self._string_attribute("state_class")

    @property
    def options(self) -> list[str] | None:
        """Return options list."""

        return self._list_attribute("options")


class FailoverBinarySensorEntity(FailoverEntityMixin, BinarySensorEntity):
    """Main failover entity for binary sensor."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""

        return self._native_bool_state()

    @property
    def device_class(self) -> str | None:
        """Return the device class."""

        return self._string_attribute("device_class")


class FailoverDeviceTrackerEntity(FailoverEntityMixin, TrackerEntity):
    """Main failover entity for device tracker."""

    @property
    def source_type(self) -> str:
        """Return the source type, eg gps or router."""

        return self._string_attribute("source_type") or "gps"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of tracker."""

        return self._float_attribute("latitude")

    @property
    def longitude(self) -> float | None:
        """Return longitude value of tracker."""

        return self._float_attribute("longitude")

    @property
    def gps_accuracy(self) -> int | None:
        """Return gps accuracy of tracker."""

        return self._int_attribute("gps_accuracy")

    @property
    def battery_level(self) -> int | None:
        """Return battery level of tracker."""

        return self._int_attribute("battery_level")

    @property
    def location_name(self) -> str | None:
        """Return location name of tracker."""

        return self._string_attribute("location_name")

    @property
    def location_accuracy(self) -> int | None:
        """Return location accuracy of tracker."""

        return self._int_attribute("location_accuracy")


class FailoverWeatherEntity(FailoverEntityMixin, WeatherEntity):
    """Main failover entity for weather."""

    @property
    def condition(self) -> str | None:
        """Return the current condition."""

        return self._native_state_value()

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""

        return self._float_attribute("temperature")

    @property
    def native_temperature_unit(self) -> str:
        """Return the unit of measurement."""

        return (
            self._string_attribute("temperature_unit")
            or self.hass.config.units.temperature_unit
        )

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""

        return self._float_attribute("pressure")

    @property
    def native_pressure_unit(self) -> str | None:
        """Return the pressure unit."""

        return self._string_attribute("pressure_unit")

    @property
    def native_humidity(self) -> float | None:
        """Return the humidity."""

        return self._float_attribute("humidity")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""

        return self._float_attribute("wind_speed")

    @property
    def native_wind_speed_unit(self) -> str | None:
        """Return the wind speed unit."""

        return self._string_attribute("wind_speed_unit")

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""

        return self._active_or_source_attribute("wind_bearing")

    @property
    def native_visibility(self) -> float | None:
        """Return the visibility."""

        return self._float_attribute("visibility")

    @property
    def native_visibility_unit(self) -> str | None:
        """Return the visibility unit."""

        return self._string_attribute("visibility_unit")

    @property
    def native_precipitation(self) -> float | None:
        """Return the precipitation."""

        return self._float_attribute("precipitation")

    @property
    def native_precipitation_unit(self) -> str | None:
        """Return the precipitation unit."""

        return self._string_attribute("precipitation_unit")

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point."""

        return self._float_attribute("dew_point")

    @property
    def native_dew_point_unit(self) -> str | None:
        """Return the dew point unit."""

        return self._string_attribute("dew_point_unit")

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return the wind gust speed."""

        return self._float_attribute("wind_gust_speed")

    @property
    def native_wind_gust_speed_unit(self) -> str | None:
        """Return the wind gust speed unit."""

        return self._string_attribute("wind_gust_speed_unit")

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast."""

        return self._active_or_source_attribute("forecast")

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("weather")
        if component:
            entity = component.get_entity(active_source)
            if entity and hasattr(entity, "async_forecast_daily"):
                return await entity.async_forecast_daily()
        return None

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("weather")
        if component:
            entity = component.get_entity(active_source)
            if entity and hasattr(entity, "async_forecast_hourly"):
                return await entity.async_forecast_hourly()
        return None

    async def async_forecast_twice_daily(self) -> list[Forecast] | None:
        """Return the twice daily forecast."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("weather")
        if component:
            entity = component.get_entity(active_source)
            if entity and hasattr(entity, "async_forecast_twice_daily"):
                return await entity.async_forecast_twice_daily()
        return None

    @property
    def supported_features(self) -> WeatherEntityFeature:
        """Return the list of supported features."""

        return WeatherEntityFeature(super().supported_features)


class FailoverAirQualityEntity(FailoverEntityMixin, AirQualityEntity):
    """Main failover entity for air quality."""

    @property
    def air_quality_index(self) -> int | None:
        """Return the Air Quality Index (AQI)."""

        return self._int_attribute("air_quality_index")

    @property
    def particulate_matter_2_5(self) -> float | None:
        """Return the particulate matter 2.5 value."""

        return self._float_attribute("particulate_matter_2_5")

    @property
    def particulate_matter_10(self) -> float | None:
        """Return the particulate matter 10 value."""

        return self._float_attribute("particulate_matter_10")

    @property
    def particulate_matter_0_1(self) -> float | None:
        """Return the particulate matter 0.1 value."""

        return self._float_attribute("particulate_matter_0_1")

    @property
    def ozone(self) -> float | None:
        """Return the O3 value."""

        return self._float_attribute("ozone")

    @property
    def carbon_monoxide(self) -> float | None:
        """Return the CO value."""

        return self._float_attribute("carbon_monoxide")

    @property
    def carbon_dioxide(self) -> float | None:
        """Return the CO2 value."""

        return self._float_attribute("carbon_dioxide")

    @property
    def sulphur_dioxide(self) -> float | None:
        """Return the SO2 value."""

        return self._float_attribute("sulphur_dioxide")

    @property
    def nitrogen_oxide(self) -> float | None:
        """Return the NOx value."""

        return self._float_attribute("nitrogen_oxide")

    @property
    def nitrogen_monoxide(self) -> float | None:
        """Return the NO value."""

        return self._float_attribute("nitrogen_monoxide")

    @property
    def nitrogen_dioxide(self) -> float | None:
        """Return the NO2 value."""

        return self._float_attribute("nitrogen_dioxide")
