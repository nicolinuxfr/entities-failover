"""Specialized domain contracts."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.image import ImageEntity
from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.components.scene import Scene
from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.components.vacuum import StateVacuumEntity, VacuumEntityFeature
from homeassistant.util import dt as dt_util

from ..base import FailoverEntityMixin
from ..routes import (
    LawnMowerRouteMixin,
    SceneRouteMixin,
    UpdateRouteMixin,
    VacuumRouteMixin,
)


class FailoverUpdateEntity(UpdateRouteMixin, FailoverEntityMixin, UpdateEntity):
    """Main failover entity for update."""

    @property
    def installed_version(self) -> str | None:
        """Version currently installed."""

        return self._string_attribute("installed_version")

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""

        return self._string_attribute("latest_version")

    @property
    def release_summary(self) -> str | None:
        """Summary of the release."""

        return self._string_attribute("release_summary")

    @property
    def release_url(self) -> str | None:
        """URL to the release notes."""

        return self._string_attribute("release_url")

    @property
    def title(self) -> str | None:
        """Title of the update."""

        return self._string_attribute("title")

    @property
    def in_progress(self) -> bool | int | None:
        """Whether the update is currently in progress."""

        val = self._bool_attribute("in_progress")
        if val is None:
            return self._int_attribute("in_progress")
        return val

    @property
    def update_percent(self) -> int | None:
        """Return the percentage of progress."""

        return self._int_attribute("update_percent")

    @property
    def supported_features(self) -> UpdateEntityFeature:
        """Return the list of supported features."""

        return UpdateEntityFeature(super().supported_features)


class FailoverVacuumEntity(VacuumRouteMixin, FailoverEntityMixin, StateVacuumEntity):
    """Main failover entity for vacuum."""

    @property
    def state(self) -> str | None:
        """State of the vacuum."""

        return self._native_state_value()

    @property
    def battery_level(self) -> int | None:
        """Battery level of the vacuum cleaner."""

        return self._int_attribute("battery_level")

    @property
    def fan_speed(self) -> str | None:
        """Fan speed of the vacuum cleaner."""

        return self._string_attribute("fan_speed")

    @property
    def fan_speed_list(self) -> list[str] | None:
        """List of available fan speeds."""

        return self._list_attribute("fan_speed_list")

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Return the list of supported features."""

        return VacuumEntityFeature(super().supported_features)


class FailoverLawnMowerEntity(
    LawnMowerRouteMixin, FailoverEntityMixin, LawnMowerEntity
):
    """Main failover entity for lawn mower."""

    @property
    def activity(self) -> LawnMowerActivity | str | None:
        """Return the current activity."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        try:
            return LawnMowerActivity(state_val)
        except ValueError:
            return state_val

    @property
    def supported_features(self) -> LawnMowerEntityFeature:
        """Return the list of supported features."""

        return LawnMowerEntityFeature(super().supported_features)


class FailoverCalendarEntity(FailoverEntityMixin, CalendarEntity):
    """Main failover entity for calendar."""

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("calendar")
        if component:
            entity = component.get_entity(active_source)
            if entity and hasattr(entity, "event"):
                return entity.event
        return None

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return calendar events."""

        active_source = self.manager.active_source
        if not active_source:
            return []
        component = self.hass.data.get("entity_components", {}).get("calendar")
        if component:
            entity = component.get_entity(active_source)
            if entity:
                return await entity.async_get_events(hass, start_date, end_date)
        return []


class FailoverImageEntity(FailoverEntityMixin, ImageEntity):
    """Main failover entity for image."""

    def __init__(self, manager, suffix=None):
        """Initialize image."""

        FailoverEntityMixin.__init__(self, manager, suffix=suffix)
        ImageEntity.__init__(self, manager.hass)

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the image was last updated."""

        val = self._active_attribute("image_last_updated")
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        return dt_util.parse_datetime(str(val))

    async def async_image(self) -> bytes | None:
        """Return image bytes."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("image")
        if component:
            entity = component.get_entity(active_source)
            if entity:
                return await entity.async_image()
        return None


class FailoverTodoListEntity(FailoverEntityMixin, TodoListEntity):
    """Main failover entity for todo list."""

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return todo items."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("todo")
        if component:
            entity = component.get_entity(active_source)
            if entity:
                return entity.todo_items
        return None


class FailoverSceneEntity(SceneRouteMixin, FailoverEntityMixin, Scene):
    """Main failover entity for scene."""
