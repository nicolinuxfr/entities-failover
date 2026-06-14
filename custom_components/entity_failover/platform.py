"""Shared platform setup helpers."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EntityFailoverConfigEntry
from .entity import (
    FailoverActiveSourceSensor,
    FailoverClearFailuresButton,
    FailoverDegradedBinarySensor,
    FailoverMainEntity,
)


async def async_setup_platform_entry(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform_domain: str,
) -> None:
    """Set up one failover platform."""

    manager = entry.runtime_data
    entities = []
    if manager.config.domain == platform_domain:
        entities.append(FailoverMainEntity(manager))
    if platform_domain == "sensor":
        entities.append(FailoverActiveSourceSensor(manager))
    elif platform_domain == "binary_sensor":
        entities.append(FailoverDegradedBinarySensor(manager))
    elif platform_domain == "button":
        entities.append(FailoverClearFailuresButton(manager))
    if entities:
        async_add_entities(entities)


def make_async_setup_entry(
    platform_domain: str,
) -> Callable[
    [HomeAssistant, EntityFailoverConfigEntry, AddEntitiesCallback],
    Coroutine[Any, Any, None],
]:
    """Create the Home Assistant platform setup entry function."""

    async def _async_setup_entry(
        hass: HomeAssistant,
        entry: EntityFailoverConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        await async_setup_platform_entry(
            hass,
            entry,
            async_add_entities,
            platform_domain,
        )

    return _async_setup_entry
