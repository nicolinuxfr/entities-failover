"""Tests for integration setup and unload."""

from __future__ import annotations

import pytest
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
)


@pytest.mark.asyncio
async def test_setup_and_unload_entry(hass) -> None:
    """A config entry can be set up and unloaded."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen Switch",
        unique_id="unique-setup",
        data={
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
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
