"""Compatibility exports for Entity Failover entity classes."""

from __future__ import annotations

from .entities import (
    FailoverActiveSourceSensor,
    FailoverDegradedBinarySensor,
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
)
from .entities.domains import FailoverGenericMainEntity as FailoverMainEntity

__all__ = [
    "FailoverActiveSourceSensor",
    "FailoverDegradedBinarySensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverMainEntity",
    "FailoverNumberEntity",
]
