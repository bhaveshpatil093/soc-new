"""
Tests for IP features.
"""
from __future__ import annotations

import pytest

import tads.features.ips as ipf


def test_unique_source_ips_feature() -> None:
    feat = ipf.UniqueSourceIPsFeature()
    assert feat.compute({"events": []}) == {"unique_source_ips": 0.0}
    events = [{"source_ip": "1.1.1.1"}, {"source_ip": "2.2.2.2"}, {"source_ip": "1.1.1.1"}]
    assert feat.compute({"events": events}) == {"unique_source_ips": 2.0}


def test_unique_destination_ips_feature() -> None:
    feat = ipf.UniqueDestinationIPsFeature()
    assert feat.compute({"events": []}) == {"unique_destination_ips": 0.0}
    events = [{"destination_ip": "1.1.1.1"}, {"destination_ip": "2.2.2.2"}, {"destination_ip": "1.1.1.1"}]
    assert feat.compute({"events": events}) == {"unique_destination_ips": 2.0}


def test_source_ip_concentration_feature() -> None:
    feat = ipf.SourceIpConcentrationFeature()
    assert feat.compute({"events": []}) == {"source_ip_concentration": 0.0}

    # 1 IP, all events -> HHI = 1.0
    assert feat.compute({"events": [{"source_ip": "1.1.1.1"}, {"source_ip": "1.1.1.1"}]}) == {
        "source_ip_concentration": 1.0
    }

    # 2 IPs, equal split -> HHI = 0.5
    assert feat.compute({"events": [{"source_ip": "1.1.1.1"}, {"source_ip": "2.2.2.2"}]}) == {
        "source_ip_concentration": 0.5
    }


def test_destination_diversity_feature() -> None:
    feat = ipf.DestinationDiversityFeature()
    assert feat.compute({"events": []}) == {"destination_diversity": 0.0}

    # 1 IP -> entropy = 0.0
    assert feat.compute({"events": [{"destination_ip": "1.1.1.1"}, {"destination_ip": "1.1.1.1"}]}) == {
        "destination_diversity": 0.0
    }

    # 2 IPs, equal split -> entropy = 1.0
    assert feat.compute({"events": [{"destination_ip": "1.1.1.1"}, {"destination_ip": "2.2.2.2"}]}) == {
        "destination_diversity": 1.0
    }


def test_internal_external_proportion_feature() -> None:
    feat = ipf.InternalExternalProportionFeature()
    assert feat.compute({"events": []}) == {"internal_source_ratio": 0.0}

    events = [
        {"source_ip": "10.0.0.1"},      # Internal (RFC1918)
        {"source_ip": "192.168.1.1"},   # Internal (RFC1918)
        {"source_ip": "8.8.8.8"},       # External
        {"source_ip": "invalid_ip"},    # Should be ignored in ratio
        {"source_ip": None},            # Should be ignored
    ]
    # 2 internal out of 3 valid IPs -> ratio = 2/3
    assert pytest.approx(feat.compute({"events": events})["internal_source_ratio"]) == 2 / 3


def test_ip_user_diversity_feature() -> None:
    feat = ipf.IpUserDiversityFeature()
    events = [
        {"source_ip": "1.1.1.1", "user_name": "a"},
        {"source_ip": "1.1.1.1", "user_name": "b"},
        {"source_ip": "2.2.2.2", "user_name": "a"},
    ]
    # 1.1.1.1 has 2 users. 2.2.2.2 has 1 user. Average = 1.5
    assert feat.compute({"events": events}) == {"ip_user_diversity": 1.5}


def test_ip_host_diversity_feature() -> None:
    feat = ipf.IpHostDiversityFeature()
    events = [
        {"source_ip": "1.1.1.1", "host_name": "h1"},
        {"source_ip": "1.1.1.1", "host_name": "h2"},
        {"source_ip": "2.2.2.2", "host_name": "h1"},
    ]
    # Average = 1.5
    assert feat.compute({"events": events}) == {"ip_host_diversity": 1.5}


def test_historical_ip_deviation_feature() -> None:
    feat = ipf.HistoricalIpFrequencyFeature()
    assert feat.compute({"events": []}) == {"historical_ip_deviation": 0.0}

    baseline = {"known_source_ips": {"1.1.1.1", "2.2.2.2"}}
    events = [
        {"source_ip": "1.1.1.1"}, # known
        {"source_ip": "2.2.2.2"}, # known
        {"source_ip": "3.3.3.3"}, # unknown -> novel
        {"source_ip": None},      # 'unknown', which is not in known_source_ips -> novel
    ]
    # 2 novel out of 4 events -> 0.5
    assert feat.compute({"events": events, "baseline": baseline}) == {"historical_ip_deviation": 0.5}


def test_relationship_novelty_feature() -> None:
    feat = ipf.RelationshipNoveltyFeature()
    assert feat.compute({"events": []}) == {"relationship_novelty_ip_user": 0.0}

    baseline = {"known_ip_user_pairs": {("1.1.1.1", "alice"), ("2.2.2.2", "bob")}}
    events = [
        {"source_ip": "1.1.1.1", "user_name": "alice"}, # known pair
        {"source_ip": "1.1.1.1", "user_name": "bob"},   # novel pair (known IP, known user, but novel relationship)
        {"source_ip": "3.3.3.3", "user_name": "charlie"}, # completely novel pair
    ]
    # 2 novel out of 3 events -> 2/3
    assert pytest.approx(feat.compute({"events": events, "baseline": baseline})["relationship_novelty_ip_user"]) == 2 / 3
