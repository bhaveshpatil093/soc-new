"""
Validation benchmark for Model-Only Candidate Anomaly identification.

Ensures that we correctly cross-reference anomaly episodes against existing
legacy alerts, filtering out covered events, and exclusively producing
"model-only candidate anomalies" with full context.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa

from tads.explanation.attribution import EventAttributor
from tads.explanation.episodes import EpisodeGrouper
from tads.explanation.temporal_analysis import TemporalAnalyzer
from tads.inference.pipeline import AugustInferencePipeline
from tads.investigation.candidates import AlertCrossReferencer, LegacyAlert
from tads.models.detectors.ensemble import EnsembleDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector


def generate_synthetic_features(n_windows: int, start: datetime) -> pa.Table:
    """Generate synthetic features for testing."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    event_counts = np.random.poisson(lam=10, size=n_windows)
    f_volume = event_counts * np.random.normal(5, 0.5, n_windows)
    f_latency = np.random.normal(30, 2, n_windows)
    f_cpu = np.random.normal(30, 2, n_windows)
    f_mem = f_cpu * 1.5 + np.random.normal(0, 1, n_windows)

    users = ["alice", "bob", "service-account"]
    hosts = ["web-01", "db-01"]

    u_col = np.random.choice(users, size=n_windows)
    h_col = np.random.choice(hosts, size=n_windows)

    return pa.table(
        {
            "window_start": timestamps,
            "event_count": event_counts.tolist(),
            "f_volume": f_volume.tolist(),
            "f_latency": f_latency.tolist(),
            "f_cpu": f_cpu.tolist(),
            "f_mem": f_mem.tolist(),
            "user": u_col.tolist(),
            "host": h_col.tolist(),
        }
    )


def inject_anomalies(data: pa.Table) -> pa.Table:
    """Inject two specific anomalies: one to be covered by legacy, one model-only."""
    f_vol = data.column("f_volume").to_numpy().copy()
    users = data.column("user").to_pylist()
    events = data.column("event_count").to_numpy().copy()

    # Anomaly 1: A massive spike for 'alice' at index 100
    # We will mock a legacy alert for this exact time and user.
    for i in range(100, 105):
        users[i] = "alice"
        events[i] = 500
        f_vol[i] = 5000.0

    # Anomaly 2: A massive spike for 'bob' at index 200
    # This will be our MODEL-ONLY CANDIDATE ANOMALY.
    for i in range(200, 205):
        users[i] = "bob"
        events[i] = 500
        f_vol[i] = 5000.0

    return pa.table(
        {
            "window_start": data.column("window_start"),
            "event_count": events.tolist(),
            "f_volume": f_vol.tolist(),
            "f_latency": data.column("f_latency"),
            "f_cpu": data.column("f_cpu"),
            "f_mem": data.column("f_mem"),
            "user": users,
            "host": data.column("host"),
        }
    )


def main() -> None:
    np.random.seed(42)

    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]

    print("=== Training on July Baseline ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_synthetic_features(2000, start=july_start)

    detectors = {
        "IForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95),
        "Statistical": RobustStatisticalDetector(feature_columns=cont_features),
        "Rarity": RarityDetector(feature_columns=cat_features),
    }

    ensemble = EnsembleDetector(detectors=detectors, strategy="max")
    ensemble.fit(july_data)

    print("=== Scoring August Data ===")
    august_start = datetime(2025, 8, 1, tzinfo=UTC)
    raw_august = generate_synthetic_features(500, start=august_start)
    august_data = inject_anomalies(raw_august)

    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)

    combined_data = pa.table(
        {
            "window_start": august_data.column("window_start"),
            "user": august_data.column("user"),
            "host": august_data.column("host"),
            "ensemble_evidence": results.column("ensemble_evidence"),
            "detector_agreement": results.column("detector_agreement"),
            "primary_category": results.column("primary_category"),
        }
    )

    grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)
    episodes = grouper.group(combined_data)

    # Isolate the two injected episodes from the background noise
    target_episodes = [ep for ep in episodes if ep.window_count >= 5]

    print(f"\nExtracted {len(target_episodes)} major anomaly episodes.")

    print("\n=== Mocking Legacy Alerts ===")
    # We create a mock legacy alert that fires right at Anomaly 1 (Index 100)
    anomaly_1_time = august_start + timedelta(seconds=100 * 5)

    legacy_alerts = [
        LegacyAlert(
            alert_id="KIBANA-101",
            rule_name="High Volume Spike",
            timestamp=anomaly_1_time,
            entities={"alice"},
        )
    ]
    print(f"Legacy Alert: KIBANA-101 at {anomaly_1_time} for user 'alice'")

    print("\n=== Cross-Referencing ===")
    referencer = AlertCrossReferencer(time_window_minutes=5.0)
    attributor = EventAttributor()
    temporal_analyzer = TemporalAnalyzer()

    # Mock drift context for the sake of the report
    drift_map = {"f_volume": "Population Drift (Median shifted 20%)"}

    candidates = referencer.cross_reference(
        episodes=target_episodes,
        legacy_alerts=legacy_alerts,
        attributor=attributor,
        temporal_analyzer=temporal_analyzer,
        drift_context_map=drift_map,
        raw_events=august_data,  # Use the window table as a mock for raw events just for stubbing
    )

    print("\n" + "=" * 80)
    print("=== FINAL INVESTIGATION REPORT ===")
    print("=" * 80)
    print(f"Found {len(candidates)} Model-Only Candidate Anomalies (out of {len(target_episodes)} total).")

    for i, c in enumerate(candidates):
        print(f"\n--- MODEL-ONLY CANDIDATE ANOMALY #{i + 1} ---")
        print(f"Episode ID:     {c.episode.episode_id}")
        print(f"Time:           {c.episode.start_time} to {c.episode.end_time}")
        print(f"Entities:       {c.episode.affected_users}")
        print(f"Peak Evidence:  {c.episode.peak_evidence:.4f}")
        print(f"Temporal Class: {c.temporal_context}")
        print(f"Drift Context:  {c.drift_context}")
        print(f"Attribution:    {json.dumps(c.attribution_data)}")
        print(f"Clearance:      {c.alert_clearance_statement}")

        # Verify strict terminology constraints
        assert "attack" not in c.alert_clearance_statement.lower()
        assert "threat" not in c.alert_clearance_statement.lower()


if __name__ == "__main__":
    main()
