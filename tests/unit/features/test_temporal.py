"""
Tests for causal temporal features.

Covers:
- Edge cases (empty windows, missing previous window)
- Hand-verifiable inter-event statistics
- Burstiness (Fano factor) correctness
- Explicit causality enforcement per feature
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

import tads.features.temporal as tf

if TYPE_CHECKING:
    from tads.features.registry import BaseFeature


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
def _make_events(timestamps_ms: list[float]) -> list[dict[str, Any]]:
    """Build a minimal event list from epoch-ms timestamps."""
    return [{"@timestamp": ts} for ts in timestamps_ms]


def _make_window(
    events: list[dict[str, Any]] | None = None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a window_data dict with optional previous-window context."""
    wd: dict[str, Any] = {"events": events or []}
    if previous is not None:
        wd["previous_window"] = previous
    return wd


PREV_SUMMARY = {
    "event_count": 10.0,
    "distinct_users": 3.0,
    "distinct_ips": 5.0,
    "distinct_hosts": 2.0,
    "distinct_processes": 4.0,
    "last_event_ts": 1000000.0,  # epoch ms
}


# ------------------------------------------------------------------
# PreviousWindowEventCount
# ------------------------------------------------------------------
class TestPreviousWindowEventCount:
    def test_no_previous(self) -> None:
        feat = tf.PreviousWindowEventCountFeature()
        assert feat.compute(_make_window()) == {"previous_window_event_count": 0.0}

    def test_with_previous(self) -> None:
        feat = tf.PreviousWindowEventCountFeature()
        result = feat.compute(_make_window(previous=PREV_SUMMARY))
        assert result == {"previous_window_event_count": 10.0}


# ------------------------------------------------------------------
# EventRateChange
# ------------------------------------------------------------------
class TestEventRateChange:
    def test_no_previous_returns_zero(self) -> None:
        events = [{"user_name": "a"}, {"user_name": "b"}]
        feat = tf.EventRateChangeFeature()
        assert feat.compute(_make_window(events)) == {"event_rate_change": 0.0}

    def test_positive_change(self) -> None:
        events = [{"x": i} for i in range(15)]  # 15 events
        feat = tf.EventRateChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        assert result == {"event_rate_change": 5.0}  # 15 - 10

    def test_negative_change(self) -> None:
        events = [{"x": i} for i in range(3)]  # 3 events
        feat = tf.EventRateChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        assert result == {"event_rate_change": -7.0}  # 3 - 10


# ------------------------------------------------------------------
# Entity count changes
# ------------------------------------------------------------------
class TestEntityCountChanges:
    def test_user_count_change_no_previous(self) -> None:
        feat = tf.UserCountChangeFeature()
        assert feat.compute(_make_window()) == {"user_count_change": 0.0}

    def test_user_count_change(self) -> None:
        events = [{"user_name": "u1"}, {"user_name": "u2"}, {"user_name": "u1"}]
        feat = tf.UserCountChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        # 2 distinct users - 3 previous = -1
        assert result == {"user_count_change": -1.0}

    def test_ip_count_change(self) -> None:
        events = [{"source_ip": "1.1.1.1"}, {"source_ip": "2.2.2.2"}]
        feat = tf.IpCountChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        # 2 - 5 = -3
        assert result == {"ip_count_change": -3.0}

    def test_host_count_change(self) -> None:
        events = [
            {"host_name": "h1"},
            {"host_name": "h2"},
            {"host_name": "h3"},
            {"host_name": "h4"},
        ]
        feat = tf.HostCountChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        # 4 - 2 = 2
        assert result == {"host_count_change": 2.0}

    def test_process_count_change(self) -> None:
        events = [{"process_name": "p1"}]
        feat = tf.ProcessCountChangeFeature()
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        # 1 - 4 = -3
        assert result == {"process_count_change": -3.0}


# ------------------------------------------------------------------
# Inter-event statistics
# ------------------------------------------------------------------
class TestInterEventStats:
    def test_mean_empty_window(self) -> None:
        feat = tf.InterEventMeanFeature()
        assert feat.compute(_make_window()) == {"inter_event_mean": 0.0}

    def test_mean_single_event(self) -> None:
        feat = tf.InterEventMeanFeature()
        events = _make_events([1000.0])
        assert feat.compute(_make_window(events)) == {"inter_event_mean": 0.0}

    def test_mean_two_events(self) -> None:
        # 1000ms apart -> 1.0 second
        feat = tf.InterEventMeanFeature()
        events = _make_events([1000.0, 2000.0])
        assert feat.compute(_make_window(events)) == {"inter_event_mean": 1.0}

    def test_mean_three_events_uniform(self) -> None:
        # 0ms, 1000ms, 2000ms -> intervals [1.0, 1.0] -> mean = 1.0
        feat = tf.InterEventMeanFeature()
        events = _make_events([0.0, 1000.0, 2000.0])
        assert feat.compute(_make_window(events)) == {"inter_event_mean": 1.0}

    def test_variance_uniform_spacing(self) -> None:
        # Uniform intervals -> variance = 0
        feat = tf.InterEventVarianceFeature()
        events = _make_events([0.0, 1000.0, 2000.0])
        assert feat.compute(_make_window(events)) == {"inter_event_variance": 0.0}

    def test_variance_non_uniform(self) -> None:
        # Intervals: [1.0, 3.0] -> mean=2.0, var = ((1-2)^2 + (3-2)^2) / 2 = 1.0
        feat = tf.InterEventVarianceFeature()
        events = _make_events([0.0, 1000.0, 4000.0])
        result = feat.compute(_make_window(events))
        assert pytest.approx(result["inter_event_variance"]) == 1.0


