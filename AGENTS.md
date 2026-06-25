# AGENTS.md

## Project

Entity Failover is a Home Assistant custom integration.

- Domain: `entity_failover`
- Repository: `https://github.com/nicolinuxfr/entities-failover`
- Integration directory: `custom_components/entity_failover/`
- HACS type: integration
- Minimum Home Assistant version: `2026.6.0`
- Runtime dependencies: none outside Home Assistant Core
- Test dependencies: declared in `pyproject.toml` under `.[test]`

The integration creates synthetic Home Assistant entities backed by ordered
source entities. The shared failover engine lives in `manager.py`; domain-specific
behavior is declared in `adapters.py`.

## Git Synchronization

Before modifying the project, always check whether the current branch has
pending changes on its remote tracking branch. Fetch the remote state first and,
if the local branch is behind, pull those changes before editing files. Preserve
any existing local modifications by stashing them when necessary, then reapply
them and resolve any conflicts before starting the requested work.

## Home Assistant Structure

Home Assistant requires a platform file named after each entity domain that an
integration exposes. For example, a synthetic `light` entity requires
`custom_components/entity_failover/light.py`.

The many small platform files are intentional. They are Home Assistant platform
entrypoints and should stay thin. Do not move platform setup logic into those
files; keep it centralized in `platform.py` and use `make_async_setup_entry()`.
The shared implementation can live in subpackages, but the platform entrypoint
files themselves must remain directly under `custom_components/entity_failover/`
because Home Assistant imports platforms by that location.

When adding a domain:

1. Add the domain to the appropriate list in `const.py`.
2. Add its `DomainAdapter` in `adapters.py`.
3. Add a `<domain>.py` platform stub using `make_async_setup_entry("<domain>")`.
4. Add or update tests in `tests/test_adapters.py`.
5. Run the full validation commands below.

## Versioning

## Pre-Public Rename Policy

Until the first public release is published, internal entity suffixes,
translation keys, and diagnostic attribute names may be renamed when it makes
the integration cleaner. Prefer the final public shape over backward
compatibility during this phase. After the first public release, treat these
names as user-facing compatibility surfaces and add migrations or aliases
instead of breaking them.

Keep these versions synchronized for releases:

- `custom_components/entity_failover/manifest.json` key `version`
- `pyproject.toml` project `version`
- release tag, preferably `v<version>`, for example `v0.1.0`

HACS uses GitHub releases when releases exist. A tag alone is not enough for the
release-selection UI; publish an actual GitHub Release. Without releases, HACS
uses the default branch.

`hacs.json` declares the minimum supported Home Assistant version through the
`homeassistant` key. Keep it aligned with the minimum Home Assistant dependency
in `pyproject.toml`.

Run `tests/test_metadata.py` after version changes; it verifies the local version
metadata stays synchronized.

## Local Test Environment

Use a local virtual environment. Do not install dependencies into the system
Python.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Run all checks:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest
```

Do not pass JSON translation files directly to `ruff`; Ruff treats explicit
JSON paths as Python input. Validate translation JSON with `json.tool` instead:

```bash
.venv/bin/python -m json.tool custom_components/entity_failover/translations/en.json >/tmp/entity_failover_en.json
.venv/bin/python -m json.tool custom_components/entity_failover/translations/fr.json >/tmp/entity_failover_fr.json
```

Format code intentionally:

```bash
.venv/bin/python -m ruff format .
.venv/bin/python -m ruff check . --fix
```

Useful targeted tests:

```bash
.venv/bin/python -m pytest tests/test_manager.py
.venv/bin/python -m pytest tests/test_config_flow.py
.venv/bin/python -m pytest tests/test_setup.py
.venv/bin/python -m pytest tests/test_metadata.py
```

## Home Assistant Practices

- No YAML configuration is required or expected.
- Use config flows and options flows for user configuration.
- Keep source tracking event-driven; do not add polling loops.
- Store unsubscribe callbacks and cancel them on unload.
- Do not block the asyncio event loop.
- Entity properties must use state already present in memory.
- Do not edit Home Assistant `.storage` files.
- Prefer entity IDs over device IDs for configured relationships.
- Keep diagnostics redacted and avoid dumping full Home Assistant states.

## HACS Readiness

Required repository shape:

```text
custom_components/entity_failover/manifest.json
hacs.json
README.md
LICENSE
```

Before publishing:

1. Ensure `documentation` and `issue_tracker` in `manifest.json` point to
   `https://github.com/nicolinuxfr/entities-failover`.
2. Create a GitHub Release matching the manifest version.
3. Run the validation commands above.
4. For default HACS inclusion, also run HACS Action and Hassfest in GitHub
   Actions and provide brand assets or submit them through the Home Assistant
   brands process.
