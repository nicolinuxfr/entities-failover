"""Camera domain contract."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature

from ..base import FailoverEntityMixin


class FailoverCameraEntity(FailoverEntityMixin, Camera):
    """Main failover entity for camera."""

    def __init__(self, manager, suffix=None):
        """Initialize camera."""

        FailoverEntityMixin.__init__(self, manager, suffix=suffix)
        Camera.__init__(self)

    @property
    def is_recording(self) -> bool | None:
        """Return true if the camera is recording."""

        return self._bool_attribute("is_recording")

    @property
    def is_streaming(self) -> bool | None:
        """Return true if the camera is streaming."""

        return self._bool_attribute("is_streaming")

    @property
    def is_on(self) -> bool:
        """Return true if the camera is on."""

        return self._native_state_value() != "off"

    @property
    def motion_detection_enabled(self) -> bool | None:
        """Return true if motion detection is enabled."""

        return self._bool_attribute("motion_detection_enabled")

    @property
    def brand(self) -> str | None:
        """Return camera brand."""

        return self._string_attribute("brand")

    @property
    def model(self) -> str | None:
        """Return camera model."""

        return self._string_attribute("model")

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return camera image."""

        active_source = self.manager.active_source
        if not active_source:
            return None
        component = self.hass.data.get("entity_components", {}).get("camera")
        if component:
            entity = component.get_entity(active_source)
            if entity:
                return await entity.async_camera_image(width, height)
        return None

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return the list of supported features."""

        return CameraEntityFeature(super().supported_features)
