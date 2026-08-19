"""
Built-in example features.

These serve as the validation-gate proof that the framework works end-to-end
(definition -> computation -> causality test).  The full feature groups from
Prompts 27-35 will be added in later modules.
"""
from __future__ import annotations

from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)


class EventCountFeature(BaseFeature):  # type: ignore[misc]
    """Volume: raw event count in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="event_count",
            group=FeatureGroup.VOLUME,
            source_fields=["event_count"],
            mathematical_definition="COUNT(*) of events whose @timestamp falls in [window_start, window_end)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 (empty window)",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        return {"event_count": float(window_data.get("event_count", 0))}


class DistinctUsersFeature(BaseFeature):  # type: ignore[misc]
    """Users: count of distinct user_name values in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="distinct_users",
            group=FeatureGroup.USERS,
            source_fields=["distinct_users"],
            mathematical_definition="COUNT(DISTINCT user_name) within the window",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 (no users observed)",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        return {"distinct_users": float(window_data.get("distinct_users", 0))}


class DistinctIPsFeature(BaseFeature):  # type: ignore[misc]
    """IPs: count of distinct source_ip values in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="distinct_ips",
            group=FeatureGroup.IPS,
            source_fields=["distinct_ips"],
            mathematical_definition="COUNT(DISTINCT source_ip) within the window",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="0 (no IPs observed)",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        return {"distinct_ips": float(window_data.get("distinct_ips", 0))}


class HourOfDayFeature(BaseFeature):  # type: ignore[misc]
    """Temporal: hour of day extracted from the window start."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="hour_of_day",
            group=FeatureGroup.TEMPORAL,
            source_fields=["hour_of_day"],
            mathematical_definition="EXTRACT(HOUR FROM window_start)",
            data_type="int32",
            expected_range=(0, 23),
            missing_value_behavior="Derived from window_start; never missing",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        return {"hour_of_day": float(window_data.get("hour_of_day", 0))}


class IsWeekendFeature(BaseFeature):  # type: ignore[misc]
    """Temporal: whether the window falls on a weekend."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="is_weekend",
            group=FeatureGroup.TEMPORAL,
            source_fields=["is_weekend"],
            mathematical_definition="1.0 if DOW in (0=Sunday, 6=Saturday), else 0.0",
            data_type="float64",
            expected_range=(0, 1),
            missing_value_behavior="Derived from window_start; never missing",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        val = window_data.get("is_weekend", False)
        return {"is_weekend": 1.0 if val else 0.0}


# ------------------------------------------------------------------
# Auto-register built-in features
# ------------------------------------------------------------------
_BUILTIN_FEATURES: list[type[BaseFeature]] = [
    EventCountFeature,
    DistinctUsersFeature,
    DistinctIPsFeature,
    HourOfDayFeature,
    IsWeekendFeature,
]

for _cls in _BUILTIN_FEATURES:
    FEATURE_REGISTRY.register(_cls())
