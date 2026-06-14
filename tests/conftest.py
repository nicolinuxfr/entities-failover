"""Pytest fixtures for Entity Failover."""

from __future__ import annotations

import sys

import pytest

sys.path = [path for path in sys.path if not path.startswith("__editable__.")]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant tests."""

    yield
