"""
Validation gate: Shared novelty mechanisms.

Confirms that unseen-entity handling is behaviorally identical across
User, IP, and Host features by verifying they all rely on the shared
utilities and produce identical behavioral shapes given analogous inputs.
"""
from __future__ import annotations

import pytest

from tads.features.hosts import HistoricalHostDeviationFeature, RelationshipNoveltyHostUserFeature
from tads.features.ips import HistoricalIpFrequencyFeature, RelationshipNoveltyFeature
from tads.features.users import HistoricalUserDeviationFeature
from tads.features.utils import calculate_historical_deviation, calculate_relationship_novelty


def test_shared_historical_deviation_utility() -> None:
    """Test the shared utility handles missing/novel entities correctly."""
    events = [
        {"entity": "known1"},
        {"entity": "known2"},
        {"entity": "novel1"},
        {"entity": None},  # Missing mapped to "unknown", which is novel
    ]
    baseline = {"known_entities": {"known1", "known2"}}

    ratio = calculate_historical_deviation(events, "entity", baseline, "known_entities")
    # 2 novel (novel1, None) out of 4 -> 0.5
    assert ratio == 0.5


def test_shared_relationship_novelty_utility() -> None:
    """Test the shared utility handles missing/novel pairs correctly."""
    events = [
        {"e1": "k1", "e2": "k2"}, # Known pair
        {"e1": "k1", "e2": "n1"}, # Novel pair
        {"e1": None, "e2": "k2"}, # Novel pair ("unknown", "k2")
    ]
    baseline = {"known_pairs": {("k1", "k2")}}

    ratio = calculate_relationship_novelty(events, "e1", "e2", baseline, "known_pairs")
    # 2 novel out of 3 -> ~0.666
    assert pytest.approx(ratio) == 2 / 3


@pytest.mark.parametrize(
    ("feature_class", "entity_field", "baseline_key"),
    [
        (HistoricalUserDeviationFeature, "user_name", "known_users"),
        (HistoricalIpFrequencyFeature, "source_ip", "known_source_ips"),
        (HistoricalHostDeviationFeature, "host_name", "known_hosts"),
    ],
)
def test_historical_features_behavioral_equivalence(
    feature_class: type, entity_field: str, baseline_key: str
) -> None:
    """
    Ensure all historical frequency features behave identically for analogous inputs,
    proving they use the shared framework correctly.
    """
    feat = feature_class()

    # Empty window
    assert next(iter(feat.compute({"events": []}).values())) == 0.0

    # 50% novel window
    events = [
        {entity_field: "known1"},
        {entity_field: "known2"},
        {entity_field: "novel1"},
        {entity_field: None},
    ]
    baseline = {baseline_key: {"known1", "known2"}}

    result = feat.compute({"events": events, "baseline": baseline})
    val = next(iter(result.values()))

    assert val == 0.5, f"{feature_class.__name__} failed behavioral equivalence"


@pytest.mark.parametrize(
    ("feature_class", "f1", "f2", "baseline_key"),
    [
        (RelationshipNoveltyFeature, "source_ip", "user_name", "known_ip_user_pairs"),
        (RelationshipNoveltyHostUserFeature, "host_name", "user_name", "known_host_user_pairs"),
    ],
)
def test_relationship_features_behavioral_equivalence(
    feature_class: type, f1: str, f2: str, baseline_key: str
) -> None:
    """
    Ensure all relationship novelty features behave identically for analogous inputs.
    """
    feat = feature_class()

    # Empty window
    assert next(iter(feat.compute({"events": []}).values())) == 0.0

    events = [
        {f1: "k1", f2: "k2"}, # Known pair
        {f1: "k1", f2: "n1"}, # Novel pair
        {f1: None, f2: "k2"}, # Novel pair ("unknown", "k2")
    ]
    baseline = {baseline_key: {("k1", "k2")}}

    result = feat.compute({"events": events, "baseline": baseline})
    val = next(iter(result.values()))

    assert pytest.approx(val) == 2 / 3, f"{feature_class.__name__} failed behavioral equivalence"
