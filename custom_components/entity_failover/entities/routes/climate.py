"""Route methods for climate-like domains."""

from __future__ import annotations

from typing import Any


class ClimateRouteMixin:
    """Route climate services."""

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

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Route preset mode."""

        await self._async_route("set_preset_mode", {"preset_mode": preset_mode})


class HumidifierRouteMixin:
    """Route humidifier services."""

    async def async_set_humidity(self, humidity: int) -> None:
        """Route set_humidity."""

        await self._async_route("set_humidity", {"humidity": humidity})

    async def async_set_mode(self, mode: str) -> None:
        """Route humidifier set_mode."""

        await self._async_route("set_mode", {"mode": mode})


class WaterHeaterRouteMixin:
    """Route water heater services."""

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Route set_temperature."""

        await self._async_route("set_temperature", kwargs)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Route water_heater set_operation_mode."""

        await self._async_route(
            "set_operation_mode", {"operation_mode": operation_mode}
        )

    async def async_set_away_mode(self, away_mode: bool) -> None:
        """Route water_heater set_away_mode."""

        await self._async_route("set_away_mode", {"away_mode": away_mode})
