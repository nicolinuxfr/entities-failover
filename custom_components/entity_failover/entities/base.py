"""Shared failover entity helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, State, callback
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import ATTR_FORWARDED_ENTITY_ID, DOMAIN, NAME
from ..manager import FailoverManager

UNAVAILABLE_STATES = {STATE_UNAVAILABLE, STATE_UNKNOWN}


class FailoverEntityMixin:
    """Base behavior for all failover entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, manager: FailoverManager, *, suffix: str | None = None) -> None:
        """Initialize a failover entity."""

        self.manager = manager
        self._suffix = suffix
        self._attr_unique_id = (
            f"{manager.config.unique_id}_{suffix}"
            if suffix
            else manager.config.unique_id
        )
        self._attr_name = suffix.replace("_", " ").title() if suffix else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.config.unique_id)},
            name=manager.config.name,
            manufacturer=NAME,
            entry_type="service",
        )

    async def async_added_to_hass(self) -> None:
        """Register update listener."""

        if self._suffix is None:
            self.manager.main_entity_id = self.entity_id
        self.async_on_remove(
            self.manager.async_add_update_listener(self._handle_manager_update)
        )

    @callback
    def _handle_manager_update(self) -> None:
        """Write HA state after manager changes."""

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return self.manager.available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return safe diagnostic and standard passthrough attributes."""

        attrs = dict(self.manager.state_attributes)
        active_state = self.manager.active_state
        if active_state is None:
            return attrs
        attrs[ATTR_FORWARDED_ENTITY_ID] = active_state.entity_id
        native_attrs = self._native_platform_attribute_keys()
        for key in self.manager.adapter.passthrough_attributes:
            if key not in native_attrs and key in active_state.attributes:
                attrs[key] = active_state.attributes[key]

        # Prevent collisions with keys produced by state_attributes
        # or capability_attributes
        excluded_keys = set()
        if hasattr(self, "state_attributes") and self.state_attributes:
            excluded_keys.update(self.state_attributes)
        if hasattr(self, "capability_attributes") and self.capability_attributes:
            excluded_keys.update(self.capability_attributes)

        for key in list(attrs):
            if key in excluded_keys:
                attrs.pop(key)

        return attrs

    def _native_platform_attribute_keys(self) -> set[str]:
        """Return attributes already managed by the Home Assistant entity class."""

        keys: set[str] = set()
        capability_attributes = self.capability_attributes
        if capability_attributes:
            keys.update(capability_attributes)
        state_attributes = self.state_attributes
        if state_attributes:
            keys.update(state_attributes)
        return keys

    @property
    def supported_features(self) -> int:
        """Return supported features according to the selected policy."""

        if self.manager.config.feature_policy == "active_source":
            return self.manager.adapter.supported_features(self.manager.active_state)
        states = [
            self.manager.hass.states.get(source)
            for source in self.manager.config.sources
        ]
        if not states:
            return 0
        result = self.manager.adapter.supported_features(states[0])
        for state in states[1:]:
            result &= self.manager.adapter.supported_features(state)
        return result

    async def _async_route(
        self,
        service: str,
        data: Mapping[str, Any] | None = None,
        *,
        context: Context | None = None,
        required_features: int = 0,
    ) -> None:
        """Route a service call through the manager."""

        payload = dict(data or {})
        payload.pop(ATTR_ENTITY_ID, None)
        await self.manager.async_call_service(
            service,
            payload,
            context=context,
            required_features=required_features,
        )

    def _active_attribute(self, attribute: str) -> Any:
        """Return an attribute from the active source state."""

        active_state = self.manager.active_state
        if active_state is None:
            return None
        return active_state.attributes.get(attribute)

    def _source_attribute(self, attribute: str) -> Any:
        """Return an attribute from the first source that exposes it."""

        for source in self.manager.config.sources:
            state = self.manager.hass.states.get(source)
            if state is not None and attribute in state.attributes:
                return state.attributes[attribute]
        return None

    def _active_or_source_attribute(self, attribute: str) -> Any:
        """Return active source attribute, falling back to any source."""

        value = self._active_attribute(attribute)
        if value is not None:
            return value
        return self._source_attribute(attribute)

    def _tuple_attribute(self, attribute: str) -> Any:
        """Return an active source sequence attribute as a tuple."""

        value = self._active_attribute(attribute)
        if value is None or isinstance(value, tuple):
            return value
        return tuple(value)

    def _native_state_value(self) -> str | None:
        """Return the active source state as a native value string."""

        active_state = self.manager.active_state
        if active_state is None or active_state.state in UNAVAILABLE_STATES:
            return None
        return active_state.state

    def _native_float_state(self) -> float | None:
        """Return the active source state as a float when possible."""

        value = self._native_state_value()
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _float_attribute(
        self,
        attribute: str,
        default: float | None = None,
    ) -> float | None:
        """Return a numeric active/source attribute."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _native_int_state(self) -> int | None:
        """Return the active source state as an int when possible."""

        value = self._native_state_value()
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _native_bool_state(self) -> bool | None:
        """Return the active source state as a bool when possible."""

        value = self._native_state_value()
        if value is None:
            return None
        if value.lower() in ("true", "on", "yes", "1"):
            return True
        if value.lower() in ("false", "off", "no", "0"):
            return False
        return None

    def _int_attribute(self, attribute: str, default: int | None = None) -> int | None:
        """Return a numeric integer active/source attribute."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _bool_attribute(
        self, attribute: str, default: bool | None = None
    ) -> bool | None:
        """Return a boolean active/source attribute."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("true", "on", "yes", "1"):
            return True
        if str(value).lower() in ("false", "off", "no", "0"):
            return False
        return default

    def _string_attribute(
        self, attribute: str, default: str | None = None
    ) -> str | None:
        """Return a string active/source attribute."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return default
        return str(value)

    def _list_attribute(self, attribute: str) -> list[Any] | None:
        """Return an active/source attribute as a list."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return list(value)

    def _enum_attribute(
        self, attribute: str, enum_cls: Any, default: Any = None
    ) -> Any:
        """Return an active/source attribute converted to a specific Enum."""

        value = self._active_or_source_attribute(attribute)
        if value is None:
            return default
        try:
            return enum_cls(value)
        except ValueError:
            return default

    def _active_state(self) -> State | None:
        """Return the active source state."""

        return self.manager.active_state
