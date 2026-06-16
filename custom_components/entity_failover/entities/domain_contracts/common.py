"""Common Home Assistant entity contracts."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from ..base import FailoverEntityMixin
from ..routes import ToggleRouteMixin
from ..routing import FailoverRouteMixin


class FailoverGenericMainEntity(FailoverRouteMixin, FailoverEntityMixin, Entity):
    """Generic main failover entity."""

    @property
    def state(self) -> str | None:
        """Mirror the active source state."""

        active_state = self.manager.active_state
        return active_state.state if active_state is not None else None


class ToggleFailoverEntity(ToggleRouteMixin, FailoverEntityMixin):
    """Shared behavior for toggle-style domains."""

    @property
    def is_on(self) -> bool | None:
        """Return whether the active source entity is on."""

        active_state = self.manager.active_state
        if active_state is None:
            return None
        return active_state.state == "on"
