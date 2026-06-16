"""Route methods for toggle-style domains."""

from __future__ import annotations

from typing import Any


class ToggleRouteMixin:
    """Route common toggle services."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Route turn_on."""

        await self._async_route("turn_on", kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Route turn_off."""

        await self._async_route("turn_off", kwargs)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Route toggle."""

        await self._async_route("toggle", kwargs)
