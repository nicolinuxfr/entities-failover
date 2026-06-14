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
