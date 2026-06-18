"""Entity classes for Entity Failover."""

from .diagnostics import (
    FailoverActiveSourceSensor,
    FailoverAllSourcesUnavailableBinarySensor,
    FailoverPrimarySourceInactiveBinarySensor,
)
from .domains import (
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
    main_entity_for_manager,
)

__all__ = [
    "FailoverActiveSourceSensor",
    "FailoverAllSourcesUnavailableBinarySensor",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverNumberEntity",
    "FailoverPrimarySourceInactiveBinarySensor",
    "main_entity_for_manager",
]
