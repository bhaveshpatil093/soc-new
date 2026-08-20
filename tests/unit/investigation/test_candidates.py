"""Tests for AlertCrossReferencer."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from tads.explanation.episodes import AnomalyEpisode
from tads.investigation.candidates import AlertCrossReferencer, LegacyAlert


def test_cross_reference_filters_covered_episodes() -> None:
    referencer = AlertCrossReferencer(time_window_minutes=5.0)
    
    ep_start = datetime(2025, 8, 1, 12, 0, 0, tzinfo=UTC)
    ep_covered = AnomalyEpisode(
        episode_id="ep_cov",
        start_time=ep_start,
        end_time=ep_start,
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.99,
        mean_evidence=0.99,
        affected_users={"alice"},
    )
    
    ep_uncovered = AnomalyEpisode(
        episode_id="ep_uncov",
        start_time=ep_start,
        end_time=ep_start,
        duration_seconds=5.0,
        window_count=1,
        peak_evidence=0.99,
        mean_evidence=0.99,
        affected_users={"bob"},
    )
    
    # Alert for alice at the exact time
    alert1 = LegacyAlert(
        alert_id="alert1",
        rule_name="High CPU",
        timestamp=ep_start,
        entities={"alice"},
    )
    
    # Alert for bob, but 10 hours later (out of window)
    alert2 = LegacyAlert(
        alert_id="alert2",
        rule_name="Failed Login",
        timestamp=datetime(2025, 8, 1, 22, 0, 0, tzinfo=UTC),
        entities={"bob"},
    )
    
    mock_attributor = MagicMock()
    mock_temporal = MagicMock()
    mock_temporal.analyze.return_value = {}
    
    candidates = referencer.cross_reference(
        episodes=[ep_covered, ep_uncovered],
        legacy_alerts=[alert1, alert2],
        attributor=mock_attributor,
        temporal_analyzer=mock_temporal,
        drift_context_map={},
    )
    
    assert len(candidates) == 1
    assert candidates[0].episode.episode_id == "ep_uncov"
    assert "CONFIRMED" in candidates[0].alert_clearance_statement
    assert "legacy alert" in candidates[0].alert_clearance_statement
    assert "attack" not in candidates[0].alert_clearance_statement.lower()
