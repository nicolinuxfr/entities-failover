"""Shared platform setup helpers."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EntityFailoverConfigEntry
from .entities import (
    FailoverActiveSourceSensor,
    FailoverClearFailuresButton,
    FailoverDegradedBinarySensor,
    main_entity_for_manager,
)


async def async_setup_platform_entry(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    platform_domain: str,
) -> None:
    """Set up one failover platform."""

    for manager in entry.runtime_data.values():
        entities = []
        if manager.config.domain == platform_domain:
            entities.append(main_entity_for_manager(manager))
        if platform_domain == "sensor":
            entities.append(FailoverActiveSourceSensor(manager))
        elif platform_domain == "binary_sensor":
            entities.append(FailoverDegradedBinarySensor(manager))
        elif platform_domain == "button":
            entities.append(FailoverClearFailuresButton(manager))
        if entities:
            async_add_entities(
                entities,
                config_subentry_id=manager.config.subentry_id,
            )


def make_async_setup_entry(
    platform_domain: str,
) -> Callable[
    [HomeAssistant, EntityFailoverConfigEntry, AddConfigEntryEntitiesCallback],
    Coroutine[Any, Any, None],
]:
    """Create the Home Assistant platform setup entry function."""

    async def _async_setup_entry(
        hass: HomeAssistant,
        entry: EntityFailoverConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        await async_setup_platform_entry(
            hass,
            entry,
            async_add_entities,
            platform_domain,
        )

    return _async_setup_entry
