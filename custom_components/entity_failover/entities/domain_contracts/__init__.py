"""Home Assistant domain contract entity classes."""

from __future__ import annotations

from importlib import import_module

_CLASS_MODULES = {
    "FailoverAirQualityEntity": "sensor",
    "FailoverAlarmControlPanelEntity": "security",
    "FailoverBinarySensorEntity": "sensor",
    "FailoverButtonEntity": "simple",
    "FailoverCalendarEntity": "specialized",
    "FailoverCameraEntity": "camera",
    "FailoverClimateEntity": "climate",
    "FailoverCoverEntity": "position",
    "FailoverDateEntity": "value",
    "FailoverDateTimeEntity": "value",
    "FailoverDeviceTrackerEntity": "sensor",
    "FailoverFanEntity": "simple",
    "FailoverGenericMainEntity": "common",
    "FailoverHumidifierEntity": "climate",
    "FailoverImageEntity": "specialized",
    "FailoverLawnMowerEntity": "specialized",
    "FailoverLightEntity": "light",
    "FailoverLockEntity": "security",
    "FailoverMediaPlayerEntity": "media",
    "FailoverNumberEntity": "value",
    "FailoverRemoteEntity": "simple",
    "FailoverSceneEntity": "specialized",
    "FailoverSelectEntity": "value",
    "FailoverSensorEntity": "sensor",
    "FailoverSirenEntity": "simple",
    "FailoverSwitchEntity": "simple",
    "FailoverTextEntity": "value",
    "FailoverTimeEntity": "value",
    "FailoverTodoListEntity": "specialized",
    "FailoverUpdateEntity": "specialized",
    "FailoverVacuumEntity": "specialized",
    "FailoverValveEntity": "position",
    "FailoverWaterHeaterEntity": "climate",
    "FailoverWeatherEntity": "sensor",
    "ToggleFailoverEntity": "common",
}

__all__ = [
    "FailoverAirQualityEntity",
    "FailoverAlarmControlPanelEntity",
    "FailoverBinarySensorEntity",
    "FailoverButtonEntity",
    "FailoverCalendarEntity",
    "FailoverCameraEntity",
    "FailoverClimateEntity",
    "FailoverCoverEntity",
    "FailoverDateEntity",
    "FailoverDateTimeEntity",
    "FailoverDeviceTrackerEntity",
    "FailoverFanEntity",
    "FailoverGenericMainEntity",
    "FailoverHumidifierEntity",
    "FailoverImageEntity",
    "FailoverLawnMowerEntity",
    "FailoverLightEntity",
    "FailoverLockEntity",
    "FailoverMediaPlayerEntity",
    "FailoverNumberEntity",
    "FailoverRemoteEntity",
    "FailoverSceneEntity",
    "FailoverSelectEntity",
    "FailoverSensorEntity",
    "FailoverSirenEntity",
    "FailoverSwitchEntity",
    "FailoverTextEntity",
    "FailoverTimeEntity",
    "FailoverTodoListEntity",
    "FailoverUpdateEntity",
    "FailoverVacuumEntity",
    "FailoverValveEntity",
    "FailoverWaterHeaterEntity",
    "FailoverWeatherEntity",
    "ToggleFailoverEntity",
]


def __getattr__(name: str) -> object:
    """Resolve domain contract classes without importing every HA platform."""

    if name not in _CLASS_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f".{_CLASS_MODULES[name]}", package=__name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
