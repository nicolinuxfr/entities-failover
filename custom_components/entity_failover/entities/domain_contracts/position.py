"""Position-based domain contracts."""

from __future__ import annotations

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.components.valve import ValveEntity, ValveEntityFeature

from ..base import FailoverEntityMixin
from ..routes import CoverRouteMixin, ValveRouteMixin


class FailoverCoverEntity(CoverRouteMixin, FailoverEntityMixin, CoverEntity):
    """Main failover entity for cover."""

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        return state_val == "closed"

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""

        return self._native_state_value() == "opening"

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""

        return self._native_state_value() == "closing"

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""

        return self._int_attribute("current_position")

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current position of cover tilt."""

        return self._int_attribute("current_tilt_position")

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Return the list of supported features."""

        return CoverEntityFeature(super().supported_features)


class FailoverValveEntity(ValveRouteMixin, FailoverEntityMixin, ValveEntity):
    """Main failover entity for valve."""

    @property
    def reports_position(self) -> bool:
        """Return whether the active/source valve reports position."""

        value = self._bool_attribute("reports_position")
        if value is not None:
            return value
        return self._active_or_source_attribute("current_position") is not None

    @property
    def is_closed(self) -> bool | None:
        """Return if the valve is closed."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        return state_val == "closed"

    @property
    def is_opening(self) -> bool | None:
        """Return if the valve is opening."""

        return self._native_state_value() == "opening"

    @property
    def is_closing(self) -> bool | None:
        """Return if the valve is closing."""

        return self._native_state_value() == "closing"

    @property
    def current_valve_position(self) -> int | None:
        """Return current position of valve."""

        return self._int_attribute("current_position")

    @property
    def supported_features(self) -> ValveEntityFeature:
        """Return the list of supported features."""

        return ValveEntityFeature(super().supported_features)
