"""
Tests for Process behavioral features.
"""
from __future__ import annotations

import tads.features.processes as pf


def test_normalize_cmdline() -> None:
    # Empty cases
    assert pf.normalize_cmdline(None) == "unknown"
    assert pf.normalize_cmdline("") == "unknown"

    # UUIDs
    assert pf.normalize_cmdline("process.exe --id 123e4567-e89b-12d3-a456-426614174000") == "process.exe --id <UUID>"

    # IPs
    assert pf.normalize_cmdline("ping 192.168.1.1") == "ping <IP>"

    # Hex
    assert pf.normalize_cmdline("process.exe a1b2c3d4e5f67890") == "process.exe <HEX>"

    # Numbers
    assert pf.normalize_cmdline("kill -9 1234") == "kill -<NUM> <NUM>"

    # Paths (Unix and Windows)
    assert pf.normalize_cmdline("cat /var/log/syslog") == "cat <PATH>"
    assert pf.normalize_cmdline(r"type C:\Temp\foo.txt") == "type <PATH>"

    # Mixed and complex
    raw = r"C:\Windows\cmd.exe /c start proc.exe --pid 1234 --out C:\Temp\a.txt 10.0.0.1 550e8400-e29b-41d4-a716-446655440000"
    expected = "<PATH> <PATH> start proc.exe --pid <NUM> --out <PATH> <IP> <UUID>"
    assert pf.normalize_cmdline(raw) == expected


def test_active_processes_feature() -> None:
    feat = pf.ActiveProcessesFeature()
    assert feat.compute({"events": []}) == {"active_processes": 0.0}
    events = [{"process_name": "p1"}, {"process_name": "p2"}, {"process_name": "p1"}]
    assert feat.compute({"events": events}) == {"active_processes": 2.0}


def test_process_event_concentration_feature() -> None:
    feat = pf.ProcessEventConcentrationFeature()
    assert feat.compute({"events": []}) == {"process_event_concentration": 0.0}
    events = [{"process_name": "p1"}, {"process_name": "p2"}]
    assert feat.compute({"events": events}) == {"process_event_concentration": 0.5}


def test_process_host_diversity_feature() -> None:
    feat = pf.ProcessHostDiversityFeature()
    events = [
        {"process_name": "p1", "host_name": "h1"},
        {"process_name": "p1", "host_name": "h2"},
        {"process_name": "p2", "host_name": "h1"},
    ]
    # Average distinct hosts per process = 1.5
    assert feat.compute({"events": events}) == {"process_host_diversity": 1.5}


def test_process_user_diversity_feature() -> None:
    feat = pf.ProcessUserDiversityFeature()
    events = [
        {"process_name": "p1", "user_name": "u1"},
        {"process_name": "p1", "user_name": "u2"},
        {"process_name": "p2", "user_name": "u1"},
    ]
    assert feat.compute({"events": events}) == {"process_user_diversity": 1.5}


def test_parent_child_diversity_feature() -> None:
    feat = pf.ParentChildDiversityFeature()
    events = [
        {"process_name": "child.exe", "process_parent_name": "parent1.exe"},
        {"process_name": "child.exe", "process_parent_name": "parent2.exe"},
    ]
    assert feat.compute({"events": events}) == {"parent_child_diversity": 2.0}


def test_cmdline_pattern_diversity_feature() -> None:
    feat = pf.CmdlinePatternDiversityFeature()
    assert feat.compute({"events": []}) == {"cmdline_pattern_diversity": 0.0}

    events = [
        {"process_command_line": "proc.exe --pid 1234"},
        {"process_command_line": "proc.exe --pid 5678"}, # Same pattern
    ]
    # Entropy of 1 pattern = 0.0
    assert feat.compute({"events": events}) == {"cmdline_pattern_diversity": 0.0}

    events = [
        {"process_command_line": "proc.exe --pid 1234"},
        {"process_command_line": "other.exe --force"}, # Different pattern
    ]
    # Entropy of 2 patterns, equal split = 1.0
    assert feat.compute({"events": events}) == {"cmdline_pattern_diversity": 1.0}


def test_historical_process_deviation_feature() -> None:
    feat = pf.HistoricalProcessDeviationFeature()
    assert feat.compute({"events": []}) == {"historical_process_deviation": 0.0}

    baseline = {"known_processes": {"p1", "p2"}}
    events = [
        {"process_name": "p1"}, # known
        {"process_name": "p3"}, # novel
    ]
    # 1 novel out of 2 events -> 0.5
    assert feat.compute({"events": events, "baseline": baseline}) == {"historical_process_deviation": 0.5}
