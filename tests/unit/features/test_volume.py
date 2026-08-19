"""
Tests for Volume features.
"""
from __future__ import annotations

import tads.features.volume as vol


def test_event_count_feature() -> None:
    feat = vol.EventCountFeature()
    assert feat.compute({}) == {"event_count": 0.0}
    assert feat.compute({"events": []}) == {"event_count": 0.0}
    assert feat.compute({"events": [{}, {}, {}]}) == {"event_count": 3.0}


def test_events_per_second_feature() -> None:
    feat = vol.EventsPerSecondFeature()
    assert feat.compute({}) == {"events_per_second": 0.0}
    assert feat.compute({"events": [{}, {}, {}]}) == {"events_per_second": 0.6}


def test_category_counts_feature() -> None:
    feat = vol.CategoryCountsFeature()
    events = [
        {"event_category": "network"},
        {"event_category": "network"},
        {"event_category": "process"},
        {"other_field": "no category"},  # Null mapped to unknown
    ]
    res = feat.compute({"events": events})
    assert res == {
        "category_count_network": 2.0,
        "category_count_process": 1.0,
        "category_count_unknown": 1.0,
    }


def test_action_counts_feature() -> None:
    feat = vol.ActionCountsFeature()
    events = [
        {"event_action": "logged-in"},
        {"event_action": "logged-out"},
        {"event_action": "logged-in"},
        {},
    ]
    res = feat.compute({"events": events})
    assert res == {
        "action_count_logged-in": 2.0,
        "action_count_logged-out": 1.0,
        "action_count_unknown": 1.0,
    }


def test_outcome_counts_feature() -> None:
    feat = vol.OutcomeCountsFeature()
    events = [
        {"event_outcome": "success"},
        {"event_outcome": "failure"},
        {"event_outcome": "failure"},
        {},
    ]
    res = feat.compute({"events": events})
    assert res == {
        "outcome_count_success": 1.0,
        "outcome_count_failure": 2.0,
        "outcome_count_unknown": 1.0,
    }


def test_authentication_volume_feature() -> None:
    feat = vol.AuthenticationVolumeFeature()
    events = [
        {"event_category": "authentication"},
        {"event_category": "network"},
        {"event_category": "authentication"},
    ]
    assert feat.compute({"events": events}) == {"authentication_volume": 2.0}
    assert feat.compute({"events": []}) == {"authentication_volume": 0.0}


def test_network_volume_feature() -> None:
    feat = vol.NetworkVolumeFeature()
    events = [
        {"event_category": "network"},
        {"event_category": "process"},
        {"event_category": "network"},
        {"event_category": "network"},
    ]
    assert feat.compute({"events": events}) == {"network_volume": 3.0}


def test_process_volume_feature() -> None:
    feat = vol.ProcessVolumeFeature()
    events = [
        {"event_category": "process"},
        {"event_category": "process"},
        {"event_category": "authentication"},
    ]
    assert feat.compute({"events": events}) == {"process_volume": 2.0}


def test_file_activity_volume_feature() -> None:
    feat = vol.FileActivityVolumeFeature()
    events = [
        {"event_category": "file"},
        {"event_category": "file"},
        {"event_category": "network"},
        {"event_category": "file"},
    ]
    assert feat.compute({"events": events}) == {"file_activity_volume": 3.0}
