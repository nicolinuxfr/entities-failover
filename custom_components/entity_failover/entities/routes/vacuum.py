"""Route methods for vacuum services."""

from __future__ import annotations

from typing import Any


class VacuumRouteMixin:
    """Route vacuum services."""

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
