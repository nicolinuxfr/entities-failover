"""Route methods for specialized service signatures."""

from __future__ import annotations

from typing import Any


class AlarmControlPanelRouteMixin:
    """Route alarm control panel services."""

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


class LawnMowerRouteMixin:
    """Route lawn mower services."""

    async def async_start_mowing(self) -> None:
        """Route lawn mower start_mowing."""

        await self._async_route("start_mowing")

    async def async_pause(self) -> None:
        """Route pause."""

        await self._async_route("pause")

    async def async_dock(self) -> None:
        """Route dock."""

        await self._async_route("dock")


class LockRouteMixin:
    """Route lock services."""

    async def async_lock(self, **kwargs: Any) -> None:
        """Route lock."""

        await self._async_route("lock", kwargs)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Route unlock."""

        await self._async_route("unlock", kwargs)

    async def async_open(self, **kwargs: Any) -> None:
        """Route open."""

        await self._async_route("open", kwargs)


class RemoteRouteMixin:
    """Route remote services."""

    async def async_send_command(self, command: str, **kwargs: Any) -> None:
        """Route send_command."""

        await self._async_route("send_command", {"command": command, **kwargs})

    async def async_learn_command(self, **kwargs: Any) -> None:
        """Route learn_command."""

        await self._async_route("learn_command", kwargs)

    async def async_delete_command(self, **kwargs: Any) -> None:
        """Route delete_command."""

        await self._async_route("delete_command", kwargs)


class UpdateRouteMixin:
    """Route update services."""

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
