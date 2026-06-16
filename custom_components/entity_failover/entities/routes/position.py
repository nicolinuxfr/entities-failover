"""Route methods for position-based domains."""

from __future__ import annotations

from typing import Any


class CoverRouteMixin:
    """Route cover services."""

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


class ValveRouteMixin:
    """Route valve services."""

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
