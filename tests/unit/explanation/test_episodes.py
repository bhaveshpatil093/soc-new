"""Tests for anomaly episode grouping."""

from datetime import UTC, datetime

import pyarrow as pa

from tads.explanation.episodes import EpisodeGrouper


def create_mock_window_data(
    timestamps: list[datetime],
    evidences: list[float],
) -> pa.Table:
    """Create a mock PyArrow table representing pipeline output."""
    n = len(timestamps)
    return pa.table({
        "window_start": timestamps,
        "ensemble_evidence": evidences,
        "detector_agreement": [1] * n,
        "primary_category": ["test_category"] * n,
        "user": [f"user_{i}" for i in range(n)],
    })


class TestEpisodeGrouper:
    def test_groups_consecutive_windows(self) -> None:
        timestamps = [
            datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
            datetime(2025, 8, 1, 10, 0, 10, tzinfo=UTC),
        ]
        # Floor is 0.90, Threshold is 0.95
        evidences = [0.92, 0.99, 0.91]

        data = create_mock_window_data(timestamps, evidences)
        grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)

        episodes = grouper.group(data)

        assert len(episodes) == 1
        ep = episodes[0]
        assert ep.window_count == 3
        assert ep.duration_seconds == 10.0
        assert ep.peak_evidence == 0.99
        assert abs(ep.mean_evidence - (0.92 + 0.99 + 0.91) / 3) < 1e-6
        assert len(ep.affected_users) == 3

    def test_splits_on_gap(self) -> None:
        timestamps = [
            datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),  # ep1
            datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),  # ep1
            datetime(2025, 8, 1, 10, 0, 30, tzinfo=UTC), # gap of 25s > 15s
            datetime(2025, 8, 1, 10, 0, 35, tzinfo=UTC), # ep2
        ]
        evidences = [0.96, 0.96, 0.96, 0.96]

        data = create_mock_window_data(timestamps, evidences)
        grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)

        episodes = grouper.group(data)

        assert len(episodes) == 2
        assert episodes[0].window_count == 2
        assert episodes[1].window_count == 2

    def test_bridges_small_gap(self) -> None:
        timestamps = [
            datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),  # 0.96
            datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),  # 0.50 (ignored)
            datetime(2025, 8, 1, 10, 0, 10, tzinfo=UTC), # 0.50 (ignored)
            datetime(2025, 8, 1, 10, 0, 15, tzinfo=UTC), # 0.96
        ]
        # The gap between the two 0.96 windows is 15 seconds.
        # max_gap_seconds = 15.0, so this should merge.
        evidences = [0.96, 0.50, 0.50, 0.96]

        data = create_mock_window_data(timestamps, evidences)
        grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)

        episodes = grouper.group(data)

        assert len(episodes) == 1
        assert episodes[0].window_count == 2
        assert episodes[0].duration_seconds == 15.0

    def test_drops_sub_threshold_episodes(self) -> None:
        """An episode where peak evidence is below 0.95 should not be emitted."""
        timestamps = [
            datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2025, 8, 1, 10, 0, 5, tzinfo=UTC),
        ]
        # Floor is 0.90, but peak is 0.94 (below 0.95 alert threshold)
        evidences = [0.91, 0.94]

        data = create_mock_window_data(timestamps, evidences)
        grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)

        episodes = grouper.group(data)

        assert len(episodes) == 0
