"""
Tests for Network behavioral features.
"""
from __future__ import annotations

import tads.features.network as nf


def test_network_unique_destinations_feature() -> None:
    feat = nf.NetworkUniqueDestinationsFeature()
    assert feat.compute({"events": []}) == {"network_unique_destinations": 0.0}
    events = [{"destination_ip": "1.1.1.1"}, {"destination_ip": "2.2.2.2"}, {"destination_ip": "1.1.1.1"}]
    assert feat.compute({"events": events}) == {"network_unique_destinations": 2.0}


def test_unique_destination_ports_feature() -> None:
    feat = nf.UniqueDestinationPortsFeature()
    assert feat.compute({"events": []}) == {"unique_destination_ports": 0.0}
    events = [{"destination_port": 80}, {"destination_port": 443}, {"destination_port": 80}]
    assert feat.compute({"events": events}) == {"unique_destination_ports": 2.0}


def test_protocol_diversity_feature() -> None:
    feat = nf.ProtocolDiversityFeature()
    assert feat.compute({"events": []}) == {"protocol_diversity": 0.0}

    events = [{"network_protocol": "tcp"}, {"network_protocol": "tcp"}]
    assert feat.compute({"events": events}) == {"protocol_diversity": 0.0}

    events = [{"network_protocol": "tcp"}, {"network_protocol": "udp"}]
    assert feat.compute({"events": events}) == {"protocol_diversity": 1.0}


def test_source_destination_diversity_feature() -> None:
    feat = nf.SourceDestinationDiversityFeature()
    events = [
        {"source_ip": "10.0.0.1", "destination_ip": "1.1.1.1"},
        {"source_ip": "10.0.0.1", "destination_ip": "8.8.8.8"},
        {"source_ip": "10.0.0.2", "destination_ip": "1.1.1.1"},
    ]
    # 10.0.0.1 -> 2 distinct
    # 10.0.0.2 -> 1 distinct
    # Average = 1.5
    assert feat.compute({"events": events}) == {"source_destination_diversity": 1.5}


def test_connection_concentration_feature() -> None:
    feat = nf.ConnectionConcentrationFeature()
    assert feat.compute({"events": []}) == {"connection_concentration": 0.0}

    events = [
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
    ]
    assert feat.compute({"events": events}) == {"connection_concentration": 1.0}

    events = [
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
        {"source_ip": "s2", "destination_ip": "d2", "destination_port": 443},
    ]
    assert feat.compute({"events": events}) == {"connection_concentration": 0.5}


def test_network_entropy_feature() -> None:
    feat = nf.NetworkEntropyFeature()
    assert feat.compute({"events": []}) == {"network_entropy": 0.0}

    events = [
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
    ]
    assert feat.compute({"events": events}) == {"network_entropy": 0.0}

    events = [
        {"source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
        {"source_ip": "s2", "destination_ip": "d2", "destination_port": 443},
    ]
    assert feat.compute({"events": events}) == {"network_entropy": 1.0}


def test_host_network_relationships_feature() -> None:
    feat = nf.HostNetworkRelationshipsFeature()
    assert feat.compute({"events": []}) == {"host_network_relationships": 0.0}

    events = [
        {"host_name": "h1", "source_ip": "s1", "destination_ip": "d1", "destination_port": 80},
        {"host_name": "h1", "source_ip": "s1", "destination_ip": "d1", "destination_port": 443}, # different connection tuple
        {"host_name": "h2", "source_ip": "s2", "destination_ip": "d2", "destination_port": 443},
    ]
    # h1 -> 2 distinct connection tuples
    # h2 -> 1 distinct connection tuple
    # Average = 1.5
    assert feat.compute({"events": events}) == {"host_network_relationships": 1.5}
