"""Media player domain contract."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.util import dt as dt_util

from ..base import FailoverEntityMixin
from ..routes import MediaPlayerRouteMixin


class FailoverMediaPlayerEntity(
    MediaPlayerRouteMixin, FailoverEntityMixin, MediaPlayerEntity
):
    """Main failover entity for media player."""

    @property
    def state(self) -> MediaPlayerState | str | None:
        """State of the player."""

        state_val = self._native_state_value()
        if state_val is None:
            return None
        try:
            return MediaPlayerState(state_val)
        except ValueError:
            return state_val

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0.0 to 1.0)."""

        return self._float_attribute("volume_level")

    @property
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""

        return self._bool_attribute("is_volume_muted")

    @property
    def media_content_id(self) -> str | None:
        """Content ID of current playing media."""

        return self._string_attribute("media_content_id")

    @property
    def media_content_type(self) -> str | None:
        """Content type of current playing media."""

        return self._string_attribute("media_content_type")

    @property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""

        return self._int_attribute("media_duration")

    @property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""

        return self._int_attribute("media_position")

    @property
    def media_position_updated_at(self) -> datetime | None:
        """When was the position of the media last updated."""

        val = self._active_attribute("media_position_updated_at")
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        return dt_util.parse_datetime(str(val))

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""

        return self._string_attribute("media_title")

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media, music track only."""

        return self._string_attribute("media_artist")

    @property
    def media_album_name(self) -> str | None:
        """Album name of current playing media, music track only."""

        return self._string_attribute("media_album_name")

    @property
    def media_album_artist(self) -> str | None:
        """Album artist of current playing media, music track only."""

        return self._string_attribute("media_album_artist")

    @property
    def media_track(self) -> int | None:
        """Track number of current playing media, music track only."""

        return self._int_attribute("media_track")

    @property
    def media_series_title(self) -> str | None:
        """Title of series of current playing media, TV show only."""

        return self._string_attribute("media_series_title")

    @property
    def media_season(self) -> str | None:
        """Season of current playing media, TV show only."""

        return self._string_attribute("media_season")

    @property
    def media_episode(self) -> str | None:
        """Episode of current playing media, TV show only."""

        return self._string_attribute("media_episode")

    @property
    def app_id(self) -> str | None:
        """ID of the current running app."""

        return self._string_attribute("app_id")

    @property
    def app_name(self) -> str | None:
        """Name of the current running app."""

        return self._string_attribute("app_name")

    @property
    def source(self) -> str | None:
        """Name of the current input source."""

        return self._string_attribute("source")

    @property
    def source_list(self) -> list[str] | None:
        """List of available input sources."""

        return self._list_attribute("source_list")

    @property
    def sound_mode(self) -> str | None:
        """Name of the current sound mode."""

        return self._string_attribute("sound_mode")

    @property
    def sound_mode_list(self) -> list[str] | None:
        """List of available sound modes."""

        return self._list_attribute("sound_mode_list")

    @property
    def shuffle(self) -> bool | None:
        """Boolean if shuffle is enabled."""

        return self._bool_attribute("shuffle")

    @property
    def repeat(self) -> str | None:
        """Return current repeat mode."""

        return self._string_attribute("repeat")

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return the list of supported features."""

        return MediaPlayerEntityFeature(super().supported_features)
