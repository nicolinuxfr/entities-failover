"""Route methods for simple value and action domains."""

from __future__ import annotations

from typing import Any


class PressRouteMixin:
    """Route button press services."""

    async def async_press(self) -> None:
        """Route button press."""

        await self._async_route("press")


class SetValueRouteMixin:
    """Route set_value style services."""

    async def async_set_value(self, value: Any) -> None:
        """Route set_value."""

        await self._async_route("set_value", {"value": value})


class SetNativeValueRouteMixin:
    """Route number set_value services."""

    async def async_set_native_value(self, value: Any) -> None:
        """Route number set_value."""

        await self._async_route("set_value", {"value": value})


class SelectOptionRouteMixin:
    """Route select option services."""

    async def async_select_option(self, option: str) -> None:
        """Route select_option."""

        await self._async_route("select_option", {"option": option})


class SceneRouteMixin:
    """Route scene activation."""

    async def async_activate(self, **kwargs: Any) -> None:
        """Route scene activation."""

        await self._async_route("turn_on", kwargs)
