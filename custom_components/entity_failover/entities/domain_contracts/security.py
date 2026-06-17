"""Security-based domain contracts."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.components.lock import LockEntity, LockEntityFeature

from ..base import FailoverEntityMixin
from ..routes import AlarmControlPanelRouteMixin, LockRouteMixin


class FailoverLockEntity(LockRouteMixin, FailoverEntityMixin, LockEntity):
    """Main failover entity for lock."""

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        return state_val == "locked"

    @property
    def is_locking(self) -> bool | None:
        """Return true if lock is locking."""

        return self._native_state_value() == "locking"

    @property
    def is_unlocking(self) -> bool | None:
        """Return true if lock is unlocking."""

        return self._native_state_value() == "unlocking"

    @property
    def is_jammed(self) -> bool | None:
        """Return true if lock is jammed."""

        return self._bool_attribute("is_jammed")

    @property
    def supported_features(self) -> LockEntityFeature:
        """Return the list of supported features."""

        return LockEntityFeature(super().supported_features)


class FailoverAlarmControlPanelEntity(
    AlarmControlPanelRouteMixin, FailoverEntityMixin, AlarmControlPanelEntity
):
    """Main failover entity for alarm control panel."""

    @property
    def state(self) -> str | None:
        """Return the state of the device."""

        return self._native_state_value()

    @property
    def code_format(self) -> str | None:
        """Regex for code format or None if no code is required."""

        return self._string_attribute("code_format")

    @property
    def changed_by(self) -> str | None:
        """Last change triggered by."""

        return self._string_attribute("changed_by")

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""

        return AlarmControlPanelEntityFeature(super().supported_features)
