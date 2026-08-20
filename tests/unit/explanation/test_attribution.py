"""Tests for defensible event attribution."""
from typing import Any

from tads.explanation.attribution import EventAttributor

# Mock raw events
MOCK_EVENTS: list[dict[str, Any]] = [
    {
        "_id": "event_1",
        "@timestamp": "2025-08-01T00:00:01Z",
        "user": "alice",
        "event_category": "authentication",
        "bytes_sent": 100,
    },
    {
        "_id": "event_2",
        "@timestamp": "2025-08-01T00:00:02Z",
        "user": "eve",  # The anomalous user
        "event_category": "network",
        "bytes_sent": 500,
    },
    {
        "_id": "event_3",
        "@timestamp": "2025-08-01T00:00:03Z",
        "user": "bob",
        "event_category": "authentication",
        "bytes_sent": 200,
    },
]


class TestEventAttributor:
    def test_categorical_exact_match(self) -> None:
        """Verify that a categorical anomaly exactly filters to the responsible event."""
        attributor = EventAttributor()

        # 'eve' is only in event_2
        results = attributor.attribute(MOCK_EVENTS, ["Driven by user='eve' [RARE (Surprisal: 3.00)]"])

        assert len(results) == 1
        assert results[0].event_id == "event_2"
        assert results[0].attribution_method == "Exact Match Filter"
        assert "HIGH" in results[0].attribution_confidence
        assert results[0].relevant_fields == {"user": "eve"}

    def test_subset_volume_match(self) -> None:
        """Verify that subset anomalies filter to the subset of events."""
        attributor = EventAttributor()

        # authentication_volume uses event_category
        results = attributor.attribute(MOCK_EVENTS, ["authentication_volume spiked by 50x"])

        # event_1 and event_3 are authentication
        assert len(results) == 2
        event_ids = {r.event_id for r in results}
        assert event_ids == {"event_1", "event_3"}

        assert results[0].attribution_method == "Subset Filter"
        assert "HIGH" in results[0].attribution_confidence

        # relevant_fields should extract the source fields defined in FeatureMetadata
        assert "event_category" in results[0].relevant_fields
        assert results[0].relevant_fields["event_category"] == "authentication"

    def test_global_distribution_match(self) -> None:
        """Verify that window-level properties attribute to all events without false narrowing."""
        attributor = EventAttributor()

        # event_count is a global feature
        results = attributor.attribute(MOCK_EVENTS, ["event_count"])

        assert len(results) == 3
        event_ids = {r.event_id for r in results}
        assert event_ids == {"event_1", "event_2", "event_3"}

        assert results[0].attribution_method == "Global Distribution"
        assert "MEDIUM" in results[0].attribution_confidence

    def test_multiple_features_combine_correctly(self) -> None:
        """Verify that an event triggering multiple rules gets combined attribution."""
        attributor = EventAttributor()

        # event_2 will match both user=eve (Exact) and f_latency (Global)
        results = attributor.attribute(MOCK_EVENTS, ["Driven by user='eve'", "f_latency"])

        assert len(results) == 3

        event_2 = next(r for r in results if r.event_id == "event_2")
        assert "user='eve'" in event_2.anomalous_features[0]
        assert "f_latency" in event_2.anomalous_features
        assert "MEDIUM" in event_2.attribution_confidence # Downgraded due to global
        assert "Exact Match Filter + Global Distribution" in event_2.attribution_method
        assert "user" in event_2.relevant_fields

        # event_1 will only match global f_latency
        event_1 = next(r for r in results if r.event_id == "event_1")
        assert len(event_1.anomalous_features) == 1
        assert "f_latency" in event_1.anomalous_features
        assert event_1.attribution_method == "Global Distribution"
