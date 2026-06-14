"""Diagnostics for Entity Failover."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .helpers import redact_mapping


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    manager = getattr(entry, "runtime_data", None)
    if manager is None:
        return {"entry": redact_mapping(entry.as_dict())}
    return redact_mapping(manager.diagnostics().as_dict())
