"""Home Assistant domain contract entity classes."""

from .common import FailoverGenericMainEntity, ToggleFailoverEntity
from .light import FailoverLightEntity
from .simple import (
    FailoverButtonEntity,
    FailoverFanEntity,
    FailoverRemoteEntity,
    FailoverSirenEntity,
    FailoverSwitchEntity,
)
from .value import (
    FailoverDateEntity,
    FailoverDateTimeEntity,
    FailoverNumberEntity,
    FailoverSelectEntity,
    FailoverTextEntity,
    FailoverTimeEntity,
)

__all__ = [
    "FailoverButtonEntity",
    "FailoverDateEntity",
    "FailoverDateTimeEntity",
    "FailoverFanEntity",
    "FailoverGenericMainEntity",
    "FailoverLightEntity",
    "FailoverNumberEntity",
    "FailoverRemoteEntity",
    "FailoverSelectEntity",
    "FailoverSirenEntity",
    "FailoverSwitchEntity",
    "FailoverTextEntity",
    "FailoverTimeEntity",
    "ToggleFailoverEntity",
]
