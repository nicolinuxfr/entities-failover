"""Value-style Home Assistant domain contracts."""

from __future__ import annotations

from datetime import date, datetime, time

from homeassistant.components.date import DateEntity
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
    NumberEntity,
    NumberMode,
)
from homeassistant.components.select import SelectEntity
from homeassistant.components.text import MAX_LENGTH_STATE_STATE, TextEntity, TextMode
from homeassistant.components.time import TimeEntity
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.util import dt as dt_util

from ..base import FailoverEntityMixin
from ..routes import (
    SelectOptionRouteMixin,
    SetNativeValueRouteMixin,
    SetValueRouteMixin,
)


class FailoverDateEntity(SetValueRouteMixin, FailoverEntityMixin, DateEntity):
    """Main failover entity for dates."""

    @property
    def native_value(self) -> date | None:
        """Return active source date."""

        value = self._native_state_value()
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None


class FailoverDateTimeEntity(SetValueRouteMixin, FailoverEntityMixin, DateTimeEntity):
    """Main failover entity for datetimes."""

    @property
    def native_value(self) -> datetime | None:
        """Return active source datetime."""

        value = self._native_state_value()
        if value is None:
            return None
        return dt_util.parse_datetime(value)


class FailoverNumberEntity(
    SetNativeValueRouteMixin,
    FailoverEntityMixin,
    NumberEntity,
):
    """Main failover entity for numbers."""

    @property
    def device_class(self) -> str | None:
        """Return active/source device class."""

        return self._active_or_source_attribute(ATTR_DEVICE_CLASS)

    @property
    def mode(self) -> NumberMode:
        """Return active/source number mode."""

        value = self._active_or_source_attribute("mode")
        return NumberMode(value) if value is not None else NumberMode.AUTO

    @property
    def native_max_value(self) -> float:
        """Return active/source maximum value."""

        value = self._float_attribute("max")
        return value if value is not None else DEFAULT_MAX_VALUE

    @property
    def native_min_value(self) -> float:
        """Return active/source minimum value."""

        value = self._float_attribute("min")
        return value if value is not None else DEFAULT_MIN_VALUE

    @property
    def native_step(self) -> float:
        """Return active/source step."""

        value = self._float_attribute("step")
        return value if value is not None else DEFAULT_STEP

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return active/source unit of measurement."""

        return self._active_or_source_attribute(ATTR_UNIT_OF_MEASUREMENT)

    @property
    def native_value(self) -> float | None:
        """Return active source numeric value."""

        return self._native_float_state()


class FailoverSelectEntity(
    SelectOptionRouteMixin,
    FailoverEntityMixin,
    SelectEntity,
):
    """Main failover entity for selects."""

    @property
    def current_option(self) -> str | None:
        """Return active source selected option."""

        return self._active_attribute("current_option") or self._native_state_value()

    @property
    def options(self) -> list[str]:
        """Return active/source options."""

        return list(self._active_or_source_attribute("options") or [])


class FailoverTextEntity(SetValueRouteMixin, FailoverEntityMixin, TextEntity):
    """Main failover entity for text entities."""

    @property
    def mode(self) -> TextMode:
        """Return active/source text mode."""

        value = self._active_or_source_attribute("mode")
        return TextMode(value) if value is not None else TextMode.TEXT

    @property
    def native_max(self) -> int:
        """Return active/source maximum length."""

        value = self._float_attribute("max", float(MAX_LENGTH_STATE_STATE))
        return int(value) if value is not None else MAX_LENGTH_STATE_STATE

    @property
    def native_min(self) -> int:
        """Return active/source minimum length."""

        value = self._float_attribute("min", 0.0)
        return int(value) if value is not None else 0

    @property
    def native_value(self) -> str | None:
        """Return active source text value."""

        return self._native_state_value()

    @property
    def pattern(self) -> str | None:
        """Return active/source pattern."""

        return self._active_or_source_attribute("pattern")


class FailoverTimeEntity(SetValueRouteMixin, FailoverEntityMixin, TimeEntity):
    """Main failover entity for times."""

    @property
    def native_value(self) -> time | None:
        """Return active source time."""

        value = self._native_state_value()
        if value is None:
            return None
        return dt_util.parse_time(value)
