"""Domain entity factory for Entity Failover."""

from __future__ import annotations

from ..manager import FailoverManager
from .base import FailoverEntityMixin
from .domain_contracts import (
    FailoverButtonEntity,
    FailoverDateEntity,
    FailoverDateTimeEntity,
    FailoverFanEntity,
    FailoverGenericMainEntity,
    FailoverLightEntity,
    FailoverNumberEntity,
    FailoverRemoteEntity,
    FailoverSelectEntity,
    FailoverSirenEntity,
    FailoverSwitchEntity,
    FailoverTextEntity,
    FailoverTimeEntity,
)

DOMAIN_ENTITY_CLASSES: dict[str, type[FailoverEntityMixin]] = {
    "button": FailoverButtonEntity,
    "date": FailoverDateEntity,
    "datetime": FailoverDateTimeEntity,
    "fan": FailoverFanEntity,
    "light": FailoverLightEntity,
    "number": FailoverNumberEntity,
    "remote": FailoverRemoteEntity,
    "select": FailoverSelectEntity,
    "siren": FailoverSirenEntity,
    "switch": FailoverSwitchEntity,
    "text": FailoverTextEntity,
    "time": FailoverTimeEntity,
}


def main_entity_for_manager(manager: FailoverManager) -> FailoverEntityMixin:
    """Build the best main entity class for one manager."""

    entity_cls = DOMAIN_ENTITY_CLASSES.get(
        manager.config.domain,
        FailoverGenericMainEntity,
    )
    return entity_cls(manager)
