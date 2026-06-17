"""Domain entity factory for Entity Failover."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from importlib import import_module

from ..const import SUPPORTED_DOMAINS
from ..manager import FailoverManager
from .base import FailoverEntityMixin
from .domain_contracts.common import FailoverGenericMainEntity
from .domain_contracts.light import FailoverLightEntity
from .domain_contracts.value import FailoverNumberEntity

_DOMAIN_ENTITY_CLASS_PATHS: dict[str, tuple[str, str]] = {
    "air_quality": ("sensor", "FailoverAirQualityEntity"),
    "alarm_control_panel": ("security", "FailoverAlarmControlPanelEntity"),
    "binary_sensor": ("sensor", "FailoverBinarySensorEntity"),
    "button": ("simple", "FailoverButtonEntity"),
    "calendar": ("specialized", "FailoverCalendarEntity"),
    "camera": ("camera", "FailoverCameraEntity"),
    "climate": ("climate", "FailoverClimateEntity"),
    "cover": ("position", "FailoverCoverEntity"),
    "date": ("value", "FailoverDateEntity"),
    "datetime": ("value", "FailoverDateTimeEntity"),
    "device_tracker": ("sensor", "FailoverDeviceTrackerEntity"),
    "fan": ("simple", "FailoverFanEntity"),
    "humidifier": ("climate", "FailoverHumidifierEntity"),
    "image": ("specialized", "FailoverImageEntity"),
    "lawn_mower": ("specialized", "FailoverLawnMowerEntity"),
    "light": ("light", "FailoverLightEntity"),
    "lock": ("security", "FailoverLockEntity"),
    "media_player": ("media", "FailoverMediaPlayerEntity"),
    "number": ("value", "FailoverNumberEntity"),
    "remote": ("simple", "FailoverRemoteEntity"),
    "scene": ("specialized", "FailoverSceneEntity"),
    "select": ("value", "FailoverSelectEntity"),
    "sensor": ("sensor", "FailoverSensorEntity"),
    "siren": ("simple", "FailoverSirenEntity"),
    "switch": ("simple", "FailoverSwitchEntity"),
    "text": ("value", "FailoverTextEntity"),
    "time": ("value", "FailoverTimeEntity"),
    "todo": ("specialized", "FailoverTodoListEntity"),
    "update": ("specialized", "FailoverUpdateEntity"),
    "vacuum": ("specialized", "FailoverVacuumEntity"),
    "valve": ("position", "FailoverValveEntity"),
    "water_heater": ("climate", "FailoverWaterHeaterEntity"),
    "weather": ("sensor", "FailoverWeatherEntity"),
}


class _DomainEntityClassMap(Mapping[str, type[FailoverEntityMixin]]):
    """Resolve domain entity classes only when a platform needs them."""

    def __init__(self) -> None:
        """Initialize the lazy class cache."""

        self._cache: dict[str, type[FailoverEntityMixin]] = {
            "light": FailoverLightEntity,
            "number": FailoverNumberEntity,
        }

    def __getitem__(self, domain: str) -> type[FailoverEntityMixin]:
        """Return the entity class for a supported domain."""

        if domain in self._cache:
            return self._cache[domain]
        module_name, class_name = _DOMAIN_ENTITY_CLASS_PATHS[domain]
        module = import_module(f".domain_contracts.{module_name}", package=__package__)
        entity_cls = getattr(module, class_name)
        self._cache[domain] = entity_cls
        return entity_cls

    def __iter__(self) -> Iterator[str]:
        """Return supported domains."""

        return iter(SUPPORTED_DOMAINS)

    def __len__(self) -> int:
        """Return the supported domain count."""

        return len(SUPPORTED_DOMAINS)


DOMAIN_ENTITY_CLASSES: Mapping[str, type[FailoverEntityMixin]] = _DomainEntityClassMap()


def main_entity_for_manager(manager: FailoverManager) -> FailoverEntityMixin:
    """Build the best main entity class for one manager."""

    entity_cls = DOMAIN_ENTITY_CLASSES.get(
        manager.config.domain,
        FailoverGenericMainEntity,
    )
    return entity_cls(manager)
