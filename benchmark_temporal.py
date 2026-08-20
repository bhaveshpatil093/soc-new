"""
Validation benchmark for temporal anomaly classification.

Injects specific data patterns into a synthetic dataset and proves that the
TemporalAnalyzer correctly classifies them based on timestamps and trends,
without using static attack rules.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa

from tads.explanation.episodes import EpisodeGrouper
from tads.explanation.temporal_analysis import TemporalAnalyzer
from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.ensemble import EnsembleDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector


def generate_realistic_features(n_windows: int, start: datetime) -> pa.Table:
    """Generate realistic synthetic features."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    event_counts = np.random.poisson(lam=10, size=n_windows)
    f_volume = event_counts * np.random.normal(5, 0.5, n_windows)
    f_latency = np.random.normal(30, 2, n_windows)
    f_cpu = np.random.normal(30, 2, n_windows)
    f_mem = f_cpu * 1.5 + np.random.normal(0, 1, n_windows)

    users = ["alice", "bob", "charlie", "david", "eve", "service-account"]
    hosts = ["web-01", "web-02", "db-01"]

    u_col = np.random.choice(users, size=n_windows, p=[0.3, 0.2, 0.15, 0.1, 0.05, 0.2])
    h_col = np.random.choice(hosts, size=n_windows, p=[0.5, 0.4, 0.1])

    return pa.table({
        "window_start": timestamps,
        "event_count": event_counts.tolist(),
        "f_volume": f_volume.tolist(),
        "f_latency": f_latency.tolist(),
        "f_cpu": f_cpu.tolist(),
        "f_mem": f_mem.tolist(),
        "user": u_col.tolist(),
        "host": h_col.tolist(),
    })


def inject_anomalies(data: pa.Table) -> pa.Table:
    """Inject anomalies into specific indices to trigger temporal patterns."""
    f_vol = data.column("f_volume").to_numpy().copy()
    f_cpu = data.column("f_cpu").to_numpy().copy()
    f_lat = data.column("f_latency").to_numpy().copy()
    users = data.column("user").to_pylist()
    events = data.column("event_count").to_numpy().copy()

    # We leave huge gaps between these indices (e.g. 100, 300, 500) so they don't merge.

    # 1. OCCUR ONCE (Index 100)
    users[100] = "USER_ONCE"
    events[100] = 300
    f_vol[100] = 3000.0

    # 2. REPEAT (Index 200, 250)
    users[200] = "USER_REPEAT"
    events[200] = 300
    f_vol[200] = 3000.0

    users[250] = "USER_REPEAT"
    events[250] = 300
    f_vol[250] = 3000.0

    # 3. PERSIST (Index 300 to 314) -> 15 windows = 75 seconds
    for i in range(300, 315):
        users[i] = "USER_PERSIST"
        events[i] = 300
        f_vol[i] = 3000.0

    # 4. ESCALATE (Index 400 to 405) -> strictly increasing CPU anomaly
    # Keep volume normal so we don't instantly peg evidence to 1.0
    for i in range(6):
        idx = 400 + i
        users[idx] = "USER_ESCALATE"
        # Ramp up latency to slowly push evidence up without maxing out
        f_lat[idx] = 100.0 + (i * 20.0)

    # 5. RECUR PERIODICALLY (Index 500, 600, 700) -> Exact 100-window (500s) gaps
    for idx in [500, 600, 700]:
        users[idx] = "USER_PERIODIC"
        events[idx] = 300
        f_vol[idx] = 3000.0

    return pa.table({
        "window_start": data.column("window_start"),
        "event_count": events.tolist(),
        "f_volume": f_vol.tolist(),
        "f_latency": f_lat.tolist(),
        "f_cpu": f_cpu.tolist(),
        "f_mem": data.column("f_mem"),
        "user": users,
        "host": data.column("host"),
    })


def main() -> None:
    np.random.seed(42)

    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]

    print("=== Training on July Baseline ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_realistic_features(5000, start=july_start)

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
    raw_august = generate_realistic_features(1000, start=august_start)
    august_data = inject_anomalies(raw_august)

    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)

    combined_data = pa.table({
        "window_start": august_data.column("window_start"),
        "user": august_data.column("user"),
        "host": august_data.column("host"),
        "ensemble_evidence": results.column("ensemble_evidence"),
        "detector_agreement": results.column("detector_agreement"),
        "primary_category": results.column("primary_category"),
    })

    grouper = EpisodeGrouper(evidence_floor=0.90, max_gap_seconds=15.0, alert_threshold=0.95)
    episodes = grouper.group(combined_data)

    print(f"\nCreated {len(episodes)} anomaly episodes.")

    print("\n=== Running Temporal Analysis ===")
    analyzer = TemporalAnalyzer()
    classifications = analyzer.analyze(episodes)

    # Filter the noisy background episodes to just show the injected ones to prove the logic
    print("\n" + "="*80)
    print("=== CATEGORY VERIFICATION ===")
    print("="*80)

    for category, eps in classifications.items():
        print(f"\n--- Category: {category.upper()} ---")
        if not eps:
            print("No examples found.")
            continue

        # We find one of our injected users in the category to prove it worked
        injected_eps = [e for e in eps if any("USER_" in u for u in e.affected_users)]

        if not injected_eps:
            print("Only background noise found in this category.")
            continue

        for ep in injected_eps[:2]: # Show up to 2 examples
            print(f"Episode ID: {ep.episode_id} | Users: {ep.affected_users}")
            print(f"Duration:   {ep.duration_seconds}s | Windows: {ep.window_count}")
            print(f"Peak Ev:    {ep.peak_evidence:.4f}")
            if category == "escalate":
                print(f"Evidence Trend: {[round(v, 4) for v in ep.evidence_trend]}")

        if len(injected_eps) > 2:
            print(f"... and {len(injected_eps) - 2} more related episodes.")

if __name__ == "__main__":
    main()
