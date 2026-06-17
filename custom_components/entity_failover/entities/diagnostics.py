"""Diagnostic entities for Entity Failover."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorEntity

from ..const import (
    ATTR_ACTIVE_SOURCE,
    ATTR_ALL_SOURCES_UNAVAILABLE,
    ATTR_SOURCE_COUNT,
    ATTR_STATE_SOURCE,
)
from ..helpers import friendly_name
from ..manager import FailoverManager
from .base import FailoverEntityMixin


class FailoverActiveSourceSensor(FailoverEntityMixin, SensorEntity):
    """Diagnostic sensor exposing the active source name."""

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
        """Return active source name."""

        return friendly_name(self.manager.hass, self.manager.active_source)

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


class FailoverPrimarySourceInactiveBinarySensor(
    FailoverEntityMixin, BinarySensorEntity
):
    """Diagnostic binary sensor exposing primary source problems."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "primary_source_inactive"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the binary sensor."""

        super().__init__(manager, suffix="primary_source_inactive")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def is_on(self) -> bool:
        """Return whether the primary source is not cleanly active."""

        return self.manager.active_priority_index != 0 or bool(
            self.manager.excluded_sources
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source health detail."""

        return self.manager.state_attributes


class FailoverAllSourcesUnavailableBinarySensor(
    FailoverEntityMixin, BinarySensorEntity
):
    """Diagnostic binary sensor exposing total source unavailability."""

    _attr_icon = "mdi:alert-outline"
    _attr_translation_key = "all_sources_unavailable"

    def __init__(self, manager: FailoverManager) -> None:
        """Initialize the binary sensor."""

        super().__init__(manager, suffix="all_sources_unavailable")

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return True

    @property
    def is_on(self) -> bool:
        """Return whether every source is unavailable or excluded."""

        return self.manager.active_source is None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source availability detail."""

        return {
            **self.manager.state_attributes,
            ATTR_ALL_SOURCES_UNAVAILABLE: self.is_on,
        }
