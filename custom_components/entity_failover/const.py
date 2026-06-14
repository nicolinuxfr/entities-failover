"""Constants for Entity Failover."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "entity_failover"
NAME: Final = "Entity Failover"
VERSION: Final = "0.1.0"

CONF_DOMAIN: Final = "domain"
CONF_SOURCES: Final = "sources"
CONF_AVAILABILITY_STRATEGY: Final = "availability_strategy"
CONF_COMMAND_VALIDATION: Final = "command_validation"
CONF_CONFIRMATION_TIMEOUT: Final = "confirmation_timeout"
CONF_FAILURE_COOLDOWN: Final = "failure_cooldown"
CONF_RECOVERY_STABILITY: Final = "recovery_stability"
CONF_MAX_ATTEMPTS: Final = "max_attempts"
CONF_FEATURE_POLICY: Final = "feature_policy"

DEFAULT_AVAILABILITY_STRATEGY: Final = "simple"
DEFAULT_COMMAND_VALIDATION: Final = "service_call"
DEFAULT_CONFIRMATION_TIMEOUT: Final = 10.0
DEFAULT_FAILURE_COOLDOWN: Final = 60.0
DEFAULT_RECOVERY_STABILITY: Final = 30.0
DEFAULT_MAX_ATTEMPTS: Final = 3
DEFAULT_FEATURE_POLICY: Final = "intersection"
DEFAULT_REPAIRS_DELAY: Final = 300.0

ATTR_ACTIVE_SOURCE: Final = "active_source"
ATTR_PRIORITY_INDEX: Final = "priority_index"
ATTR_DEGRADED: Final = "degraded"
ATTR_AVAILABLE_SOURCES: Final = "available_sources"
ATTR_EXCLUDED_SOURCES: Final = "excluded_sources"
ATTR_FORWARDED_ENTITY_ID: Final = "forwarded_entity_id"
ATTR_SOURCE_COUNT: Final = "source_count"

SERVICE_CLEAR_FAILURES: Final = "clear_failures"

SUBENTRY_TYPE_FAILOVER: Final = "failover"

AVAILABILITY_STRATEGIES: Final = ["simple", "home_assistant"]
COMMAND_VALIDATION_MODES: Final = ["none", "service_call", "state_confirmation"]
FEATURE_POLICIES: Final = ["intersection", "active_source"]

COMMANDABLE_DOMAINS: Final = [
    "alarm_control_panel",
    "button",
    "climate",
    "cover",
    "date",
    "datetime",
    "fan",
    "humidifier",
    "lawn_mower",
    "light",
    "lock",
    "media_player",
    "number",
    "remote",
    "scene",
    "select",
    "siren",
    "switch",
    "text",
    "time",
    "update",
    "vacuum",
    "valve",
    "water_heater",
]

READ_ONLY_DOMAINS: Final = [
    "air_quality",
    "binary_sensor",
    "device_tracker",
    "sensor",
    "weather",
]

SPECIALIZED_DOMAINS: Final = [
    "calendar",
    "camera",
    "image",
    "todo",
]

SUPPORTED_DOMAINS: Final = sorted(
    COMMANDABLE_DOMAINS + READ_ONLY_DOMAINS + SPECIALIZED_DOMAINS
)

DIAGNOSTIC_PLATFORMS: Final = ["sensor", "binary_sensor", "button"]
PLATFORMS: Final = sorted(set(SUPPORTED_DOMAINS + DIAGNOSTIC_PLATFORMS))

EXCLUDED_DOMAINS: Final = [
    "ai_task",
    "assist_satellite",
    "conversation",
    "event",
    "infrared",
    "notify",
    "radio_frequency",
    "speech-to-text",
    "text-to-speech",
    "wake_word",
]

ISSUE_ALL_SOURCES_UNAVAILABLE: Final = "all_sources_unavailable"
