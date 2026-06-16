"""Route methods for media player services."""

from __future__ import annotations

from typing import Any


class MediaPlayerRouteMixin:
    """Route media player services."""

    async def async_media_play(self) -> None:
        """Route media_play."""

        await self._async_route("media_play")

    async def async_media_pause(self) -> None:
        """Route media_pause."""

        await self._async_route("media_pause")

    async def async_media_stop(self) -> None:
        """Route media_stop."""

        await self._async_route("media_stop")

    async def async_media_next_track(self) -> None:
        """Route media_next_track."""

        await self._async_route("media_next_track")

    async def async_media_previous_track(self) -> None:
        """Route media_previous_track."""

        await self._async_route("media_previous_track")

    async def async_set_volume_level(self, volume: float) -> None:
        """Route volume_set."""

        await self._async_route("volume_set", {"volume_level": volume})

    async def async_mute_volume(self, mute: bool) -> None:
        """Route volume_mute."""

        await self._async_route("volume_mute", {"is_volume_muted": mute})

    async def async_select_source(self, source: str) -> None:
        """Route media player source selection."""

        await self._async_route("select_source", {"source": source})

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Route media player sound mode selection."""

        await self._async_route("select_sound_mode", {"sound_mode": sound_mode})

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Route play_media."""

        data = {
            "media_content_type": media_type,
            "media_content_id": media_id,
            **kwargs,
        }
        await self._async_route("play_media", data)

    async def async_clear_playlist(self) -> None:
        """Route clear_playlist."""

        await self._async_route("clear_playlist")

    async def async_shuffle_set(self, shuffle: bool) -> None:
        """Route shuffle_set."""

        await self._async_route("shuffle_set", {"shuffle": shuffle})

    async def async_repeat_set(self, repeat: str) -> None:
        """Route repeat_set."""

        await self._async_route("repeat_set", {"repeat": repeat})
