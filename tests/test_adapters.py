"""Tests for domain adapters."""

from __future__ import annotations

import pytest

from custom_components.entity_failover.adapters import ADAPTERS, adapter_for_domain
from custom_components.entity_failover.const import (
    COMMANDABLE_DOMAINS,
    SUPPORTED_DOMAINS,
)


def test_all_supported_domains_have_adapter() -> None:
    """All declared domains must have an adapter."""

    assert sorted(ADAPTERS) == SUPPORTED_DOMAINS


@pytest.mark.parametrize("domain", COMMANDABLE_DOMAINS)
def test_commandable_domains_have_service_or_intentional_button(domain: str) -> None:
    """Commandable domains expose service routing metadata."""

    adapter = adapter_for_domain(domain)
    assert adapter.services
    assert not adapter.read_only


@pytest.mark.parametrize(
    "domain", ["sensor", "binary_sensor", "weather", "device_tracker"]
)
def test_read_only_domains_are_read_only(domain: str) -> None:
    """Read-only mirror domains are marked read-only."""

    assert adapter_for_domain(domain).read_only
