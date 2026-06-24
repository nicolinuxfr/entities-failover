"""Persistent command-latency learning state."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, LEARNING_SAMPLE_COUNT

STORAGE_VERSION = 1


@dataclass(slots=True)
class LearningState:
    """Samples collected while learning source priority."""

    sources: tuple[str, ...]
    samples: dict[str, list[float]] = field(default_factory=dict)

    @classmethod
    def empty(cls, sources: tuple[str, ...]) -> LearningState:
        """Create an empty learning state."""

        return cls(sources, {source: [] for source in sources})

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        sources: tuple[str, ...],
    ) -> LearningState:
        """Restore learning state when it matches the configured sources."""

        if data is None or set(data.get("sources", [])) != set(sources):
            return cls.empty(sources)
        stored_samples = data.get("samples", {})
        samples = {
            source: [
                float(value)
                for value in stored_samples.get(source, [])
                if isinstance(value, int | float)
            ][:LEARNING_SAMPLE_COUNT]
            for source in sources
        }
        return cls(sources, samples)

    def as_dict(self) -> dict[str, Any]:
        """Return serializable learning data."""

        return {
            "sources": list(self.sources),
            "samples": self.samples,
        }

    def add_sample(self, source: str, latency: float) -> None:
        """Add one successful sample up to the configured target."""

        samples = self.samples[source]
        if len(samples) < LEARNING_SAMPLE_COUNT:
            samples.append(latency)

    def complete(self, source: str) -> bool:
        """Return whether a source has enough samples."""

        return len(self.samples[source]) >= LEARNING_SAMPLE_COUNT

    def median_latency(self, source: str) -> float | None:
        """Return the source median after learning is complete."""

        if not self.complete(source):
            return None
        return median(self.samples[source])


class LearningStore:
    """Store learning data for one failover subentry."""

    def __init__(self, hass: HomeAssistant, unique_id: str) -> None:
        """Initialize the store."""

        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.learning.{unique_id}",
            private=True,
            atomic_writes=True,
        )

    async def async_load(self, sources: tuple[str, ...]) -> LearningState:
        """Load stored learning data."""

        return LearningState.from_dict(await self._store.async_load(), sources)

    async def async_save(self, state: LearningState) -> None:
        """Persist learning data immediately."""

        await self._store.async_save(state.as_dict())

    async def async_remove(self) -> None:
        """Remove learning data."""

        await self._store.async_remove()
