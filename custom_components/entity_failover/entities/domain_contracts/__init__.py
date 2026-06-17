"""Home Assistant domain contract entity classes."""

from .climate import (
    FailoverClimateEntity,
    FailoverHumidifierEntity,
    FailoverWaterHeaterEntity,
)
from .common import FailoverGenericMainEntity, ToggleFailoverEntity
from .light import FailoverLightEntity
from .media import FailoverMediaPlayerEntity
from .position import FailoverCoverEntity, FailoverValveEntity
from .security import FailoverAlarmControlPanelEntity, FailoverLockEntity
from .sensor import (
    FailoverAirQualityEntity,
    FailoverBinarySensorEntity,
    FailoverDeviceTrackerEntity,
    FailoverSensorEntity,
    FailoverWeatherEntity,
)
from .simple import (
    FailoverButtonEntity,
    FailoverFanEntity,
    FailoverRemoteEntity,
    FailoverSirenEntity,
    FailoverSwitchEntity,
)
from .specialized import (
    FailoverCalendarEntity,
    FailoverCameraEntity,
    FailoverImageEntity,
    FailoverLawnMowerEntity,
    FailoverSceneEntity,
    FailoverTodoListEntity,
    FailoverUpdateEntity,
    FailoverVacuumEntity,
)
from .value import (
    FailoverDateEntity,
    FailoverDateTimeEntity,
    FailoverNumberEntity,
    FailoverSelectEntity,
    FailoverTextEntity,
    FailoverTimeEntity,
)

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
