"""Simple Home Assistant domain contracts."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.remote import RemoteEntity
from homeassistant.components.siren import SirenEntity, SirenEntityFeature
from homeassistant.components.switch import SwitchEntity

from ..base import FailoverEntityMixin
from ..routes import FanRouteMixin, PressRouteMixin, RemoteRouteMixin
from .common import ToggleFailoverEntity


class FailoverButtonEntity(PressRouteMixin, FailoverEntityMixin, ButtonEntity):
    """Main failover entity for buttons."""


class FailoverFanEntity(FanRouteMixin, ToggleFailoverEntity, FanEntity):
    """Main failover entity for fans."""

    @property
    def percentage(self) -> int | None:
        """Return active source fan percentage."""

        value = self._float_attribute("percentage")
        return int(value) if value is not None else None

    @property
    def percentage_step(self) -> float | None:
        """Return active source fan percentage step."""

        return self._float_attribute("percentage_step")

    @property
    def preset_mode(self) -> str | None:
        """Return active source preset mode."""

        return self._active_attribute("preset_mode")

    @property
    def preset_modes(self) -> list[str] | None:
        """Return active source preset modes."""

        return self._active_or_source_attribute("preset_modes")

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return active source supported fan features."""

        return FanEntityFeature(super().supported_features)


class FailoverRemoteEntity(RemoteRouteMixin, ToggleFailoverEntity, RemoteEntity):
    """Main failover entity for remotes."""


class FailoverSirenEntity(ToggleFailoverEntity, SirenEntity):
    """Main failover entity for sirens."""

    @property
    def supported_features(self) -> SirenEntityFeature:
        """Return active source supported siren features."""

        return SirenEntityFeature(super().supported_features)


class FailoverSwitchEntity(ToggleFailoverEntity, SwitchEntity):
    """Main failover entity for switches."""
