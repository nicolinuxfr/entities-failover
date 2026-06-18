"""Tests for failover manager behavior."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.entity_failover.manager import FailoverManager
from custom_components.entity_failover.model import (
    CommandValidation,
    FailoverConfig,
    FeaturePolicy,
    SelectionPolicy,
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
        "feature_policy": FeaturePolicy.INTERSECTION,
    }
    data.update(overrides)
    return FailoverConfig(**data)


async def _finish_confirmation(hass, task: asyncio.Task[None], seconds: float) -> None:
    """Advance Home Assistant time until a pending confirmation can finish."""

    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds + 1))
    await hass.async_block_till_done()
    await task


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
        hass.states.async_set(entity_id, "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(command_validation=CommandValidation.STATE_CONFIRMATION),
    )
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary", "switch.backup"]
    assert manager.active_source == "switch.backup"
    assert "switch.primary" in manager.excluded_sources
    await manager.async_unload()


@pytest.mark.asyncio
async def test_command_logs_routed_source(hass, caplog) -> None:
    """Successful commands log the source that received the service call."""

    caplog.set_level(
        logging.DEBUG,
        logger="custom_components.entity_failover.manager",
    )

    async def _turn_on(call):
        hass.states.async_set(call.data["entity_id"], "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert (
        "Entity Failover Kitchen Switch routing switch.turn_on "
        "to switch.primary (attempt 1)"
    ) in caplog.text
    assert (
        "Entity Failover Kitchen Switch completed switch.turn_on "
        "on switch.primary (attempt 1)"
    ) in caplog.text
    await manager.async_unload()


@pytest.mark.asyncio
async def test_successful_command_can_mirror_confirming_state_source(hass) -> None:
    """Commands keep priority while state can mirror a confirming source."""

    calls: list[str] = []

    async def _turn_on(call):
        calls.append(call.data["entity_id"])
        hass.states.async_set("switch.backup", "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert manager.state_source == "switch.backup"
    assert manager.sources_desynchronized
    assert manager.active_state == hass.states.get("switch.backup")
    assert manager.state_attributes["active_source"] == "switch.primary"
    assert manager.state_attributes["state_source"] == "switch.backup"
    assert manager.state_attributes["sources_desynchronized"] is True

    hass.states.async_set("switch.primary", "on")
    await hass.async_block_till_done()

    assert manager.active_source == "switch.primary"
    assert manager.state_source is None
    assert not manager.sources_desynchronized
    assert manager.active_state == hass.states.get("switch.primary")
    await manager.async_unload()


@pytest.mark.asyncio
async def test_successful_service_call_can_mirror_delayed_peer_state(hass) -> None:
    """A delayed peer update can mirror command result in service-call mode."""

    calls: list[str] = []

    async def _turn_on(call):
        calls.append(call.data["entity_id"])

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert manager.state_source is None
    assert manager.active_state == hass.states.get("switch.primary")

    hass.states.async_set("switch.backup", "on")
    await hass.async_block_till_done()

    assert manager.active_source == "switch.primary"
    assert manager.state_source == "switch.backup"
    assert manager.sources_desynchronized
    assert manager.active_state == hass.states.get("switch.backup")

    hass.states.async_set("switch.primary", "on")
    await hass.async_block_till_done()

    assert manager.state_source is None
    assert not manager.sources_desynchronized
    assert manager.active_state == hass.states.get("switch.primary")
    await manager.async_unload()


@pytest.mark.asyncio
async def test_service_call_validation_does_not_block_on_slow_source(hass) -> None:
    """Service-call mode returns once Home Assistant accepts the service."""

    call_started = asyncio.Event()
    allow_finish = asyncio.Event()

    async def _turn_on(call):
        call_started.set()
        await allow_finish.wait()
        hass.states.async_set(call.data["entity_id"], "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    await asyncio.wait_for(manager.async_call_service("turn_on"), timeout=0.1)

    await asyncio.wait_for(call_started.wait(), timeout=0.1)
    assert manager.last_command_result is not None
    assert manager.last_command_result.success

    allow_finish.set()
    await hass.async_block_till_done()
    await manager.async_unload()


@pytest.mark.asyncio
async def test_latency_selection_waits_for_service_call_to_measure_latency(
    hass,
) -> None:
    """Lowest-latency selection waits for service completion before recording."""

    call_started = asyncio.Event()
    allow_finish = asyncio.Event()

    async def _turn_on(call):
        call_started.set()
        await allow_finish.wait()
        hass.states.async_set(call.data["entity_id"], "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(selection_policy=SelectionPolicy.LOWEST_LATENCY),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await asyncio.wait_for(call_started.wait(), timeout=0.1)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert not task.done()
    assert not manager._health["switch.primary"].latencies

    allow_finish.set()
    await asyncio.wait_for(task, timeout=0.1)
    assert manager._health["switch.primary"].latencies
    await manager.async_unload()


@pytest.mark.asyncio
async def test_state_confirmation_accepts_any_configured_source(hass) -> None:
    """State confirmation succeeds when a peer source publishes the result."""

    calls: list[str] = []

    async def _turn_on(call):
        calls.append(call.data["entity_id"])
        hass.states.async_set("switch.backup", "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(command_validation=CommandValidation.STATE_CONFIRMATION),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await _finish_confirmation(hass, task, manager.config.confirmation_timeout)

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert manager.state_source == "switch.backup"
    assert manager.last_command_result is not None
    assert manager.last_command_result.success
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

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await _finish_confirmation(hass, task, manager.config.confirmation_timeout)

    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    await manager.async_unload()


@pytest.mark.asyncio
async def test_state_confirmation_retries_when_state_does_not_stay_confirmed(
    hass,
) -> None:
    """State confirmation requires the expected state to survive the timeout."""

    calls: list[str] = []

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)
        hass.states.async_set(entity_id, "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(
            command_validation=CommandValidation.STATE_CONFIRMATION,
            confirmation_timeout=5,
        ),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await hass.async_block_till_done()

    hass.states.async_set("switch.primary", "off")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    assert calls == ["switch.primary", "switch.backup"]

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=12))
    await hass.async_block_till_done()
    await task

    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    assert manager.last_command_result.source == "switch.backup"
    assert "switch.primary" in manager.excluded_sources
    await manager.async_unload()


@pytest.mark.asyncio
async def test_number_state_confirmation_uses_entity_state(hass) -> None:
    """Number set_value confirmation compares against the source state."""

    calls: list[str] = []

    async def _set_value(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)
        hass.states.async_set(entity_id, str(float(call.data["value"])))

    hass.services.async_register("number", "set_value", _set_value)
    hass.states.async_set("number.primary", "16")
    hass.states.async_set("number.backup", "8")
    manager = FailoverManager(
        hass,
        _config(
            domain="number",
            sources=("number.primary", "number.backup"),
            command_validation=CommandValidation.STATE_CONFIRMATION,
        ),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("set_value", {"value": 20}))
    await _finish_confirmation(hass, task, manager.config.confirmation_timeout)

    assert calls == ["number.primary"]
    assert manager.active_source == "number.primary"
    assert not manager.excluded_sources
    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    await manager.async_unload()


@pytest.mark.asyncio
async def test_recovery_returns_to_higher_priority_source_when_available(hass) -> None:
    """Recovery returns to priority order when a source becomes operational."""

    hass.states.async_set("switch.primary", "unavailable")
    hass.states.async_set("switch.backup", "on")
    manager = FailoverManager(
        hass,
        _config(
            recovery_stability=30,
        ),
    )
    await manager.async_start()
    assert manager.active_source == "switch.backup"

    hass.states.async_set("switch.primary", "off")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    assert manager.active_source == "switch.primary"
    await manager.async_unload()


@pytest.mark.asyncio
async def test_repairs_alert_is_disabled_by_default(hass) -> None:
    """No Repairs issue is created when all sources are unavailable by default."""

    manager = FailoverManager(hass, _config())
    await manager.async_start()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))
    await hass.async_block_till_done()

    assert manager.active_source is None
    assert manager.state_attributes["failover_active"] is True
    assert manager.diagnostics().repairs_issue_active is False
    await manager.async_unload()


@pytest.mark.asyncio
async def test_repairs_alert_can_be_enabled_with_delay(hass) -> None:
    """A positive Repairs delay creates the all-sources-unavailable issue."""

    manager = FailoverManager(hass, _config(repairs_delay=1))
    await manager.async_start()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()

    assert manager.active_source is None
    assert manager.diagnostics().repairs_issue_active is True
    await manager.async_unload()


@pytest.mark.asyncio
async def test_static_priority_failover_active_when_primary_unavailable(hass) -> None:
    """Failover is active when the preferred static-priority source is down."""

    hass.states.async_set("switch.primary", "unavailable")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    assert manager.nominal_source == "switch.primary"
    assert manager.active_source == "switch.backup"
    assert manager.failover_active
    assert manager.state_attributes["failover_active"] is True
    await manager.async_unload()


@pytest.mark.asyncio
async def test_latency_failover_active_when_fastest_source_unavailable(
    hass,
) -> None:
    """Failover is active when the measured fastest source is down."""

    hass.states.async_set("switch.primary", "unavailable")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(
        hass,
        _config(selection_policy=SelectionPolicy.LOWEST_LATENCY),
    )

    manager._health["switch.primary"].latencies = [0.1]
    manager._health["switch.backup"].latencies = [1.0]
    await manager.async_start()

    assert manager.nominal_source == "switch.primary"
    assert manager.active_source == "switch.backup"
    assert manager.failover_active
    assert manager.state_attributes["nominal_source"] == "switch.primary"
    await manager.async_unload()


@pytest.mark.asyncio
async def test_latency_selection_bootstraps_and_explores(hass) -> None:
    """Unmeasured sources are tried first in configured priority order."""

    calls: list[str] = []

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)
        hass.states.async_set(entity_id, "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")

    manager = FailoverManager(
        hass,
        _config(
            selection_policy=SelectionPolicy.LOWEST_LATENCY,
            recovery_stability=0,
            command_validation=CommandValidation.STATE_CONFIRMATION,
        ),
    )
    await manager.async_start()

    # Initially, both are unmeasured. The first in configured order
    # (switch.primary) is active.
    assert manager.active_source == "switch.primary"
    assert not manager._health["switch.primary"].latencies
    assert not manager._health["switch.backup"].latencies

    # Send a command. It goes to switch.primary, and measures latency.
    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary"]
    assert manager._health["switch.primary"].latencies
    assert not manager._health["switch.backup"].latencies

    # Now switch.backup is the only unmeasured operational source.
    # It should become the active source. We must advance time to trigger
    # the recovery timer callback.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert manager.active_source == "switch.backup"

    # Next command should route to switch.backup to measure it.
    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary", "switch.backup"]
    assert manager._health["switch.backup"].latencies

    # Once all are measured, it picks the faster one.
    # Since they are equal, it falls back to manual order (switch.primary).
    now = dt_util.utcnow()
    manager._health["switch.primary"].latencies = [1.0]
    manager._health["switch.primary"].last_measured = now
    manager._health["switch.backup"].latencies = [1.0]
    manager._health["switch.backup"].last_measured = now
    old_active = manager.active_source
    manager._refresh_health()
    manager._select_after_state_change(old_active)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert manager.active_source == "switch.primary"
    await manager.async_unload()


@pytest.mark.asyncio
async def test_latency_selection_prefers_lower_average(hass) -> None:
    """The manager routes to the source with the lowest average latency."""

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        hass.states.async_set(entity_id, "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")

    manager = FailoverManager(
        hass,
        _config(
            selection_policy=SelectionPolicy.LOWEST_LATENCY,
            recovery_stability=0,
        ),
    )
    await manager.async_start()

    # Manually seed latencies to simulate measurements
    now = dt_util.utcnow()
    manager._health["switch.primary"].latencies = [2.0, 2.5]
    manager._health["switch.primary"].last_measured = now
    manager._health["switch.backup"].latencies = [0.5, 0.4]
    manager._health["switch.backup"].last_measured = now

    # Trigger a refresh
    old_active = manager.active_source
    manager._refresh_health()
    manager._select_after_state_change(old_active)

    # Backup should be active because its average latency (0.45s)
    # is lower than primary (2.25s).
    # We must advance time to trigger the recovery timer callback.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert manager.active_source == "switch.backup"
    assert not manager.degraded
    await manager.async_unload()


@pytest.mark.asyncio
async def test_latency_selection_refreshes_stale_source(hass) -> None:
    """A stale measurement triggers exploration to refresh statistics."""

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        hass.states.async_set(entity_id, "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")

    manager = FailoverManager(
        hass,
        _config(
            selection_policy=SelectionPolicy.LOWEST_LATENCY,
            recovery_stability=0,
        ),
    )
    await manager.async_start()

    # Primary is fast (0.1s) and backup is slow (2.0s)
    now = dt_util.utcnow()
    manager._health["switch.primary"].latencies = [0.1]
    manager._health["switch.primary"].last_measured = now
    manager._health["switch.backup"].latencies = [2.0]
    # Backup measurement is 6 minutes old (stale)
    manager._health["switch.backup"].last_measured = now - timedelta(seconds=360)

    # Trigger refresh
    old_active = manager.active_source
    manager._refresh_health()
    manager._select_after_state_change(old_active)

    # Backup should become active because its latency measurement is
    # stale and needs refresh.
    # We must advance time to trigger the recovery timer callback.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert manager.active_source == "switch.backup"
    await manager.async_unload()
