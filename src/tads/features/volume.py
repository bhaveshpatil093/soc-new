"""
Volume features.

These features characterize the raw volume and categorical distribution of
events within a window. They are pure descriptive aggregations and do not
assign anomaly status directly.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)


class EventCountFeature(BaseFeature):  # type: ignore[misc]
    """Total event count in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="event_count",
            group=FeatureGroup.VOLUME,
            source_fields=["_id"],
            mathematical_definition="COUNT(*) of raw events in the window",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 if window has no events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"event_count": float(len(events))}


class EventsPerSecondFeature(BaseFeature):  # type: ignore[misc]
    """Average events per second across the 5-second window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="events_per_second",
            group=FeatureGroup.VOLUME,
            source_fields=["_id"],
            mathematical_definition="event_count / 5.0",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="0.0 if window has no events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"events_per_second": len(events) / 5.0}


class CategoryCountsFeature(BaseFeature):  # type: ignore[misc]
    """Frequencies of event.category values."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="category_counts",
            group=FeatureGroup.VOLUME,
            source_fields=["event_category"],
            mathematical_definition="Frequency map of event_category. Nulls counted as 'unknown'.",
            data_type="dict[str, int]",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, Any]:
        # Returns a dict of sub-features e.g. {"category_count_network": 5}
        events = window_data.get("events", [])
        counts = Counter(e.get("event_category") or "unknown" for e in events)
        return {f"category_count_{k}": float(v) for k, v in counts.items()}


class ActionCountsFeature(BaseFeature):  # type: ignore[misc]
    """Frequencies of event.action values."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="action_counts",
            group=FeatureGroup.VOLUME,
            source_fields=["event_action"],
            mathematical_definition="Frequency map of event_action. Nulls counted as 'unknown'.",
            data_type="dict[str, int]",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, Any]:
        events = window_data.get("events", [])
        counts = Counter(e.get("event_action") or "unknown" for e in events)
        return {f"action_count_{k}": float(v) for k, v in counts.items()}


class OutcomeCountsFeature(BaseFeature):  # type: ignore[misc]
    """Frequencies of event.outcome values."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="outcome_counts",
            group=FeatureGroup.VOLUME,
            source_fields=["event_outcome"],
            mathematical_definition="Frequency map of event_outcome. Nulls counted as 'unknown'.",
            data_type="dict[str, int]",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, Any]:
        events = window_data.get("events", [])
        counts = Counter(e.get("event_outcome") or "unknown" for e in events)
        return {f"outcome_count_{k}": float(v) for k, v in counts.items()}


class AuthenticationVolumeFeature(BaseFeature):  # type: ignore[misc]
    """Total authentication events in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="authentication_volume",
            group=FeatureGroup.VOLUME,
            source_fields=["event_category", "event_type"],
            mathematical_definition="COUNT(*) where event_category == 'authentication'",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 if window has no authentication events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        count = sum(1 for e in events if e.get("event_category") == "authentication")
        return {"authentication_volume": float(count)}


class NetworkVolumeFeature(BaseFeature):  # type: ignore[misc]
    """Total network events in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="network_volume",
            group=FeatureGroup.VOLUME,
            source_fields=["event_category"],
            mathematical_definition="COUNT(*) where event_category == 'network'",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 if window has no network events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        count = sum(1 for e in events if e.get("event_category") == "network")
        return {"network_volume": float(count)}


class ProcessVolumeFeature(BaseFeature):  # type: ignore[misc]
    """Total process events in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_volume",
            group=FeatureGroup.VOLUME,
            source_fields=["event_category"],
            mathematical_definition="COUNT(*) where event_category == 'process'",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 if window has no process events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        count = sum(1 for e in events if e.get("event_category") == "process")
        return {"process_volume": float(count)}


class FileActivityVolumeFeature(BaseFeature):  # type: ignore[misc]
    """Total file activity events in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="file_activity_volume",
            group=FeatureGroup.VOLUME,
            source_fields=["event_category"],
            mathematical_definition="COUNT(*) where event_category == 'file'",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 if window has no file events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        count = sum(1 for e in events if e.get("event_category") == "file")
        return {"file_activity_volume": float(count)}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    EventCountFeature,
    EventsPerSecondFeature,
    CategoryCountsFeature,
    ActionCountsFeature,
    OutcomeCountsFeature,
    AuthenticationVolumeFeature,
    NetworkVolumeFeature,
    ProcessVolumeFeature,
    FileActivityVolumeFeature,
]

for _cls in _FEATURES:
    # Remove existing if present (e.g. from builtin)
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