# ------------------------------------------------------------------
# Burstiness (Fano factor)
# ------------------------------------------------------------------
class TestBurstiness:
    def test_empty_window(self) -> None:
        feat = tf.BurstinessFeature()
        assert feat.compute(_make_window()) == {"burstiness": 0.0}

    def test_single_event(self) -> None:
        feat = tf.BurstinessFeature()
        events = _make_events([1000.0])
        assert feat.compute(_make_window(events)) == {"burstiness": 0.0}

    def test_uniform_spacing_zero_variance(self) -> None:
        # Intervals all equal -> variance=0 -> Fano=0
        feat = tf.BurstinessFeature()
        events = _make_events([0.0, 1000.0, 2000.0, 3000.0])
        assert feat.compute(_make_window(events)) == {"burstiness": 0.0}

    def test_bursty_arrivals(self) -> None:
        # Intervals: [0.1, 0.1, 4.7] seconds (burst then gap)
        # mean = 5.0/3 ≈ 1.6667
        # var = ((0.1-1.6667)^2 + (0.1-1.6667)^2 + (4.7-1.6667)^2) / 3
        # Fano = var / mean
        feat = tf.BurstinessFeature()
        events = _make_events([0.0, 100.0, 200.0, 4900.0])
        result = feat.compute(_make_window(events))
        assert result["burstiness"] > 1.0, "Bursty arrivals should have Fano > 1"


# ------------------------------------------------------------------
# TimeSincePreviousActivity
# ------------------------------------------------------------------
class TestTimeSincePreviousActivity:
    def test_no_previous_window(self) -> None:
        feat = tf.TimeSincePreviousActivityFeature()
        assert feat.compute(_make_window()) == {"time_since_previous_activity": 5.0}

    def test_no_previous_last_event(self) -> None:
        feat = tf.TimeSincePreviousActivityFeature()
        prev = {"event_count": 0.0}
        assert feat.compute(_make_window(previous=prev)) == {"time_since_previous_activity": 5.0}

    def test_gap_calculation(self) -> None:
        # Previous last event at 1000000ms, first current event at 1002000ms
        # Gap = 2000ms = 2.0 seconds
        feat = tf.TimeSincePreviousActivityFeature()
        events = _make_events([1002000.0, 1003000.0])
        result = feat.compute(_make_window(events, PREV_SUMMARY))
        assert result == {"time_since_previous_activity": 2.0}


# ------------------------------------------------------------------
# Causality enforcement: every temporal feature must ignore future keys
# ------------------------------------------------------------------
TEMPORAL_FEATURES = [
    tf.PreviousWindowEventCountFeature(),
    tf.EventRateChangeFeature(),
    tf.UserCountChangeFeature(),
    tf.IpCountChangeFeature(),
    tf.HostCountChangeFeature(),
    tf.ProcessCountChangeFeature(),
    tf.InterEventMeanFeature(),
    tf.InterEventVarianceFeature(),
    tf.BurstinessFeature(),
    tf.TimeSincePreviousActivityFeature(),
]

SAMPLE_TEMPORAL_WINDOW: dict[str, Any] = {
    "events": [
        {
            "@timestamp": 1000000.0,
            "user_name": "alice",
            "source_ip": "10.0.0.1",
            "host_name": "srv1",
            "process_name": "bash",
        },
        {
            "@timestamp": 1002000.0,
            "user_name": "bob",
            "source_ip": "10.0.0.2",
            "host_name": "srv2",
            "process_name": "sshd",
        },
    ],
    "previous_window": PREV_SUMMARY,
}


class TestTemporalCausality:
    @pytest.mark.parametrize(
        "feat",
        TEMPORAL_FEATURES,
        ids=[f.metadata.name for f in TEMPORAL_FEATURES],
    )
    def test_causal_feature_ignores_future(self, feat: BaseFeature) -> None:
        baseline = feat.compute(SAMPLE_TEMPORAL_WINDOW)

        # Add simulated future context keys that a non-causal feature might read
        window_with_future = dict(SAMPLE_TEMPORAL_WINDOW)
        window_with_future["_future_window_event_count"] = 9999
        window_with_future["_future_anomaly_score"] = 0.99
        window_with_future["_next_window_events"] = [{"@timestamp": 999999999}]

        result = feat.compute(window_with_future)
        assert result == baseline, (
            f"Causal feature '{feat.metadata.name}' changed output when "
            f"future context was added: {baseline} -> {result}"
        )

    @pytest.mark.parametrize(
        "feat",
        TEMPORAL_FEATURES,
        ids=[f.metadata.name for f in TEMPORAL_FEATURES],
    )
    def test_metadata_declares_causal(self, feat: BaseFeature) -> None:
        assert feat.metadata.is_causal is True, (
            f"Feature '{feat.metadata.name}' must be declared causal"
        )
