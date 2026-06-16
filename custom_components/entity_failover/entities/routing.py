"""Compatibility route mixin for failover main entities."""

from __future__ import annotations

from .routes import (
    AlarmControlPanelRouteMixin,
    ClimateRouteMixin,
    CoverRouteMixin,
    FanRouteMixin,
    HumidifierRouteMixin,
    LawnMowerRouteMixin,
    LockRouteMixin,
    MediaPlayerRouteMixin,
    PressRouteMixin,
    RemoteRouteMixin,
    SceneRouteMixin,
    SelectOptionRouteMixin,
    SetNativeValueRouteMixin,
    SetValueRouteMixin,
    ToggleRouteMixin,
    UpdateRouteMixin,
    VacuumRouteMixin,
    ValveRouteMixin,
    WaterHeaterRouteMixin,
)


class FailoverRouteMixin(
    AlarmControlPanelRouteMixin,
    ClimateRouteMixin,
    CoverRouteMixin,
    FanRouteMixin,
    HumidifierRouteMixin,
    LawnMowerRouteMixin,
    LockRouteMixin,
    MediaPlayerRouteMixin,
    PressRouteMixin,
    RemoteRouteMixin,
    SceneRouteMixin,
    SelectOptionRouteMixin,
    SetNativeValueRouteMixin,
    SetValueRouteMixin,
    ToggleRouteMixin,
    UpdateRouteMixin,
    VacuumRouteMixin,
    ValveRouteMixin,
    WaterHeaterRouteMixin,
):
    """Route Home Assistant entity methods to the active source."""


__all__ = ["FailoverRouteMixin"]
