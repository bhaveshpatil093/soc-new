"""
Modular feature-engineering framework.

Every feature is a small, independently testable class that conforms to the
:class:`BaseFeature` interface.  Features self-describe via
:class:`FeatureMetadata` and are collected in a global
:data:`FEATURE_REGISTRY`.

Key design invariant
--------------------
Features marked ``is_causal=True`` must never reference data beyond the
current window and its past.  This is *enforced*, not just documented: the
test suite feeds truncated data (up to time *t*) and confirms the output is
identical to feeding the full dataset and only reading the value at *t*.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

__all__ = [
    "FEATURE_REGISTRY",
    "BaseFeature",
    "FeatureGroup",
    "FeatureMetadata",
    "FeatureRegistry",
]


# ------------------------------------------------------------------
# Feature groups
# ------------------------------------------------------------------
class FeatureGroup(StrEnum):
    VOLUME = "volume"
    USERS = "users"
    IPS = "ips"
    HOSTS = "hosts"
    PROCESSES = "processes"
    NETWORK = "network"
    EVENTS = "events"
    ENTROPY = "entropy"
    TEMPORAL = "temporal"
    STATISTICAL = "statistical"
    RELATIONSHIP_NOVELTY = "relationship_novelty"


# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------
class FeatureMetadata(BaseModel):
    """Declarative description of a single feature."""

    name: str = Field(..., description="Unique feature name")
    group: FeatureGroup
    source_fields: list[str] = Field(
        ..., description="Canonical schema fields consumed"
    )
    mathematical_definition: str = Field(
        ..., description="Precise mathematical formula or description"
    )
    data_type: str = Field(
        default="float64", description="Arrow / numpy dtype string"
    )
    expected_range: tuple[float | None, float | None] = Field(
        default=(None, None),
        description="(min, max) bounds; None means unbounded on that side",
    )
    missing_value_behavior: str = Field(
        ..., description="What happens when source fields are null"
    )
    requires_baseline: bool = Field(
        default=False,
        description="True if July baseline stats are needed to compute",
    )
    is_causal: bool = Field(
        default=True,
        description=(
            "True means the feature only uses the current window and its "
            "past.  False means it peeks at future data (forbidden at "
            "inference time)."
        ),
    )


# ------------------------------------------------------------------
# Base class
# ------------------------------------------------------------------
class BaseFeature(ABC):
    """Contract that every feature implementation must satisfy."""

    @property
    @abstractmethod
    def metadata(self) -> FeatureMetadata:
        """Return the feature's self-describing metadata."""

    @abstractmethod
    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        """Compute one or more named feature values from a single window.

        Parameters
        ----------
        window_data:
            A dict representing a single 5-second window row.  Keys
            correspond to canonical window-dataset columns (e.g.
            ``event_count``, ``distinct_users``, etc.).

        Returns
        -------
        ``{feature_name: value}`` for each scalar this feature produces.
        """


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------
class FeatureRegistry:
    """Thread-safe, ordered collection of :class:`BaseFeature` instances."""

    def __init__(self) -> None:
        self._features: dict[str, BaseFeature] = {}

    def register(self, feature: BaseFeature) -> None:
        """Add a feature; raises on duplicate names."""
        name = feature.metadata.name
        if name in self._features:
            msg = f"Duplicate feature name: {name}"
            raise ValueError(msg)
        self._features[name] = feature
        logger.debug("Registered feature: %s (%s)", name, feature.metadata.group.value)

    def get(self, name: str) -> BaseFeature:
        return self._features[name]

    def all_features(self) -> list[BaseFeature]:
        return list(self._features.values())

    def by_group(self, group: FeatureGroup) -> list[BaseFeature]:
        return [f for f in self._features.values() if f.metadata.group == group]

    def causal_features(self) -> list[BaseFeature]:
        return [f for f in self._features.values() if f.metadata.is_causal]

    def non_causal_features(self) -> list[BaseFeature]:
        return [f for f in self._features.values() if not f.metadata.is_causal]

    @property
    def names(self) -> list[str]:
        return list(self._features.keys())

    def __len__(self) -> int:
        return len(self._features)

    def compute_all(self, window_data: dict[str, Any]) -> dict[str, float]:
        """Run every registered feature on a window and merge results."""
        result: dict[str, float] = {}
        for feat in self._features.values():
            result.update(feat.compute(window_data))
        return result


# Global singleton — import and use from anywhere
FEATURE_REGISTRY = FeatureRegistry()
