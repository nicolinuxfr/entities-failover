"""Diagnostic entities for Entity Failover."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity

from ..const import (
    ATTR_ACTIVE_SOURCE,
    ATTR_FAILOVER_ACTIVE,
    ATTR_NOMINAL_SOURCE,
    ATTR_SOURCE_COUNT,
    ATTR_STATE_SOURCE,
)
from ..helpers import friendly_name
from ..manager import FailoverManager
from .base import FailoverEntityMixin


class FailoverActiveSourceSensor(FailoverEntityMixin, SensorEntity):
    """Diagnostic sensor exposing the selected source name."""

    _attr_icon = "mdi:source-branch"
    _attr_translation_key = "source"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the sensor."""

        super().__init__(manager, suffix="source")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def native_value(self) -> str | None:
        """Return selected source name."""

        return friendly_name(self.manager.hass, self.manager.active_source)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return selected source metadata."""

        sources = list(self.manager.config.sources)

        return {
            ATTR_ACTIVE_SOURCE: self.manager.active_source,
            ATTR_STATE_SOURCE: self.manager.effective_state_source,
            ATTR_NOMINAL_SOURCE: self.manager.nominal_source,
            "active_source_name": friendly_name(
                self.manager.hass,
                self.manager.active_source,
            ),
            "state_source_name": friendly_name(
                self.manager.hass,
                self.manager.effective_state_source,
            ),
            "nominal_source_name": friendly_name(
                self.manager.hass,
                self.manager.nominal_source,
            ),
            "sources": sources,
            "source_names": [
                friendly_name(self.manager.hass, source) for source in sources
            ],
            ATTR_SOURCE_COUNT: len(self.manager.config.sources),
        }


class FailoverActiveBinarySensor(FailoverEntityMixin, BinarySensorEntity):
    """Diagnostic binary sensor exposing active failover."""

    _attr_icon = "mdi:source-branch"
    _attr_translation_key = "failover_active"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the binary sensor."""

        super().__init__(manager, suffix="failover_active")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def is_on(self) -> bool:
        """Return whether failover is active."""

        return self.manager.failover_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source failover detail."""

        return {
            **self.manager.state_attributes,
            ATTR_FAILOVER_ACTIVE: self.is_on,
        }
