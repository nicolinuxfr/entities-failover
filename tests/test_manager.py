"""Tests for failover manager behavior."""

from __future__ import annotations

import pytest

from custom_components.entity_failover.manager import FailoverManager
from custom_components.entity_failover.model import (
    CommandValidation,
    FailoverConfig,
    FeaturePolicy,
)


def _config(**overrides):
    data = {
        "entry_id": "entry-1",
        "unique_id": "unique-1",
        "name": "Kitchen Switch",
        "domain": "switch",
        "sources": ("switch.primary", "switch.backup"),
        "command_validation": CommandValidation.SERVICE_CALL,
        "recovery_stability": 30,
        "failure_cooldown": 60,
        "confirmation_timeout": 5,
        "max_attempts": 3,
        "feature_policy": FeaturePolicy.INTERSECTION,
    }
    data.update(overrides)
    return FailoverConfig(**data)


@pytest.mark.asyncio
async def test_selects_first_available_source(hass) -> None:
    """The highest-priority available source is active."""

    hass.states.async_set("switch.primary", "on")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())

    await manager.async_start()

    assert manager.active_source == "switch.primary"
    await manager.async_unload()


@pytest.mark.asyncio
async def test_immediate_failover_when_active_unavailable(hass) -> None:
    """The manager immediately uses backup when active source fails."""

    hass.states.async_set("switch.primary", "on")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    hass.states.async_set("switch.primary", "unavailable")
    await hass.async_block_till_done()

    assert manager.active_source == "switch.backup"
    assert manager.degraded
    await manager.async_unload()


@pytest.mark.asyncio
async def test_command_retries_on_backup(hass) -> None:
    """A failing active source is excluded and the command is retried."""

    calls: list[str] = []

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)
        if entity_id == "switch.primary":
            raise RuntimeError("boom")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    await manager.async_call_service("turn_on")

    assert calls == ["switch.primary", "switch.backup"]
    assert manager.active_source == "switch.backup"
    assert "switch.primary" in manager.excluded_sources
    await manager.async_unload()


@pytest.mark.asyncio
async def test_state_confirmation_success(hass) -> None:
    """State confirmation succeeds when the source publishes expected state."""

    async def _turn_on(call):
        hass.states.async_set(call.data["entity_id"], "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(command_validation=CommandValidation.STATE_CONFIRMATION),
    )
    await manager.async_start()

    await manager.async_call_service("turn_on")

    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    await manager.async_unload()
