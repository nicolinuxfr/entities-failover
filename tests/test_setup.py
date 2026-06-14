"""Tests for integration setup and unload."""

from __future__ import annotations

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_failover.const import (
    CONF_AVAILABILITY_STRATEGY,
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_MAX_ATTEMPTS,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DOMAIN,
    NAME,
    SUBENTRY_TYPE_FAILOVER,
)


@pytest.mark.asyncio
async def test_setup_and_unload_entry(hass) -> None:
    """A config entry can be set up and unloaded."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Kitchen Switch",
                    CONF_DOMAIN: "switch",
                    CONF_SOURCES: ["switch.one", "switch.two"],
                    CONF_AVAILABILITY_STRATEGY: "simple",
                    CONF_COMMAND_VALIDATION: "service_call",
                    CONF_CONFIRMATION_TIMEOUT: 10,
                    CONF_FAILURE_COOLDOWN: 60,
                    CONF_RECOVERY_STABILITY: 30,
                    CONF_MAX_ATTEMPTS: 3,
                    CONF_FEATURE_POLICY: "intersection",
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Kitchen Switch",
                "unique_id": "unique-setup",
            }
        ],
        version=2,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "unique-setup" in hass.data[DOMAIN]
    registry_entry = er.async_get(hass).async_get("switch.kitchen_switch")
    assert registry_entry is not None
    assert registry_entry.config_subentry_id == subentry.subentry_id

    assert await hass.config_entries.async_unload(entry.entry_id)
