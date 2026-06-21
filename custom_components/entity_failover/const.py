"""Constants for Entity Failover."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "entity_failover"
NAME: Final = "Entity Failover"
VERSION: Final = "0.1.0"

CONF_DOMAIN: Final = "domain"
CONF_SOURCES: Final = "sources"
CONF_COMMAND_VALIDATION: Final = "command_validation"
CONF_CONFIRMATION_TIMEOUT: Final = "confirmation_timeout"
CONF_FAILURE_COOLDOWN: Final = "failure_cooldown"
CONF_RECOVERY_STABILITY: Final = "recovery_stability"
CONF_FEATURE_POLICY: Final = "feature_policy"
CONF_HIDE_SOURCES: Final = "hide_sources"
CONF_REPAIRS_DELAY: Final = "repairs_delay"
CONF_SELECTION_POLICY: Final = "selection_policy"

DEFAULT_COMMAND_VALIDATION: Final = "service_call"
DEFAULT_CONFIRMATION_TIMEOUT: Final = 10.0
DEFAULT_FAILURE_COOLDOWN: Final = 60.0
DEFAULT_RECOVERY_STABILITY: Final = 30.0
DEFAULT_FEATURE_POLICY: Final = "intersection"
DEFAULT_HIDE_SOURCES: Final = False
DEFAULT_REPAIRS_DELAY: Final = 0.0
DEFAULT_SELECTION_POLICY: Final = "static_priority"

ATTR_ACTIVE_SOURCE: Final = "active_source"
ATTR_STATE_SOURCE: Final = "state_source"
ATTR_SOURCES_DESYNCHRONIZED: Final = "sources_desynchronized"
ATTR_PRIORITY_INDEX: Final = "priority_index"
ATTR_DEGRADED: Final = "degraded"
ATTR_AVAILABLE_SOURCES: Final = "available_sources"
ATTR_EXCLUDED_SOURCES: Final = "excluded_sources"
ATTR_FORWARDED_ENTITY_ID: Final = "forwarded_entity_id"
ATTR_SOURCE_COUNT: Final = "source_count"
ATTR_FAILOVER_ACTIVE: Final = "failover_active"
ATTR_NOMINAL_SOURCE: Final = "nominal_source"

SERVICE_CLEAR_FAILURES: Final = "clear_failures"

SUBENTRY_TYPE_FAILOVER: Final = "failover"

COMMAND_VALIDATION_MODES: Final = ["service_call", "state_confirmation"]
FEATURE_POLICIES: Final = ["intersection", "active_source"]
SELECTION_POLICIES: Final = ["static_priority", "lowest_latency"]

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

DIAGNOSTIC_PLATFORMS: Final = ["sensor", "binary_sensor"]
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
