"""
Tests for the modular feature-engineering framework.

Covers:
- Registry mechanics (register, dedup guard, lookup, grouping)
- Metadata completeness (every field populated)
- Compute interface (correct output shape)
- Causality enforcement (truncated-data test for all causal features)
"""
from __future__ import annotations

from typing import Any

import pytest

# Importing builtin triggers auto-registration into FEATURE_REGISTRY
from tads.features import builtin as _  # noqa: F401
from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureRegistry,
)

# ------------------------------------------------------------------
# Sample window data
# ------------------------------------------------------------------
SAMPLE_WINDOW: dict[str, Any] = {
    "window_id": 357117120,
    "event_count": 42,
    "distinct_users": 5,
    "distinct_ips": 12,
    "distinct_hosts": 3,
    "distinct_processes": 7,
    "hour_of_day": 14,
    "minute_of_hour": 30,
    "day_of_week": 2,  # Wednesday
    "is_weekend": False,
    "day_of_month": 15,
    "window_position_in_hour": 360,
}

EMPTY_WINDOW: dict[str, Any] = {
    "window_id": 357117121,
    "event_count": 0,
    "distinct_users": 0,
    "distinct_ips": 0,
    "distinct_hosts": 0,
    "distinct_processes": 0,
    "hour_of_day": 3,
    "minute_of_hour": 0,
    "day_of_week": 0,  # Sunday
    "is_weekend": True,
    "day_of_month": 2,
    "window_position_in_hour": 0,
}


# ------------------------------------------------------------------
# Registry tests
# ------------------------------------------------------------------
class TestFeatureRegistry:
    def test_builtin_features_registered(self) -> None:
        assert len(FEATURE_REGISTRY) >= 5

    def test_all_names_unique(self) -> None:
        names = FEATURE_REGISTRY.names
        assert len(names) == len(set(names))

    def test_duplicate_raises(self) -> None:
        reg = FeatureRegistry()
        feat = FEATURE_REGISTRY.get("event_count")
        reg.register(feat)
        with pytest.raises(ValueError, match="Duplicate"):
            reg.register(feat)

    def test_get_by_name(self) -> None:
        feat = FEATURE_REGISTRY.get("event_count")
        assert feat.metadata.name == "event_count"

    def test_by_group_volume(self) -> None:
        volume = FEATURE_REGISTRY.by_group(FeatureGroup.VOLUME)
        assert any(f.metadata.name == "event_count" for f in volume)

    def test_by_group_temporal(self) -> None:
        temporal = FEATURE_REGISTRY.by_group(FeatureGroup.TEMPORAL)
        names = {f.metadata.name for f in temporal}
        assert "hour_of_day" in names
        assert "is_weekend" in names

    def test_causal_features_non_empty(self) -> None:
        assert len(FEATURE_REGISTRY.causal_features()) > 0


# ------------------------------------------------------------------
# Metadata completeness tests
# ------------------------------------------------------------------
class TestFeatureMetadata:
    @pytest.mark.parametrize("feat", FEATURE_REGISTRY.all_features(),
                             ids=[f.metadata.name for f in FEATURE_REGISTRY.all_features()])
    def test_metadata_fields_populated(self, feat: BaseFeature) -> None:
        m = feat.metadata
        assert m.name
        assert isinstance(m.group, FeatureGroup)
        assert len(m.source_fields) > 0
        assert m.mathematical_definition
        assert m.data_type
        assert m.missing_value_behavior

    @pytest.mark.parametrize("feat", FEATURE_REGISTRY.all_features(),
                             ids=[f.metadata.name for f in FEATURE_REGISTRY.all_features()])
    def test_expected_range_is_tuple(self, feat: BaseFeature) -> None:
        lo, hi = feat.metadata.expected_range
        if lo is not None and hi is not None:
            assert lo <= hi


# ------------------------------------------------------------------
# Compute interface tests
# ------------------------------------------------------------------
class TestFeatureCompute:
    @pytest.mark.parametrize("feat", FEATURE_REGISTRY.all_features(),
                             ids=[f.metadata.name for f in FEATURE_REGISTRY.all_features()])
    def test_compute_returns_dict_of_floats(self, feat: BaseFeature) -> None:
        result = feat.compute(SAMPLE_WINDOW)
        assert isinstance(result, dict)
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, float | int), f"{k}: {v} is {type(v)}"

    def test_event_count_value(self) -> None:
        result = FEATURE_REGISTRY.get("event_count").compute(SAMPLE_WINDOW)
        assert result["event_count"] == 42.0

    def test_event_count_empty_window(self) -> None:
        result = FEATURE_REGISTRY.get("event_count").compute(EMPTY_WINDOW)
        assert result["event_count"] == 0.0

    def test_is_weekend_weekday(self) -> None:
        result = FEATURE_REGISTRY.get("is_weekend").compute(SAMPLE_WINDOW)
        assert result["is_weekend"] == 0.0

    def test_is_weekend_weekend(self) -> None:
        result = FEATURE_REGISTRY.get("is_weekend").compute(EMPTY_WINDOW)
        assert result["is_weekend"] == 1.0

    def test_compute_all(self) -> None:
        result = FEATURE_REGISTRY.compute_all(SAMPLE_WINDOW)
        assert "event_count" in result
        assert "distinct_users" in result
        assert "hour_of_day" in result


# ------------------------------------------------------------------
# Causality enforcement
# ------------------------------------------------------------------
class TestCausalityEnforcement:
    """
    For every feature marked is_causal=True, verify that its output depends
    only on the current window's data and not on future information.

    Method: compute the feature on the full window data, then compute it
    again on a "truncated" copy that has the same current-window values but
    different future-context keys (simulated by adding a bogus future key).
    A truly causal feature must produce identical output in both cases
    because it never reads beyond the current window.
    """

    @pytest.mark.parametrize(
        "feat",
        FEATURE_REGISTRY.causal_features(),
        ids=[f.metadata.name for f in FEATURE_REGISTRY.causal_features()],
    )
    def test_causal_feature_ignores_future(self, feat: BaseFeature) -> None:
        # Baseline: compute on the current window
        baseline = feat.compute(SAMPLE_WINDOW)

        # Truncated: same window data, but with a "future_context" key
        # that a non-causal feature might peek at
        truncated = dict(SAMPLE_WINDOW)
        truncated["_future_window_event_count"] = 9999
        truncated["_future_anomaly_score"] = 0.99

        result = feat.compute(truncated)
        assert result == baseline, (
            f"Causal feature '{feat.metadata.name}' changed output when "
            f"future context was added: {baseline} -> {result}"
        )
