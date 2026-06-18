"""Compatibility exports for Entity Failover entity classes."""

from __future__ import annotations

from .entities import (
    FailoverActiveBinarySensor,
    FailoverActiveSourceSensor,
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
)
from .entities.domains import FailoverGenericMainEntity as FailoverMainEntity

__all__ = [
    "FailoverActiveBinarySensor",
    "FailoverActiveSourceSensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverMainEntity",
    "FailoverNumberEntity",
]
