"""
Tests for Entropy features.
"""
from __future__ import annotations

from typing import Any

import pytest

import tads.features.entropy as ef
from tads.features.utils import calculate_entropy


def test_entropy_edge_cases() -> None:
    # Empty window -> H=0
    assert calculate_entropy([], "field") == 0.0

    # Single-value distribution -> H=0
    assert calculate_entropy([{"field": "A"}], "field") == 0.0
    assert calculate_entropy([{"field": "A"}, {"field": "A"}], "field") == 0.0

    # Two-category 50/50 split -> H=1 bit
    # 2 events: p(A)=0.5, p(B)=0.5 -> - (0.5*-1 + 0.5*-1) = 1.0
    events = [{"field": "A"}, {"field": "B"}]
    assert pytest.approx(calculate_entropy(events, "field")) == 1.0

    # Uniform 4-category split -> H=2 bits
    # 4 events: p=0.25 -> - (4 * 0.25 * -2) = 2.0
    events = [{"field": "A"}, {"field": "B"}, {"field": "C"}, {"field": "D"}]
    assert pytest.approx(calculate_entropy(events, "field")) == 2.0

    # Missing fields mapped to 'unknown'
    missing_events: list[dict[str, Any]] = [{"field": None}, {"field": None}]
    # Single value ('unknown') -> H=0
    assert calculate_entropy(missing_events, "field") == 0.0


def test_user_entropy_feature() -> None:
    feat = ef.UserEntropyFeature()
    assert feat.compute({"events": []}) == {"user_entropy": 0.0}
    events = [{"user_name": "a"}, {"user_name": "b"}]
    assert feat.compute({"events": events}) == {"user_entropy": 1.0}


def test_ip_entropy_feature() -> None:
    feat = ef.IpEntropyFeature()
    assert feat.compute({"events": []}) == {"source_ip_entropy": 0.0}
    events = [{"source_ip": "a"}, {"source_ip": "b"}]
    assert feat.compute({"events": events}) == {"source_ip_entropy": 1.0}


def test_host_entropy_feature() -> None:
    feat = ef.HostEntropyFeature()
    assert feat.compute({"events": []}) == {"host_entropy": 0.0}
    events = [{"host_name": "a"}, {"host_name": "b"}]
    assert feat.compute({"events": events}) == {"host_entropy": 1.0}


def test_process_entropy_feature() -> None:
    feat = ef.ProcessEntropyFeature()
    assert feat.compute({"events": []}) == {"process_entropy": 0.0}
    events = [{"process_name": "a"}, {"process_name": "b"}]
    assert feat.compute({"events": events}) == {"process_entropy": 1.0}


def test_destination_entropy_feature() -> None:
    feat = ef.DestinationEntropyFeature()
    assert feat.compute({"events": []}) == {"destination_entropy": 0.0}
    events = [{"destination_ip": "a"}, {"destination_ip": "b"}]
    assert feat.compute({"events": events}) == {"destination_entropy": 1.0}


def test_protocol_entropy_feature() -> None:
    feat = ef.ProtocolEntropyFeature()
    assert feat.compute({"events": []}) == {"protocol_entropy": 0.0}
    events = [{"network_protocol": "tcp"}, {"network_protocol": "udp"}]
    assert feat.compute({"events": events}) == {"protocol_entropy": 1.0}


def test_category_entropy_feature() -> None:
    feat = ef.CategoryEntropyFeature()
    assert feat.compute({"events": []}) == {"event_category_entropy": 0.0}
    events = [{"event_category": "auth"}, {"event_category": "network"}]
    assert feat.compute({"events": events}) == {"event_category_entropy": 1.0}
