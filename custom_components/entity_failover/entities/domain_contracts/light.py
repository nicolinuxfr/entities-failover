"""Light domain contract."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)

from .common import ToggleFailoverEntity


class FailoverLightEntity(ToggleFailoverEntity, LightEntity):
    """Main failover entity for lights."""

    @property
    def brightness(self) -> int | None:
        """Return active source brightness."""

        value = self._active_attribute(ATTR_BRIGHTNESS)
        return int(value) if value is not None else None

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return active source color mode."""

        return self._active_attribute(ATTR_COLOR_MODE)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return active source color temperature."""

        value = self._active_attribute(ATTR_COLOR_TEMP_KELVIN)
        return int(value) if value is not None else None

    @property
    def effect(self) -> str | None:
        """Return active source effect."""

        return self._active_attribute(ATTR_EFFECT)

    @property
    def effect_list(self) -> list[str] | None:
        """Return active source effect list."""

        return self._active_attribute(ATTR_EFFECT_LIST)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return active source HS color."""

        return self._tuple_attribute(ATTR_HS_COLOR)

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return active source maximum color temperature."""

        value = self._float_attribute(ATTR_MAX_COLOR_TEMP_KELVIN)
        return int(value) if value is not None else super().max_color_temp_kelvin

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return active source minimum color temperature."""

        value = self._float_attribute(ATTR_MIN_COLOR_TEMP_KELVIN)
        return int(value) if value is not None else super().min_color_temp_kelvin

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return active source RGB color."""

        return self._tuple_attribute(ATTR_RGB_COLOR)

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return active source RGBW color."""

        return self._tuple_attribute(ATTR_RGBW_COLOR)

    @property
    def rgbww_color(self) -> tuple[int, int, int, int, int] | None:
        """Return active source RGBWW color."""

        return self._tuple_attribute(ATTR_RGBWW_COLOR)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return active source supported color modes."""

        value = self._active_or_source_attribute(ATTR_SUPPORTED_COLOR_MODES)
        if value is None:
            return {ColorMode.ONOFF}
        return {ColorMode(mode) for mode in value}

    @property
    def supported_features(self) -> LightEntityFeature:
        """Return active source supported light features."""

        return LightEntityFeature(super().supported_features)

    @property
    def xy_color(self) -> tuple[float, float] | None:
        """Return active source XY color."""

        return self._tuple_attribute(ATTR_XY_COLOR)
