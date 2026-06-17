"""Entity classes for Entity Failover."""

from .diagnostics import (
    FailoverActiveSourceSensor,
    FailoverDegradedBinarySensor,
)
from .domains import (
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
    main_entity_for_manager,
)

__all__ = [
    "FailoverActiveSourceSensor",
    "FailoverDegradedBinarySensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverNumberEntity",
    "main_entity_for_manager",
]
