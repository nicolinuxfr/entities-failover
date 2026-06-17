"""Helper functions for Entity Failover."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def entity_domain(entity_id: str) -> str:
    """Return the domain part of an entity id."""

    return entity_id.split(".", 1)[0]


def normalize_sources(sources: Iterable[str]) -> list[str]:
    """Normalize and strip an iterable of entity ids."""

    return [str(source).strip() for source in sources if str(source).strip()]


def state_available(state: State | None, allow_unknown: bool = False) -> bool:
    """Return whether a Home Assistant state is usable."""

    if state is None:
        return False
    if state.state == "unavailable":
        return False
    if not allow_unknown and state.state == "unknown":
        return False
    return True


def state_supported_features(state: State | None) -> int:
    """Read supported_features from a state."""

    if state is None:
        return 0
    value = state.attributes.get("supported_features", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def shared_supported_features(states: Iterable[State | None]) -> int:
    """Calculate the bitwise feature intersection for states."""

    features: list[int] = [state_supported_features(state) for state in states]
    if not features:
        return 0
    result = features[0]
    for value in features[1:]:
        result &= value
    return result


def friendly_name(hass: HomeAssistant, entity_id: str | None) -> str | None:
    """Return a friendly name for an entity id."""

    if entity_id is None:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return state.name or entity_id


def is_entity_failover_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Return whether an entity belongs to this integration."""

    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    return entry is not None and entry.platform == DOMAIN


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Redact values that might contain credentials."""

    sensitive = {"token", "access_token", "refresh_token", "password", "secret", "key"}
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if any(part in key.lower() for part in sensitive):
            redacted[key] = "**REDACTED**"
        elif isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
        else:
            redacted[key] = value
    return redacted
