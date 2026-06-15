"""Typed models for Entity Failover."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_NAME

from .const import (
    CONF_AVAILABILITY_STRATEGY,
    CONF_COMMAND_VALIDATION,
    CONF_CONFIRMATION_TIMEOUT,
    CONF_DOMAIN,
    CONF_FAILURE_COOLDOWN,
    CONF_FEATURE_POLICY,
    CONF_MAX_ATTEMPTS,
    CONF_RECOVERY_STABILITY,
    CONF_SOURCES,
    DEFAULT_AVAILABILITY_STRATEGY,
    DEFAULT_COMMAND_VALIDATION,
    DEFAULT_CONFIRMATION_TIMEOUT,
    DEFAULT_FAILURE_COOLDOWN,
    DEFAULT_FEATURE_POLICY,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_RECOVERY_STABILITY,
)


class AvailabilityStrategy(StrEnum):
    """Source availability strategies."""

    SIMPLE = "simple"
    HOME_ASSISTANT = "home_assistant"


class CommandValidation(StrEnum):
    """Command validation modes."""

    NONE = "none"
    SERVICE_CALL = "service_call"
    STATE_CONFIRMATION = "state_confirmation"


class FeaturePolicy(StrEnum):
    """Supported feature calculation policies."""

    INTERSECTION = "intersection"
    ACTIVE_SOURCE = "active_source"


@dataclass(slots=True, frozen=True)
class FailoverConfig:
    """Normalized config entry data/options."""

    entry_id: str
    unique_id: str
    name: str
    domain: str
    sources: tuple[str, ...]
    availability_strategy: AvailabilityStrategy = AvailabilityStrategy.SIMPLE
    command_validation: CommandValidation = CommandValidation.SERVICE_CALL
    confirmation_timeout: float = DEFAULT_CONFIRMATION_TIMEOUT
    failure_cooldown: float = DEFAULT_FAILURE_COOLDOWN
    recovery_stability: float = DEFAULT_RECOVERY_STABILITY
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    feature_policy: FeaturePolicy = FeaturePolicy.INTERSECTION
    subentry_id: str | None = None

    @classmethod
    def from_subentry(
        cls,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> FailoverConfig:
        """Create normalized config from a config subentry."""

        data = subentry.data
        return cls(
            entry_id=entry.entry_id,
            subentry_id=subentry.subentry_id,
            unique_id=subentry.unique_id or subentry.subentry_id,
            name=str(data.get(CONF_NAME, subentry.title)),
            domain=str(data[CONF_DOMAIN]),
            sources=tuple(str(source) for source in data[CONF_SOURCES]),
            availability_strategy=AvailabilityStrategy(
                data.get(CONF_AVAILABILITY_STRATEGY, DEFAULT_AVAILABILITY_STRATEGY)
            ),
            command_validation=CommandValidation(
                data.get(CONF_COMMAND_VALIDATION, DEFAULT_COMMAND_VALIDATION)
            ),
            confirmation_timeout=float(
                data.get(CONF_CONFIRMATION_TIMEOUT, DEFAULT_CONFIRMATION_TIMEOUT)
            ),
            failure_cooldown=float(
                data.get(CONF_FAILURE_COOLDOWN, DEFAULT_FAILURE_COOLDOWN)
            ),
            recovery_stability=float(
                data.get(CONF_RECOVERY_STABILITY, DEFAULT_RECOVERY_STABILITY)
            ),
            max_attempts=int(data.get(CONF_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS)),
            feature_policy=FeaturePolicy(
                data.get(CONF_FEATURE_POLICY, DEFAULT_FEATURE_POLICY)
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return {
            "entry_id": self.entry_id,
            "subentry_id": self.subentry_id,
            "unique_id": self.unique_id,
            "name": self.name,
            "domain": self.domain,
            "sources": list(self.sources),
            "availability_strategy": self.availability_strategy.value,
            "command_validation": self.command_validation.value,
            "confirmation_timeout": self.confirmation_timeout,
            "failure_cooldown": self.failure_cooldown,
            "recovery_stability": self.recovery_stability,
            "max_attempts": self.max_attempts,
            "feature_policy": self.feature_policy.value,
        }


@dataclass(slots=True)
class SourceHealth:
    """Runtime health data for one source."""

    entity_id: str
    exists: bool = False
    available: bool = False
    excluded_until: datetime | None = None
    last_error: str | None = None

    @property
    def excluded(self) -> bool:
        """Return whether the source is currently excluded."""

        return self.excluded_until is not None

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return {
            "entity_id": self.entity_id,
            "exists": self.exists,
            "available": self.available,
            "excluded_until": self.excluded_until.isoformat()
            if self.excluded_until
            else None,
            "last_error": self.last_error,
        }


@dataclass(slots=True)
class CommandResult:
    """Last command routing result."""

    service: str
    source: str | None
    success: bool
    attempts: int
    error: str | None = None
    when: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return {
            "service": self.service,
            "source": self.source,
            "success": self.success,
            "attempts": self.attempts,
            "error": self.error,
            "when": self.when.isoformat() if self.when else None,
        }


@dataclass(slots=True)
class ManagerDiagnostics:
    """Serializable manager diagnostics."""

    entry: dict[str, Any]
    active_source: str | None
    source_health: dict[str, dict[str, Any]]
    temporary_exclusions: dict[str, str]
    pending_recovery: str | None
    last_failover: str | None
    last_command_result: dict[str, Any] | None
    repairs_issue_active: bool
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a dictionary for diagnostics."""

        return {
            "entry": self.entry,
            "active_source": self.active_source,
            "source_health": self.source_health,
            "temporary_exclusions": self.temporary_exclusions,
            "pending_recovery": self.pending_recovery,
            "last_failover": self.last_failover,
            "last_command_result": self.last_command_result,
            "repairs_issue_active": self.repairs_issue_active,
            **self.extra,
        }
