"""Entity Failover integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DIAGNOSTIC_PLATFORMS, DOMAIN, SERVICE_CLEAR_FAILURES
from .manager import FailoverManager
from .model import FailoverConfig

type EntityFailoverConfigEntry = ConfigEntry[FailoverManager]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration services."""

    async def _async_clear_failures(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        entity_id = call.data.get(ATTR_ENTITY_ID)
        managers = hass.data.get(DOMAIN, {})
        matched = [
            manager
            for manager in managers.values()
            if (entry_id is None or manager.config.entry_id == entry_id)
            and (entity_id is None or manager.main_entity_id == entity_id)
        ]
        if not matched:
            raise HomeAssistantError("No matching Entity Failover entry found")
        for manager in matched:
            await manager.async_clear_failures()

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_FAILURES,
        _async_clear_failures,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): str,
                vol.Optional(ATTR_ENTITY_ID): str,
            }
        ),
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
) -> bool:
    """Set up an Entity Failover config entry."""

    hass.data.setdefault(DOMAIN, {})
    config = FailoverConfig.from_entry(entry)
    manager = FailoverManager(hass, config)
    entry.runtime_data = manager
    hass.data[DOMAIN][entry.entry_id] = manager
    await manager.async_start()
    await hass.config_entries.async_forward_entry_setups(
        entry,
        _entry_platforms(config.domain),
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
) -> bool:
    """Unload an Entity Failover config entry."""

    manager = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        _entry_platforms(manager.config.domain),
    )
    if unload_ok:
        await manager.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
) -> None:
    """Reload a config entry after options change."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: EntityFailoverConfigEntry,
) -> bool:
    """Migrate old config entries."""

    if entry.version == 1:
        return True
    return False


def _entry_platforms(domain: str) -> list[str]:
    """Return platforms needed by one config entry."""

    return sorted({domain, *DIAGNOSTIC_PLATFORMS})
