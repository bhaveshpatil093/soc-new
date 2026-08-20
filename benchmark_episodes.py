"""
Validation benchmark for anomaly episode grouping.

Validates that consecutive/related anomalous windows are properly grouped
into episodes, and stats are aggregated correctly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa
from tabulate import tabulate

from tads.explanation.episodes import EpisodeGrouper
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
    f_volume = event_counts * np.random.normal(5, 1, n_windows)
    f_latency = np.random.exponential(scale=50, size=n_windows)
    f_cpu = np.random.normal(30, 5, n_windows)
    f_mem = f_cpu * 1.5 + np.random.normal(0, 2, n_windows)
    
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
    """Inject a 3-window sustained burst anomaly."""
    n_windows = len(data)
    
    f_vol = data.column("f_volume").to_numpy().copy()
    f_lat = data.column("f_latency").to_numpy().copy()
    f_cpu = data.column("f_cpu").to_numpy().copy()
    f_mem = data.column("f_mem").to_numpy().copy()
    users = data.column("user").to_pylist()
    hosts = data.column("host").to_pylist()
    events = data.column("event_count").to_numpy().copy()
    
    # Sustained Attack / Temporal Burst (3 consecutive high-volume windows)
    idx_burst = 4000
    for i in range(3):
        events[idx_burst + i] = 500
        f_vol[idx_burst + i] = 5000.0
        f_cpu[idx_burst + i] = 99.0
        users[idx_burst + i] = "HACKER_ADMIN"
        hosts[idx_burst + i] = "db-01"
        
    return pa.table({
        "window_start": data.column("window_start"),
        "event_count": events.tolist(),
        "f_volume": f_vol.tolist(),
        "f_latency": f_lat.tolist(),
        "f_cpu": f_cpu.tolist(),
        "f_mem": f_mem.tolist(),
        "user": users,
        "host": hosts,
    })


def main() -> None:
    np.random.seed(42)
    
    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]
    
    print("=== Training on July Baseline ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_realistic_features(10000, start=july_start)
    
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
    raw_august = generate_realistic_features(5000, start=august_start)
    august_data = inject_anomalies(raw_august)
    
    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)
    
    # Combine results with window_start, user, host for Episode Grouper
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
    
    print(f"\nCreated {len(episodes)} episodes.")
    
    # Find the multi-window burst episode (it has HACKER_ADMIN)
    burst_ep = next(e for e in episodes if "HACKER_ADMIN" in e.affected_users)
    
    print("\n" + "="*80)
    print("=== MULTI-WINDOW BURST EPISODE ===")
    print("="*80)
    print(f"Episode ID:     {burst_ep.episode_id}")
    print(f"Start Time:     {burst_ep.start_time}")
    print(f"End Time:       {burst_ep.end_time}")
    print(f"Duration:       {burst_ep.duration_seconds}s")
    print(f"Window Count:   {burst_ep.window_count}")
    print(f"Peak Evidence:  {burst_ep.peak_evidence:.4f}")
    print(f"Mean Evidence:  {burst_ep.mean_evidence:.4f}")
    print(f"Mean Agreement: {burst_ep.model_agreement_mean:.2f}")
    print(f"Affected Users: {burst_ep.affected_users}")
    print(f"Affected Hosts: {burst_ep.affected_hosts}")
    print(f"Categories:     {burst_ep.primary_categories}")
    
    print("\n--- Constituent Windows Sanity Check ---")
    timestamps = combined_data.column("window_start").to_pylist()
    evidences = combined_data.column("ensemble_evidence").to_pylist()
    agreements = combined_data.column("detector_agreement").to_pylist()
    
    # Find the indices of the windows that fall within the episode's time bounds
    constituent_indices = [
        i for i, ts in enumerate(timestamps)
        if burst_ep.start_time <= ts <= burst_ep.end_time and evidences[i] >= 0.90
    ]
    
    calc_evs = []
    calc_ags = []
    
    for i in constituent_indices:
        ev = evidences[i]
        ag = agreements[i]
        calc_evs.append(ev)
        calc_ags.append(ag)
        print(f"Window {i} Evidence: {ev:.4f} | Agreement: {ag}")
        
    calc_peak = max(calc_evs)
    calc_mean = sum(calc_evs) / len(calc_evs)
    calc_ag_mean = sum(calc_ags) / len(calc_ags)
    
    print("\n--- Manual Recomputation ---")
    print(f"Calculated Peak:       {calc_peak:.4f}  (Matches: {abs(calc_peak - burst_ep.peak_evidence) < 1e-6})")
    print(f"Calculated Mean:       {calc_mean:.4f}  (Matches: {abs(calc_mean - burst_ep.mean_evidence) < 1e-6})")
    print(f"Calculated Mean Agree: {calc_ag_mean:.2f}  (Matches: {abs(calc_ag_mean - burst_ep.model_agreement_mean) < 1e-6})")

if __name__ == "__main__":
    main()
