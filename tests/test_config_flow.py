"""Tests for config flow validation."""

from __future__ import annotations

import pytest

from custom_components.entity_failover.config_flow import (
    EntityFailoverConfigFlow,
    _sources_schema,
    _user_schema,
    _validate_sources,
)
from custom_components.entity_failover.const import CONF_DOMAIN, CONF_SOURCES


@pytest.mark.asyncio
async def test_validate_refuses_single_source(hass) -> None:
    """A failover entity needs at least two sources."""

    assert _validate_sources(hass, "switch", ["switch.one"], None) == "too_few_sources"


@pytest.mark.asyncio
async def test_validate_refuses_duplicates(hass) -> None:
    """A source cannot be selected twice."""

    assert (
        _validate_sources(hass, "switch", ["switch.one", "switch.one"], None)
        == "duplicate_sources"
    )


@pytest.mark.asyncio
async def test_validate_refuses_mixed_domains(hass) -> None:
    """All sources must match the selected domain."""

    assert (
        _validate_sources(hass, "switch", ["switch.one", "light.two"], None)
        == "mixed_domains"
    )


@pytest.mark.asyncio
async def test_validate_refuses_unsupported_domain(hass) -> None:
    """All sources must use a supported domain."""

    assert (
        _validate_sources(
            hass, "automation", ["automation.one", "automation.two"], None
        )
        == "unsupported_domain"
    )


def test_source_selectors_default_to_empty_lists() -> None:
    """Multiple entity selectors must never receive None as a default."""

    assert _user_schema()({})[CONF_SOURCES] == []
    assert _sources_schema("switch")({})[CONF_SOURCES] == []


@pytest.mark.asyncio
async def test_config_flow_creates_entry(hass) -> None:
    """The UI flow creates a config entry."""

    hass.states.async_set("switch.one", "on")
    hass.states.async_set("switch.two", "off")

    flow = EntityFailoverConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    result = await flow.async_step_user()
    assert result["type"] == "form"

    result = await flow.async_step_user(
        {"name": "Kitchen Switch", CONF_SOURCES: ["switch.one", "switch.two"]},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "general"

    result = await flow.async_step_general(
        {
            "availability_strategy": "simple",
            "recovery_stability": 30,
            "failure_cooldown": 60,
            "feature_policy": "intersection",
        },
    )
    result = await flow.async_step_advanced(
        {
            "command_validation": "service_call",
            "confirmation_timeout": 10,
            "max_attempts": 3,
        },
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Kitchen Switch"
    assert result["data"][CONF_DOMAIN] == "switch"
