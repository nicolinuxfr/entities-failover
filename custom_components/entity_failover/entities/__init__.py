"""Entity classes for Entity Failover."""

from .diagnostics import (
    FailoverActiveSourceSensor,
    FailoverClearFailuresButton,
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
    "FailoverClearFailuresButton",
    "FailoverDegradedBinarySensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverNumberEntity",
    "main_entity_for_manager",
]
