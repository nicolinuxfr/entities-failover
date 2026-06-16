"""Composable route mixins for failover entities."""

from .climate import ClimateRouteMixin, HumidifierRouteMixin, WaterHeaterRouteMixin
from .fan import FanRouteMixin
from .media import MediaPlayerRouteMixin
from .position import CoverRouteMixin, ValveRouteMixin
from .simple import (
    PressRouteMixin,
    SceneRouteMixin,
    SelectOptionRouteMixin,
    SetNativeValueRouteMixin,
    SetValueRouteMixin,
)
from .specialized import (
    AlarmControlPanelRouteMixin,
    LawnMowerRouteMixin,
    LockRouteMixin,
    RemoteRouteMixin,
    UpdateRouteMixin,
)
from .toggle import ToggleRouteMixin
from .vacuum import VacuumRouteMixin

__all__ = [
    "AlarmControlPanelRouteMixin",
    "ClimateRouteMixin",
    "CoverRouteMixin",
    "FanRouteMixin",
    "HumidifierRouteMixin",
    "LawnMowerRouteMixin",
    "LockRouteMixin",
    "MediaPlayerRouteMixin",
    "PressRouteMixin",
    "RemoteRouteMixin",
    "SceneRouteMixin",
    "SelectOptionRouteMixin",
    "SetNativeValueRouteMixin",
    "SetValueRouteMixin",
    "ToggleRouteMixin",
    "UpdateRouteMixin",
    "VacuumRouteMixin",
    "ValveRouteMixin",
    "WaterHeaterRouteMixin",
]
