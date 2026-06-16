# Entity Failover

Entity Failover is a Home Assistant custom integration that creates synthetic
entities backed by several equivalent source entities ordered by priority.

Example:

```text
cover.salon_volet
├── priority 1: cover.salon_volet_homekit
├── priority 2: cover.salon_volet_tahoma
└── priority 3: cover.salon_volet_mqtt
```

Automations and dashboards use only the synthetic entity, for example
`cover.salon_volet`.

## Installation

Install `https://github.com/nicolinuxfr/entities-failover` as a HACS custom
repository of type Integration, restart Home Assistant, then add
**Entity Failover** from **Settings > Devices & services**.

This integration is local, has no Supervisor dependency, and does not require
YAML configuration.

The integration ships local brand images in
`custom_components/entity_failover/brand/`, which Home Assistant 2026.3 and
newer can expose to the UI and HACS.

## Supported Domains

Commandable domains:

`alarm_control_panel`, `button`, `climate`, `cover`, `date`, `datetime`, `fan`,
`humidifier`, `lawn_mower`, `light`, `lock`, `media_player`, `number`, `remote`,
`scene`, `select`, `siren`, `switch`, `text`, `time`, `update`, `vacuum`,
`valve`, `water_heater`.

Read-only or mostly mirrored domains:

`air_quality`, `binary_sensor`, `device_tracker`, `sensor`, `weather`.

Specialized domains exposed as conservative mirrors in v1:

`calendar`, `camera`, `image`, `todo`.

Excluded from v1: `ai_task`, `assist_satellite`, `conversation`, `event`,
`infrared`, `notify`, `radio_frequency`, `speech-to-text`, `text-to-speech`,
`wake_word`.

## Behavior

The active source is the first operational source in the configured priority
order. If the active source becomes unavailable, Entity Failover immediately
switches to the next usable source. When a higher-priority source returns, it
must remain stable for the configured recovery delay before it becomes active
again.

Defaults:

- Recovery stability: 30 seconds
- Failure cooldown: 60 seconds
- Command verification: retry if the service call fails
- Exposed features: features shared by every source

## Source Availability

Entity Failover treats a source as usable when it exists, is not
`unavailable`, is not `unknown`, and is not temporarily excluded.

Entity Failover does not treat an old `last_changed` as a failure. A switch can
stay off for months and still be healthy.

## Command Verification

By default, Entity Failover retries another source when the active source
service call raises an error.

State confirmation is advanced and experimental. It waits for a state that is
consistent with the command when that can be done reliably. When a command
cannot be confirmed safely, Entity Failover falls back to service-call behavior
rather than inventing a failure.

State confirmation cannot guarantee that real hardware acted. It can only
confirm what the source integration publishes back to Home Assistant.

## Feature Policy

The default policy announces only features common to all configured sources.
This is the most stable behavior for dashboards and automations.

The active-source policy mirrors the currently active source features. This can
expose more capabilities but may change after a failover.

## Diagnostics

Each synthetic device includes:

- the main synthetic entity;
- `sensor.<name>_active_source`;
- `binary_sensor.<name>_degraded`;
- `button.<name>_clear_failures`.

`clear_failures` clears temporary exclusions and immediately recalculates the
active source.

If every source remains unusable for five minutes, Entity Failover creates one
Repairs issue for that config entry and removes it after recovery.

## Examples

Two fans:

```text
fan.bedroom_air
├── fan.bedroom_air_zigbee
└── fan.bedroom_air_ir_bridge
```

Several Somfy covers exposed through different integrations:

```text
cover.living_room_shutter
├── cover.living_room_shutter_homekit
├── cover.living_room_shutter_tahoma
└── cover.living_room_shutter_mqtt
```

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest
```
