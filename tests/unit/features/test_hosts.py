"""
Tests for Host behavioral features.
"""
from __future__ import annotations

import pytest

import tads.features.hosts as hf


def test_active_hosts_feature() -> None:
    feat = hf.ActiveHostsFeature()
    assert feat.compute({"events": []}) == {"active_hosts": 0.0}
    assert feat.compute({"events": [{"host_name": "h1"}, {"host_name": "h2"}, {"host_name": "h1"}]}) == {"active_hosts": 2.0}


def test_host_event_concentration_feature() -> None:
    feat = hf.HostEventConcentrationFeature()
    assert feat.compute({"events": []}) == {"host_event_concentration": 0.0}

    assert feat.compute({"events": [{"host_name": "h1"}, {"host_name": "h1"}]}) == {
        "host_event_concentration": 1.0
    }

    assert feat.compute({"events": [{"host_name": "h1"}, {"host_name": "h2"}]}) == {
        "host_event_concentration": 0.5
    }


def test_host_user_diversity_feature() -> None:
    feat = hf.HostUserDiversityFeature()
    events = [
        {"host_name": "h1", "user_name": "a"},
        {"host_name": "h1", "user_name": "b"},
        {"host_name": "h2", "user_name": "a"},
    ]
    # h1 has 2 users. h2 has 1 user. Average = 1.5
    assert feat.compute({"events": events}) == {"host_user_diversity": 1.5}


def test_host_ip_diversity_feature() -> None:
    feat = hf.HostIpDiversityFeature()
    events = [
        {"host_name": "h1", "source_ip": "1.1.1.1"},
        {"host_name": "h1", "source_ip": "2.2.2.2"},
        {"host_name": "h2", "source_ip": "1.1.1.1"},
    ]
    # Average = 1.5
    assert feat.compute({"events": events}) == {"host_ip_diversity": 1.5}


def test_host_process_diversity_feature() -> None:
    feat = hf.HostProcessDiversityFeature()
    events = [
        {"host_name": "h1", "process_name": "p1"},
        {"host_name": "h2", "process_name": "p2"},
        {"host_name": "h3", "process_name": "p3"},
    ]
    # Average = 1.0
    assert feat.compute({"events": events}) == {"host_process_diversity": 1.0}


def test_host_category_diversity_feature() -> None:
    feat = hf.HostCategoryDiversityFeature()
    events = [
        {"host_name": "h1", "event_category": "network"},
        {"host_name": "h1", "event_category": "process"},
        {"host_name": "h2", "event_category": "network"},
    ]
    # Average = 1.5
    assert feat.compute({"events": events}) == {"host_category_diversity": 1.5}


def test_historical_host_deviation_feature() -> None:
    feat = hf.HistoricalHostDeviationFeature()
    assert feat.compute({"events": []}) == {"historical_host_deviation": 0.0}

    baseline = {"known_hosts": {"h1", "h2"}}
    events = [
        {"host_name": "h1"}, # known
        {"host_name": "h3"}, # novel
    ]
    # 1 novel out of 2 events -> 0.5
    assert feat.compute({"events": events, "baseline": baseline}) == {"historical_host_deviation": 0.5}


def test_relationship_novelty_host_user_feature() -> None:
    feat = hf.RelationshipNoveltyHostUserFeature()
    assert feat.compute({"events": []}) == {"relationship_novelty_host_user": 0.0}

    baseline = {"known_host_user_pairs": {("h1", "alice")}}
    events = [
        {"host_name": "h1", "user_name": "alice"}, # known pair
        {"host_name": "h1", "user_name": "bob"},   # novel pair
    ]
    # 1 novel out of 2 events -> 0.5
    assert pytest.approx(feat.compute({"events": events, "baseline": baseline})["relationship_novelty_host_user"]) == 0.5
