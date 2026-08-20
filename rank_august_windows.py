"""
Rank and explain the most anomalous August windows.

Produces a diagnostic report of the top 5 highest-evidence windows, including
temporal context, baseline comparisons, and feature-level explanations.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
from tabulate import tabulate

from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.ensemble import EnsembleDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector
from tads.models.detectors.autoencoder import AutoencoderDetector
from tads.models.detectors.sequence_lstm import SequenceLSTMDetector


def generate_realistic_features(n_windows: int, start: datetime) -> pa.Table:
    """Generate realistic synthetic features including an event count."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]
    
    # Simulate realistic baseline
    event_counts = np.random.poisson(lam=10, size=n_windows)
    
    # Core continuous features
    f_volume = event_counts * np.random.normal(5, 1, n_windows)
    f_latency = np.random.exponential(scale=50, size=n_windows)
    f_cpu = np.random.normal(30, 5, n_windows)
    f_mem = f_cpu * 1.5 + np.random.normal(0, 2, n_windows) # Correlated with CPU
    
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
    """Inject specific anomalies into the dataset for validation purposes."""
    n_windows = len(data)
    
    f_vol = data.column("f_volume").to_numpy().copy()
    f_lat = data.column("f_latency").to_numpy().copy()
    f_cpu = data.column("f_cpu").to_numpy().copy()
    f_mem = data.column("f_mem").to_numpy().copy()
    users = data.column("user").to_pylist()
    hosts = data.column("host").to_pylist()
    events = data.column("event_count").to_numpy().copy()
    
    # 1. Pure Statistical Anomaly (Massive spike in latency, everything else normal)
    idx_stat = 500
    f_lat[idx_stat] = 5000.0
    
    # 2. PCA Correlation Anomaly (CPU high but MEM low - violates physics/baseline)
    idx_pca = 1200
    f_cpu[idx_pca] = 95.0
    f_mem[idx_pca] = 10.0
    
    # 3. Novel Relationship Anomaly (Unseen user-host pair)
    idx_rare = 3500
    users[idx_rare] = "HACKER_ADMIN"
    hosts[idx_rare] = "db-01"
    
    # 4. Sustained Attack / Temporal Burst (3 consecutive high-volume windows)
    idx_burst = 4000
    for i in range(3):
        events[idx_burst + i] = 500
        f_vol[idx_burst + i] = 5000.0
        f_cpu[idx_burst + i] = 99.0
        
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
    import torch
    np.random.seed(42)
    torch.manual_seed(42)
    
    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]
    
    print("=== Training on July Baseline ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_realistic_features(10000, start=july_start)
    
    # Calculate July Medians for Baseline Comparison
    july_medians = {
        "event_count": np.median(july_data.column("event_count").to_numpy()),
        "f_volume": np.median(july_data.column("f_volume").to_numpy()),
        "f_latency": np.median(july_data.column("f_latency").to_numpy()),
        "f_cpu": np.median(july_data.column("f_cpu").to_numpy()),
        "f_mem": np.median(july_data.column("f_mem").to_numpy()),
    }
    
    detectors = {
        "IForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95),
        "Statistical": RobustStatisticalDetector(feature_columns=cont_features),
        "Rarity": RarityDetector(feature_columns=cat_features),
        "Autoencoder": AutoencoderDetector(
            feature_columns=cont_features, hidden_dim=8, latent_dim=3, epochs=1, batch_size=256
        ),
        "LSTM": SequenceLSTMDetector(
            feature_columns=cont_features, seq_len=10, hidden_dim=16, num_layers=1, epochs=1, batch_size=128
        ),
    }
    
    ensemble = EnsembleDetector(detectors=detectors, strategy="max")
    ensemble.fit(july_data)
    
    print("=== Scoring August Data ===")
    august_start = datetime(2025, 8, 1, tzinfo=UTC)
    raw_august = generate_realistic_features(5000, start=august_start)
    august_data = inject_anomalies(raw_august)
    
    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)
    
    # Get top 5 windows. Break ties by looking at the sum of all evidences (so windows where MULTIPLE detectors fired rank higher)
    ens_ev = results.column("ensemble_evidence").to_numpy()
    sum_ev = np.sum([results.column(f"evidence_{n}").to_numpy() for n in detectors.keys()], axis=0)
    
    # lexsort sorts by the last key first, so we want sum_ev then ens_ev
    top_indices = np.lexsort((sum_ev, ens_ev))[::-1][:5]
    
    print("\n" + "="*80)
    print("=== TOP 5 AUGUST ANOMALIES ===")
    print("="*80)
    
    # Pre-compute explanations to avoid re-evaluating the whole dataset
    explanations = ensemble.explain(august_data).to_pylist()
    
    for rank, idx in enumerate(top_indices, 1):
        window_start = august_data.column("window_start")[idx].as_py()
        event_count = august_data.column("event_count")[idx].as_py()
        evidence = ens_ev[idx]
        top_det = results.column("top_detector")[idx].as_py()
        category = results.column("primary_category")[idx].as_py()
        
        print(f"\n[{rank}] Timestamp: {window_start} | Evidence: {evidence:.4f} | Events: {event_count}")
        print(f"    Category: {category}")
        
        # Detector breakdown
        print("    --- Detector Breakdown ---")
        for name in detectors.keys():
            det_ev = results.column(f"evidence_{name}")[idx].as_py()
            marker = "*" if name == top_det else " "
            print(f"      {marker} {name:<12}: {det_ev:.4f}")
            
        # Top Feature Deviations
        print("    --- Top Feature Deviations ---")
        print(f"      Explanation: {explanations[idx]}")
        
        # Baseline Comparison
        print("    --- Baseline Comparison ---")
        for f in ["event_count", "f_volume", "f_latency", "f_cpu", "f_mem"]:
            val = august_data.column(f)[idx].as_py()
            baseline = july_medians[f]
            ratio = val / baseline if baseline > 0 else 0
            print(f"      {f:<12}: {val:>8.2f} (July Median: {baseline:>8.2f}) -> {ratio:.1f}x")
            
        # Novel Relationships
        if "Rarity" in top_det or results.column("evidence_Rarity")[idx].as_py() > 0.95:
            user = august_data.column("user")[idx].as_py()
            host = august_data.column("host")[idx].as_py()
            print("    --- Novel Relationships ---")
            print(f"      User: {user} | Host: {host} (Categorical Surprise)")
            
        # Temporal Context
        print("    --- Temporal Context ---")
        if idx > 0:
            prev_ev = ens_ev[idx-1]
            print(f"      [T-1] {august_data.column('window_start')[idx-1].as_py()}: Evidence {prev_ev:.4f}")
        print(f"      [ T ] {window_start}: Evidence {evidence:.4f} <-- CURRENT")
        if idx < len(august_data) - 1:
            next_ev = ens_ev[idx+1]
            print(f"      [T+1] {august_data.column('window_start')[idx+1].as_py()}: Evidence {next_ev:.4f}")
            
    print("\n" + "="*80)
    print("=== INJECTED ANOMALIES SANITY CHECK ===")
    print("="*80)
    
    injected_indices = [500, 1200, 3500, 4000, 4001, 4002]
    for idx in injected_indices:
        evidence = ens_ev[idx]
        top_det = results.column("top_detector")[idx].as_py()
        print(f"Index {idx:4} | Evidence: {evidence:.4f} | Top: {top_det:<10} | Expl: {explanations[idx]}")

if __name__ == "__main__":
    main()
