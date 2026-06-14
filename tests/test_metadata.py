"""Tests for HACS and Home Assistant metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "entity_failover" / "manifest.json"
HACS = ROOT / "hacs.json"
PYPROJECT = ROOT / "pyproject.toml"
REPOSITORY_URL = "https://github.com/nicolinuxfr/entities-failover"


def test_manifest_has_hacs_required_keys() -> None:
    """The integration manifest contains the keys HACS expects."""

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert {
        "domain",
        "documentation",
        "issue_tracker",
        "codeowners",
        "name",
        "version",
    } <= set(manifest)
    assert manifest["domain"] == "entity_failover"
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "helper"
    assert manifest["iot_class"] == "calculated"
    assert manifest["documentation"] == REPOSITORY_URL
    assert manifest["issue_tracker"] == f"{REPOSITORY_URL}/issues"


def test_versions_are_synchronized() -> None:
    """The package and manifest versions must stay aligned."""

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert manifest["version"] == pyproject["project"]["version"]


def test_hacs_min_homeassistant_matches_test_dependency() -> None:
    """The HACS minimum HA version matches the tested HA floor."""

    hacs = json.loads(HACS.read_text(encoding="utf-8"))
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    test_dependencies = pyproject["project"]["optional-dependencies"]["test"]

    assert f"homeassistant>={hacs['homeassistant']}" in test_dependencies


def test_single_hacs_integration_directory() -> None:
    """HACS should see exactly one custom integration in this repository."""

    integrations = [
        path
        for path in (ROOT / "custom_components").iterdir()
        if path.is_dir() and not path.name.startswith("__")
    ]

    assert [path.name for path in integrations] == ["entity_failover"]
