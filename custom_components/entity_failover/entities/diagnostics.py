"""Diagnostic entities for Entity Failover."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity

from ..const import ATTR_ACTIVE_SOURCE, ATTR_SOURCE_COUNT, ATTR_STATE_SOURCE
from ..helpers import friendly_name
from ..manager import FailoverManager
from .base import FailoverEntityMixin


class FailoverActiveSourceSensor(FailoverEntityMixin, SensorEntity):
    """Diagnostic sensor exposing the active source entity id."""

    _attr_icon = "mdi:source-branch"
    _attr_translation_key = "active_source"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the sensor."""

        super().__init__(manager, suffix="active_source")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def native_value(self) -> str | None:
        """Return active source id."""

        return self.manager.active_source

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return active source metadata."""

        return {
            ATTR_ACTIVE_SOURCE: self.manager.active_source,
            ATTR_STATE_SOURCE: self.manager.effective_state_source,
            "active_source_name": friendly_name(
                self.manager.hass,
                self.manager.active_source,
            ),
            "state_source_name": friendly_name(
                self.manager.hass,
                self.manager.effective_state_source,
            ),
            ATTR_SOURCE_COUNT: len(self.manager.config.sources),
        }


class FailoverDegradedBinarySensor(FailoverEntityMixin, BinarySensorEntity):
    """Diagnostic binary sensor exposing degraded status."""

    _attr_icon = "mdi:alert-circle-outline"
    _attr_translation_key = "fallback_active"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the binary sensor."""

        super().__init__(manager, suffix="degraded")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def is_on(self) -> bool:
        """Return whether the entity is degraded."""

        return self.manager.degraded

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return degradation detail."""

        return self.manager.state_attributes
