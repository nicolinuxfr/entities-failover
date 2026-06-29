"""Tests for failover manager behavior."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.entity_failover.const import (
    CONF_DOMAIN,
    CONF_LEARNING_ENABLED,
    CONF_SOURCES,
    DOMAIN,
    SUBENTRY_TYPE_FAILOVER,
)
from custom_components.entity_failover.manager import FailoverManager
from custom_components.entity_failover.model import (
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
        "recovery_stability": 30,
        "failure_cooldown": 60,
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
        _config(learning_enabled=True),
    )
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    assert calls == ["switch.primary", "switch.backup"]
    assert manager.active_source == "switch.backup"
    assert "switch.primary" in manager.excluded_sources
    assert manager.learning_progress == {
        "switch.primary": 0,
        "switch.backup": 1,
    }
    await manager.async_unload()


@pytest.mark.asyncio
async def test_repeated_command_failures_back_off_source_recovery(hass) -> None:
    """Repeated command failures keep an unstable source excluded for longer."""

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
        _config(failure_cooldown=10, recovery_stability=1),
    )
    await manager.async_start()

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    first_excluded_until = manager._health["switch.primary"].excluded_until
    assert first_excluded_until is not None
    assert manager._health["switch.primary"].consecutive_failures == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()
    assert manager.active_source == "switch.primary"

    await manager.async_call_service("turn_on")
    await hass.async_block_till_done()

    second_excluded_until = manager._health["switch.primary"].excluded_until
    assert second_excluded_until is not None
    assert manager._health["switch.primary"].consecutive_failures == 2
    assert second_excluded_until - dt_util.utcnow() > timedelta(seconds=15)
    assert calls == [
        "switch.primary",
        "switch.backup",
        "switch.primary",
        "switch.backup",
    ]
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
async def test_confirmation_timeout_does_not_retry_accepted_service(hass) -> None:
    """Accepted service calls are not retried when state confirmation is late."""

    calls: list[str] = []

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await hass.async_block_till_done()

    assert calls == ["switch.primary"]
    assert not task.done()

    async_fire_time_changed(
        hass,
        dt_util.utcnow() + timedelta(seconds=10 + 1),
    )
    await hass.async_block_till_done()
    await task

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert not manager.excluded_sources
    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    assert manager.last_command_result.source == "switch.primary"

    hass.states.async_set("switch.primary", "on")
    await hass.async_block_till_done()

    assert manager.state_source is None
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

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await hass.async_block_till_done()

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert manager.state_source is None
    assert manager.active_state == hass.states.get("switch.primary")

    hass.states.async_set("switch.backup", "on")
    await hass.async_block_till_done()
    await task

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
    """Services without reliable confirmation stay non-blocking."""

    call_started = asyncio.Event()
    allow_finish = asyncio.Event()

    async def _press(call):
        call_started.set()
        await allow_finish.wait()

    hass.services.async_register("button", "press", _press)
    hass.states.async_set("button.primary", "2026-06-26T12:00:00+00:00")
    hass.states.async_set("button.backup", "2026-06-26T12:00:00+00:00")
    manager = FailoverManager(
        hass,
        _config(
            domain="button",
            sources=("button.primary", "button.backup"),
        ),
    )
    await manager.async_start()

    await asyncio.wait_for(manager.async_call_service("press"), timeout=0.1)

    await asyncio.wait_for(call_started.wait(), timeout=0.1)
    assert manager.last_command_result is not None
    assert manager.last_command_result.success

    allow_finish.set()
    await hass.async_block_till_done()
    await manager.async_unload()


@pytest.mark.asyncio
async def test_learning_waits_for_service_call_to_measure_latency(
    hass,
) -> None:
    """Learning waits for service completion before recording."""

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
        _config(learning_enabled=True),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await asyncio.wait_for(call_started.wait(), timeout=0.1)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert not task.done()
    assert manager.learning_progress["switch.primary"] == 0

    allow_finish.set()
    await asyncio.wait_for(task, timeout=0.1)
    assert manager.learning_progress["switch.primary"] == 1
    await manager.async_unload()


@pytest.mark.asyncio
async def test_command_confirmation_accepts_any_configured_source(hass) -> None:
    """Command confirmation succeeds when a peer source publishes the result."""

    calls: list[str] = []

    async def _turn_on(call):
        calls.append(call.data["entity_id"])
        hass.states.async_set("switch.backup", "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await _finish_confirmation(hass, task, 10)

    assert calls == ["switch.primary"]
    assert manager.active_source == "switch.primary"
    assert manager.state_source == "switch.backup"
    assert manager.last_command_result is not None
    assert manager.last_command_result.success
    await manager.async_unload()


@pytest.mark.asyncio
async def test_command_confirmation_success(hass) -> None:
    """Command confirmation succeeds when the source publishes expected state."""

    async def _turn_on(call):
        hass.states.async_set(call.data["entity_id"], "on")

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config())
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("turn_on"))
    await _finish_confirmation(hass, task, 10)

    assert manager.last_command_result is not None
    assert manager.last_command_result.success
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
        ),
    )
    await manager.async_start()

    task = asyncio.create_task(manager.async_call_service("set_value", {"value": 20}))
    await _finish_confirmation(hass, task, 10)

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
@pytest.mark.asyncio
async def test_learning_rotates_commands_without_changing_active_source(hass) -> None:
    """Learning balances real commands while state priority remains static."""

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
            learning_enabled=True,
        ),
    )
    await manager.async_start()

    assert manager.active_source == "switch.primary"
    for _ in range(4):
        await manager.async_call_service("turn_on")
        await hass.async_block_till_done()

    assert calls == [
        "switch.primary",
        "switch.backup",
        "switch.primary",
        "switch.backup",
    ]
    assert manager.active_source == "switch.primary"
    assert manager.learning_progress == {
        "switch.primary": 2,
        "switch.backup": 2,
    }
    await manager.async_unload()


@pytest.mark.asyncio
async def test_learning_never_rotates_source_from_state_events(hass) -> None:
    """Ordinary state updates do not change priority during learning."""

    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    manager = FailoverManager(hass, _config(learning_enabled=True))
    await manager.async_start()

    for state in ("on", "off", "on"):
        hass.states.async_set("switch.backup", state)
        await hass.async_block_till_done()

    assert manager.active_source == "switch.primary"
    assert manager.learning_progress == {
        "switch.primary": 0,
        "switch.backup": 0,
    }
    await manager.async_unload()


@pytest.mark.asyncio
async def test_learning_skips_sources_incompatible_with_command(hass) -> None:
    """A source without required features receives no learning sample."""

    calls: list[str] = []

    async def _turn_on(call):
        entity_id = call.data["entity_id"]
        calls.append(entity_id)
        hass.states.async_set(entity_id, "on", {"supported_features": 1})

    hass.services.async_register("switch", "turn_on", _turn_on)
    hass.states.async_set("switch.primary", "off", {"supported_features": 0})
    hass.states.async_set("switch.backup", "off", {"supported_features": 1})
    manager = FailoverManager(hass, _config(learning_enabled=True))
    await manager.async_start()

    await manager.async_call_service("turn_on", required_features=1)

    assert calls == ["switch.backup"]
    assert manager.learning_progress == {
        "switch.primary": 0,
        "switch.backup": 1,
    }
    await manager.async_unload()


@pytest.mark.asyncio
async def test_learning_writes_median_order_and_disables_itself(hass) -> None:
    """Completed learning persists median order and disables the checkbox."""

    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Entity Failover",
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Kitchen Switch",
                    CONF_DOMAIN: "switch",
                    CONF_SOURCES: ["switch.primary", "switch.backup"],
                    CONF_LEARNING_ENABLED: True,
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Kitchen Switch",
                "unique_id": "learning-order",
            }
        ],
        version=3,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))
    manager = FailoverManager(
        hass,
        FailoverConfig.from_subentry(entry, subentry),
        entry,
    )
    await manager.async_start()

    for latency in (0.8, 1.0, 1.2):
        await manager._async_record_learning_sample("switch.primary", latency)
    for latency in (0.1, 0.2, 0.3):
        await manager._async_record_learning_sample("switch.backup", latency)

    updated = entry.subentries[subentry.subentry_id]
    assert updated.data[CONF_SOURCES] == ["switch.backup", "switch.primary"]
    assert updated.data[CONF_LEARNING_ENABLED] is False
    assert manager.learned_latencies == {
        "switch.primary": 1.0,
        "switch.backup": 0.2,
    }
    await manager.async_unload()


@pytest.mark.asyncio
async def test_learning_samples_survive_manager_reload(hass) -> None:
    """Incomplete learning resumes from persisted samples."""

    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    config = _config(learning_enabled=True, unique_id="persist-learning")
    manager = FailoverManager(hass, config)
    await manager.async_start()
    await manager._async_record_learning_sample("switch.primary", 0.4)
    await manager.async_unload()

    restored = FailoverManager(hass, config)
    await restored.async_start()

    assert restored.learning_progress == {
        "switch.primary": 1,
        "switch.backup": 0,
    }
    await restored.async_unload()


@pytest.mark.asyncio
async def test_learning_partially_orders_available_sources(hass) -> None:
    """Unavailable sources stay last and can be evaluated after returning."""

    hass.states.async_set("switch.primary", "off")
    hass.states.async_set("switch.backup", "off")
    hass.states.async_set("switch.offline", "unavailable")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Entity Failover",
        data={},
        subentries_data=[
            {
                "data": {
                    "name": "Kitchen Switch",
                    CONF_DOMAIN: "switch",
                    CONF_SOURCES: [
                        "switch.primary",
                        "switch.backup",
                        "switch.offline",
                    ],
                    CONF_LEARNING_ENABLED: True,
                },
                "subentry_type": SUBENTRY_TYPE_FAILOVER,
                "title": "Kitchen Switch",
                "unique_id": "partial-learning",
            }
        ],
        version=3,
    )
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))
    manager = FailoverManager(
        hass,
        FailoverConfig.from_subentry(entry, subentry),
        entry,
    )
    await manager.async_start()

    for latency in (0.8, 1.0, 1.2):
        await manager._async_record_learning_sample("switch.primary", latency)
    for latency in (0.1, 0.2, 0.3):
        await manager._async_record_learning_sample("switch.backup", latency)

    updated = entry.subentries[subentry.subentry_id]
    assert updated.data[CONF_SOURCES] == [
        "switch.backup",
        "switch.primary",
        "switch.offline",
    ]
    assert updated.data[CONF_LEARNING_ENABLED] is True
    assert manager.learning_status == "partial"

    hass.states.async_set("switch.offline", "off")
    await hass.async_block_till_done()
    for latency in (0.04, 0.05, 0.06):
        await manager._async_record_learning_sample("switch.offline", latency)

    completed = entry.subentries[subentry.subentry_id]
    assert completed.data[CONF_SOURCES] == [
        "switch.offline",
        "switch.backup",
        "switch.primary",
    ]
    assert completed.data[CONF_LEARNING_ENABLED] is False
    await manager.async_unload()
