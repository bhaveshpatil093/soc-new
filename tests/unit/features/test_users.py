"""
Tests for user features.
"""
from __future__ import annotations

import tads.features.users as uf


def test_active_users_feature() -> None:
    feat = uf.ActiveUsersFeature()
    assert feat.compute({"events": []}) == {"active_users": 0.0}
    assert feat.compute({"events": [{"user_name": "a"}, {"user_name": "b"}, {"user_name": "a"}]}) == {"active_users": 2.0}
    assert feat.compute({"events": [{"user_name": None}]}) == {"active_users": 1.0}


def test_user_event_concentration_feature() -> None:
    feat = uf.UserEventConcentrationFeature()
    assert feat.compute({"events": []}) == {"user_event_concentration": 0.0}

    # 1 user, all events -> HHI = 1.0
    assert feat.compute({"events": [{"user_name": "a"}, {"user_name": "a"}]}) == {"user_event_concentration": 1.0}

    # 2 users, equal split -> HHI = 0.5^2 + 0.5^2 = 0.5
    assert feat.compute({"events": [{"user_name": "a"}, {"user_name": "b"}]}) == {"user_event_concentration": 0.5}


def test_user_diversity_feature() -> None:
    feat = uf.UserDiversityFeature()
    assert feat.compute({"events": []}) == {"user_diversity": 0.0}

    # 1 user -> entropy = 0.0
    assert feat.compute({"events": [{"user_name": "a"}, {"user_name": "a"}]}) == {"user_diversity": 0.0}

    # 2 users, equal split -> entropy = 1.0
    assert feat.compute({"events": [{"user_name": "a"}, {"user_name": "b"}]}) == {"user_diversity": 1.0}


def test_login_volume_feature() -> None:
    feat = uf.LoginVolumeFeature()
    events = [
        {"event_category": "authentication", "event_action": "logon"},
        {"event_category": "authentication", "event_action": "logon"},
        {"event_category": "network", "event_action": "logon"},
        {"event_category": "authentication", "event_action": "logoff"},
    ]
    assert feat.compute({"events": events}) == {"login_volume": 2.0}


def test_failed_login_ratio_feature() -> None:
    feat = uf.FailedLoginRatioFeature()
    assert feat.compute({"events": []}) == {"failed_login_ratio": 0.0}

    events = [
        {"event_category": "authentication", "event_action": "logon", "event_outcome": "success"},
        {"event_category": "authentication", "event_action": "login", "event_outcome": "failure"},
    ]
    assert feat.compute({"events": events}) == {"failed_login_ratio": 0.5}


def test_user_host_diversity_feature() -> None:
    feat = uf.UserHostDiversityFeature()
    events = [
        {"user_name": "a", "host_name": "h1"},
        {"user_name": "a", "host_name": "h2"},
        {"user_name": "b", "host_name": "h1"},
    ]
    # user a has 2 hosts. user b has 1 host. Average = 1.5
    assert feat.compute({"events": events}) == {"user_host_diversity": 1.5}


def test_user_ip_diversity_feature() -> None:
    feat = uf.UserIpDiversityFeature()
    events = [
        {"user_name": "a", "source_ip": "1.1.1.1"},
        {"user_name": "a", "source_ip": "1.1.1.1"},
        {"user_name": "b", "source_ip": "2.2.2.2"},
        {"user_name": "b", "source_ip": "3.3.3.3"},
    ]
    # a has 1 IP. b has 2 IPs. Average = 1.5
    assert feat.compute({"events": events}) == {"user_ip_diversity": 1.5}


def test_user_process_diversity_feature() -> None:
    feat = uf.UserProcessDiversityFeature()
    events = [
        {"user_name": "a", "process_name": "p1"},
        {"user_name": "b", "process_name": "p2"},
        {"user_name": "c", "process_name": "p3"},
    ]
    # Average = 1.0
    assert feat.compute({"events": events}) == {"user_process_diversity": 1.0}


def test_historical_user_deviation_feature() -> None:
    feat = uf.HistoricalUserDeviationFeature()
    assert feat.compute({"events": []}) == {"historical_user_deviation": 0.0}

    baseline = {"known_users": {"alice", "bob"}}
    events = [
        {"user_name": "alice"}, # known
        {"user_name": "bob"},   # known
        {"user_name": "charlie"}, # unknown
        {"user_name": None}, # null mapped to 'unknown', which is not in known_users
    ]
    # 2 out of 4 events are from novel users -> 0.5
    assert feat.compute({"events": events, "baseline": baseline}) == {"historical_user_deviation": 0.5}
