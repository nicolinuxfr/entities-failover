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

Install as a HACS custom repository of type Integration, restart Home Assistant,
then add **Entity Failover** from **Settings > Devices & services**.

This integration is local, has no Supervisor dependency, and does not require
YAML configuration.

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
- Command validation: service call
- Feature policy: intersection

## Availability Strategies

Simple availability treats a source as usable when it exists, is not
`unavailable`, is not `unknown`, and is not temporarily excluded.

Home Assistant availability treats a source as usable when its state exists and
is not `unavailable`. For read-only domains, `unknown` may remain acceptable.

Entity Failover does not treat an old `last_changed` as a failure. A switch can
stay off for months and still be healthy.

## Command Validation

`none` considers a command successful if the service call does not raise.

`service_call` retries another source when a source service call raises.

`state_confirmation` is advanced and experimental. It waits for a state that is
consistent with the command when that can be done reliably. When a command
cannot be confirmed safely, Entity Failover falls back to `service_call`
behavior rather than inventing a failure.

State confirmation cannot guarantee that real hardware acted. It can only
confirm what the source integration publishes back to Home Assistant.

## Feature Policy

`intersection` announces only features common to all configured sources. This is
the default and is the most stable for dashboards and automations.

`active_source` mirrors the currently active source features. This can expose
more capabilities but may change after a failover.

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
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

