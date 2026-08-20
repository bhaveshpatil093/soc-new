"""Tests for temporal anomaly classification."""

from datetime import UTC, datetime

from tads.explanation.episodes import AnomalyEpisode
from tads.explanation.temporal_analysis import TemporalAnalyzer


def test_occur_once() -> None:
    analyzer = TemporalAnalyzer()

    ep1 = AnomalyEpisode(
        episode_id="ep1",
        start_time=datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.95,
        mean_evidence=0.95,
        affected_users={"alice"},
        evidence_trend=[0.95],
    )
    ep2 = AnomalyEpisode(
        episode_id="ep2",
        start_time=datetime(2025, 8, 1, 11, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 11, 0, 5, tzinfo=UTC),
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.96,
        mean_evidence=0.96,
        affected_users={"bob"},
        evidence_trend=[0.96],
    )

    results = analyzer.analyze([ep1, ep2])

    assert len(results["occur once"]) == 2
    assert len(results["repeat"]) == 0
    assert len(results["persist"]) == 0


def test_repeat() -> None:
    analyzer = TemporalAnalyzer()

    ep1 = AnomalyEpisode(
        episode_id="ep1",
        start_time=datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.95,
        mean_evidence=0.95,
        affected_users={"alice"},
        evidence_trend=[0.95],
    )
    ep2 = AnomalyEpisode(
        episode_id="ep2",
        start_time=datetime(2025, 8, 1, 11, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 11, 0, 5, tzinfo=UTC),
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.95,
        mean_evidence=0.95,
        affected_users={"alice"},
        evidence_trend=[0.95],
    )

    results = analyzer.analyze([ep1, ep2])

    assert len(results["occur once"]) == 0
    assert len(results["repeat"]) == 2


def test_persist() -> None:
    analyzer = TemporalAnalyzer(persist_threshold_seconds=60.0)

    ep = AnomalyEpisode(
        episode_id="ep1",
        start_time=datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 10, 1, 10, tzinfo=UTC),  # 70s duration
        duration_seconds=70.0,
        window_count=14,
        peak_evidence=0.99,
        mean_evidence=0.95,
        affected_users={"alice"},
        evidence_trend=[0.95] * 14,
    )

    results = analyzer.analyze([ep])

    assert len(results["persist"]) == 1


def test_escalate_intra_episode() -> None:
    analyzer = TemporalAnalyzer(escalation_correlation_threshold=0.8)

    ep = AnomalyEpisode(
        episode_id="ep1",
        start_time=datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 10, 0, 20, tzinfo=UTC),
        duration_seconds=20.0,
        window_count=5,
        peak_evidence=0.99,
        mean_evidence=0.94,
        affected_users={"alice"},
        evidence_trend=[0.90, 0.92, 0.94, 0.97, 0.99],  # Perfect monotonic increase
    )

    results = analyzer.analyze([ep])

    assert len(results["escalate"]) == 1


def test_escalate_inter_episode() -> None:
    analyzer = TemporalAnalyzer()

    # 3 repeated episodes, strictly increasing peak evidence
    ep1 = AnomalyEpisode(
        "ep1",
        datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
        5,
        1,
        0.91,
        0.91,
        affected_users={"alice"},
    )
    ep2 = AnomalyEpisode(
        "ep2",
        datetime(2025, 8, 1, 11, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 11, 0, 5, tzinfo=UTC),
        5,
        1,
        0.95,
        0.95,
        affected_users={"alice"},
    )
    ep3 = AnomalyEpisode(
        "ep3",
        datetime(2025, 8, 1, 12, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 12, 0, 5, tzinfo=UTC),
        5,
        1,
        0.99,
        0.99,
        affected_users={"alice"},
    )

    results = analyzer.analyze([ep1, ep2, ep3])

    assert len(results["escalate"]) == 3
    assert len(results["repeat"]) == 3


def test_recur_periodically() -> None:
    analyzer = TemporalAnalyzer(periodicity_cv_threshold=0.1)

    # 3 repeated episodes, exactly 1 hour apart (CV = 0)
    ep1 = AnomalyEpisode(
        "ep1",
        datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
        5,
        1,
        0.95,
        0.95,
        affected_users={"alice"},
    )
    ep2 = AnomalyEpisode(
        "ep2",
        datetime(2025, 8, 1, 11, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 11, 0, 5, tzinfo=UTC),
        5,
        1,
        0.95,
        0.95,
        affected_users={"alice"},
    )
    ep3 = AnomalyEpisode(
        "ep3",
        datetime(2025, 8, 1, 12, 0, 0, tzinfo=UTC),
        datetime(2025, 8, 1, 12, 0, 5, tzinfo=UTC),
        5,
        1,
        0.95,
        0.95,
        affected_users={"alice"},
    )

    results = analyzer.analyze([ep1, ep2, ep3])

    assert len(results["recur periodically"]) == 3
    assert len(results["repeat"]) == 3
