"""
Tests for multi-scale causal rolling context features.

Covers:
- RollingContextComputer correctness (ring buffer, aggregation math)
- Graceful degradation at dataset start (partial history)
- Causality enforcement (rolling features ignore future context)
- Empty sub-window participation in rolling aggregates
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tads.features.rolling import (
    _ROLLING_FEATURE_CLASSES,
    ROLLING_SCALES,
    RollingContextComputer,
)

if TYPE_CHECKING:
    from tads.features.registry import BaseFeature


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _make_summary(event_count: float = 0.0) -> dict[str, float]:
    """Create a minimal window summary."""
    return {
        "event_count": event_count,
        "distinct_users": 1.0,
        "distinct_ips": 1.0,
        "distinct_hosts": 1.0,
        "distinct_processes": 1.0,
    }


# ------------------------------------------------------------------
# RollingContextComputer tests
# ------------------------------------------------------------------
class TestRollingContextComputer:
    def test_single_window_mean_equals_value(self) -> None:
        """With only 1 window pushed, mean == that window's value."""
        computer = RollingContextComputer()
        summary = _make_summary(event_count=10.0)
        result = computer.push(summary)
        # All scales should have mean = 10.0 (only one data point)
        for label in ROLLING_SCALES:
            assert result[f"rolling_event_count_mean_{label}"] == 10.0
            assert result[f"rolling_event_count_sum_{label}"] == 10.0
            assert result[f"rolling_event_count_std_{label}"] == 0.0

    def test_two_windows_mean(self) -> None:
        """With 2 windows pushed, mean is their average."""
        computer = RollingContextComputer()
        computer.push(_make_summary(event_count=10.0))
        result = computer.push(_make_summary(event_count=20.0))
        for label in ROLLING_SCALES:
            assert result[f"rolling_event_count_mean_{label}"] == 15.0
            assert result[f"rolling_event_count_sum_{label}"] == 30.0

    def test_std_calculation(self) -> None:
        """Verify population std with known values."""
        computer = RollingContextComputer()
        computer.push(_make_summary(event_count=10.0))
        result = computer.push(_make_summary(event_count=20.0))
        # Population std of [10, 20]: mean=15, var=25, std=5
        for label in ROLLING_SCALES:
            assert result[f"rolling_event_count_std_{label}"] == pytest.approx(5.0)

    def test_ring_buffer_eviction(self) -> None:
        """30s scale holds 6 windows; the 7th should evict the first."""
        computer = RollingContextComputer()
        # Push 6 windows of value 10
        for _ in range(6):
            computer.push(_make_summary(event_count=10.0))
        # 7th window with value 100 evicts the first 10
        result = computer.push(_make_summary(event_count=100.0))
        # 30s buffer now contains [10, 10, 10, 10, 10, 100]
        expected_sum = 5 * 10.0 + 100.0
        expected_mean = expected_sum / 6
        assert result["rolling_event_count_sum_30s"] == expected_sum
        assert result["rolling_event_count_mean_30s"] == pytest.approx(expected_mean)

    def test_empty_windows_participate(self) -> None:
        """Empty windows (event_count=0) are real data, not skipped."""
        computer = RollingContextComputer()
        computer.push(_make_summary(event_count=10.0))
        result = computer.push(_make_summary(event_count=0.0))  # empty window
        for label in ROLLING_SCALES:
            # Mean of [10, 0] = 5.0, NOT just [10] = 10.0
            assert result[f"rolling_event_count_mean_{label}"] == 5.0

    def test_output_key_structure(self) -> None:
        """All expected keys are present."""
        computer = RollingContextComputer()
        result = computer.push(_make_summary())
        metrics = ["event_count", "distinct_users", "distinct_ips",
                    "distinct_hosts", "distinct_processes"]
        aggs = ["mean", "sum", "std"]
        for metric in metrics:
            for agg in aggs:
                for label in ROLLING_SCALES:
                    key = f"rolling_{metric}_{agg}_{label}"
                    assert key in result, f"Missing key: {key}"


# ------------------------------------------------------------------
# Graceful degradation at dataset start
# ------------------------------------------------------------------
class TestGracefulDegradation:
    def test_first_window_no_error(self) -> None:
        """The very first window should compute without error."""
        computer = RollingContextComputer()
        result = computer.push(_make_summary(event_count=42.0))
        assert isinstance(result, dict)
        assert result["rolling_event_count_mean_15m"] == 42.0

    def test_partial_history_no_padding(self) -> None:
        """
        With 3 windows pushed, the 30s scale (6 windows) should compute
        from exactly 3 data points, not pad with zeros.
        """
        computer = RollingContextComputer()
        for val in [10.0, 20.0, 30.0]:
            result = computer.push(_make_summary(event_count=val))
        # Mean of [10, 20, 30] = 20.0 (3 real data points, no padding)
        assert result["rolling_event_count_mean_30s"] == 20.0
        assert result["rolling_event_count_sum_30s"] == 60.0

    def test_feature_class_at_start(self) -> None:
        """
        A rolling feature class, when no rolling_context is provided,
        returns 0.0 (not an error).
        """
        feat_cls = _ROLLING_FEATURE_CLASSES[0]
        feat = feat_cls()
        # No rolling_context key at all
        result = feat.compute({"events": []})
        assert next(iter(result.values())) == 0.0


# ------------------------------------------------------------------
# Causality enforcement
# ------------------------------------------------------------------
SAMPLE_ROLLING_FEATURES = [cls() for cls in _ROLLING_FEATURE_CLASSES[:12]]  # First 12

SAMPLE_ROLLING_WINDOW: dict[str, Any] = {
    "events": [{"@timestamp": 1000000}],
    "rolling_context": {
        feat.metadata.name: 42.0
        for feat in SAMPLE_ROLLING_FEATURES
    },
}


class TestRollingCausality:
    @pytest.mark.parametrize(
        "feat",
        SAMPLE_ROLLING_FEATURES,
        ids=[f.metadata.name for f in SAMPLE_ROLLING_FEATURES],
    )
    def test_causal_feature_ignores_future(self, feat: BaseFeature) -> None:
        baseline = feat.compute(SAMPLE_ROLLING_WINDOW)

        window_with_future = dict(SAMPLE_ROLLING_WINDOW)
        window_with_future["_future_window_event_count"] = 9999
        window_with_future["_future_anomaly_score"] = 0.99

        result = feat.compute(window_with_future)
        assert result == baseline, (
            f"Causal feature '{feat.metadata.name}' changed output when "
            f"future context was added: {baseline} -> {result}"
        )

    @pytest.mark.parametrize(
        "feat",
        SAMPLE_ROLLING_FEATURES,
        ids=[f.metadata.name for f in SAMPLE_ROLLING_FEATURES],
    )
    def test_metadata_declares_causal(self, feat: BaseFeature) -> None:
        assert feat.metadata.is_causal is True


# ------------------------------------------------------------------
# Feature count sanity
# ------------------------------------------------------------------
class TestFeatureCount:
    def test_total_rolling_features(self) -> None:
        """5 metrics x 3 aggs x 4 scales = 60 features."""
        assert len(_ROLLING_FEATURE_CLASSES) == 60
