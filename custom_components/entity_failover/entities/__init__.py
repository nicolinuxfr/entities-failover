"""Entity classes for Entity Failover."""

from .diagnostics import (
    FailoverActiveBinarySensor,
    FailoverActiveSourceSensor,
)
from .domains import (
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
    main_entity_for_manager,
)

__all__ = [
    "FailoverActiveBinarySensor",
    "FailoverActiveSourceSensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverNumberEntity",
    "main_entity_for_manager",
]
