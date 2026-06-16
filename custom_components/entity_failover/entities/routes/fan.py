"""Route methods for fan-like services."""

from __future__ import annotations

from typing import Any


class FanRouteMixin:
    """Route fan services."""

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
