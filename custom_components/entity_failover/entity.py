"""Compatibility exports for Entity Failover entity classes."""

from __future__ import annotations

from .entities import (
    FailoverActiveSourceSensor,
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
    FailoverPrimarySourceInactiveBinarySensor,
)
from .entities.domains import FailoverGenericMainEntity as FailoverMainEntity

__all__ = [
    "FailoverActiveSourceSensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverMainEntity",
    "FailoverNumberEntity",
    "FailoverPrimarySourceInactiveBinarySensor",
]
