"""Domain entity factory for Entity Failover."""

from __future__ import annotations

from ..manager import FailoverManager
from .base import FailoverEntityMixin
from .domain_contracts import (
    FailoverAirQualityEntity,
    FailoverAlarmControlPanelEntity,
    FailoverBinarySensorEntity,
    FailoverButtonEntity,
    FailoverCalendarEntity,
    FailoverCameraEntity,
    FailoverClimateEntity,
    FailoverCoverEntity,
    FailoverDateEntity,
    FailoverDateTimeEntity,
    FailoverDeviceTrackerEntity,
    FailoverFanEntity,
    FailoverGenericMainEntity,
    FailoverHumidifierEntity,
    FailoverImageEntity,
    FailoverLawnMowerEntity,
    FailoverLightEntity,
    FailoverLockEntity,
    FailoverMediaPlayerEntity,
    FailoverNumberEntity,
    FailoverRemoteEntity,
    FailoverSceneEntity,
    FailoverSelectEntity,
    FailoverSensorEntity,
    FailoverSirenEntity,
    FailoverSwitchEntity,
    FailoverTextEntity,
    FailoverTimeEntity,
    FailoverTodoListEntity,
    FailoverUpdateEntity,
    FailoverVacuumEntity,
    FailoverValveEntity,
    FailoverWaterHeaterEntity,
    FailoverWeatherEntity,
)

DOMAIN_ENTITY_CLASSES: dict[str, type[FailoverEntityMixin]] = {
    "air_quality": FailoverAirQualityEntity,
    "alarm_control_panel": FailoverAlarmControlPanelEntity,
    "binary_sensor": FailoverBinarySensorEntity,
    "button": FailoverButtonEntity,
    "calendar": FailoverCalendarEntity,
    "camera": FailoverCameraEntity,
    "climate": FailoverClimateEntity,
    "cover": FailoverCoverEntity,
    "date": FailoverDateEntity,
    "datetime": FailoverDateTimeEntity,
    "device_tracker": FailoverDeviceTrackerEntity,
    "fan": FailoverFanEntity,
    "humidifier": FailoverHumidifierEntity,
    "image": FailoverImageEntity,
    "lawn_mower": FailoverLawnMowerEntity,
    "light": FailoverLightEntity,
    "lock": FailoverLockEntity,
    "media_player": FailoverMediaPlayerEntity,
    "number": FailoverNumberEntity,
    "remote": FailoverRemoteEntity,
    "scene": FailoverSceneEntity,
    "select": FailoverSelectEntity,
    "sensor": FailoverSensorEntity,
    "siren": FailoverSirenEntity,
    "switch": FailoverSwitchEntity,
    "text": FailoverTextEntity,
    "time": FailoverTimeEntity,
    "todo": FailoverTodoListEntity,
    "update": FailoverUpdateEntity,
    "vacuum": FailoverVacuumEntity,
    "valve": FailoverValveEntity,
    "water_heater": FailoverWaterHeaterEntity,
    "weather": FailoverWeatherEntity,
}


def main_entity_for_manager(manager: FailoverManager) -> FailoverEntityMixin:
    """Build the best main entity class for one manager."""

    entity_cls = DOMAIN_ENTITY_CLASSES.get(
        manager.config.domain,
        FailoverGenericMainEntity,
    )
    return entity_cls(manager)
