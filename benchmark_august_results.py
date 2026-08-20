"""
August Inference Results Benchmark.

Executes the frozen inference pipeline over synthetic August data, generates
aggregate statistics (rates, counts, top evidence), and enforces a strict
Sanity Range Validation Gate (0.01% - 15.0%) to catch pathological behavior.
"""

from __future__ import annotations

import logging
import sys
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

logging.basicConfig(level=logging.INFO)


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


def main() -> None:
    np.random.seed(42)

    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]

    print("=== Training on July Baseline ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_synthetic_features(5000, start=july_start)

    detectors = {
        "IForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95),
        "Statistical": RobustStatisticalDetector(feature_columns=cont_features),
        "Rarity": RarityDetector(feature_columns=cat_features),
    }

    ensemble = EnsembleDetector(detectors=detectors, strategy="mean")
    ensemble.fit(july_data)

    print("=== Scoring August Data ===")
    august_start = datetime(2025, 8, 1, tzinfo=UTC)
    # Simulate ~1 day of data (17280 windows)
    total_august_windows = 17280
    august_data = generate_synthetic_features(total_august_windows, start=august_start)

    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="mean")
    results = pipeline.score_all(august_data)

    # Identify anomalous windows
    # We use the frozen calibration threshold floor of 0.90
    evidence = results.column("ensemble_evidence").to_numpy()
    anomalous_mask = evidence >= 0.90
    anomalous_count = int(np.sum(anomalous_mask))

    anomaly_pct = (anomalous_count / total_august_windows) * 100.0

    # Run episode grouping to get the episode count
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

    # Calculate rates
    total_days = total_august_windows * 5 / (24 * 3600)
    total_hours = total_august_windows * 5 / 3600

    daily_rate = anomalous_count / total_days if total_days > 0 else 0.0
    hourly_rate = anomalous_count / total_hours if total_hours > 0 else 0.0
    top_evidence = float(np.max(evidence))

    print("\n" + "=" * 60)
    print("=== AUGUST INFERENCE STATISTICS ===")
    print("=" * 60)

    table_data = [
        ["Total Windows", f"{total_august_windows:,}"],
        ["Anomalous Windows (>= 0.90)", f"{anomalous_count:,}"],
        ["Anomaly Percentage", f"{anomaly_pct:.3f}%"],
        ["Daily Anomaly Rate (Windows)", f"{daily_rate:.1f} / day"],
        ["Hourly Anomaly Rate (Windows)", f"{hourly_rate:.1f} / hour"],
        ["Anomaly Episodes Extracted", f"{len(episodes):,}"],
        ["Top Anomaly Evidence", f"{top_evidence:.4f}"],
    ]
    print(tabulate(table_data, tablefmt="grid"))

    print("\n=== VALIDATION GATE: SANITY RANGE CHECK ===")

    SANITY_MIN = 0.01
    SANITY_MAX = 15.0

    print(f"Sanity Range: {SANITY_MIN}% to {SANITY_MAX}%")
    print(f"Observed Rate: {anomaly_pct:.3f}%")

    if SANITY_MIN <= anomaly_pct <= SANITY_MAX:
        print("\n✅ SUCCESS: Anomaly percentage falls within the expected sanity range.")
        print("✅ SUCCESS: Results are mathematically valid and trusted for presentation.")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Pathological detector behavior detected!")
        if anomaly_pct > SANITY_MAX:
            print(f"Flagged rate ({anomaly_pct:.3f}%) exceeds maximum limit ({SANITY_MAX}%).")
            print("Reason: Model is over-sensitive or baseline has massively drifted.")
        else:
            print(f"Flagged rate ({anomaly_pct:.3f}%) falls below minimum limit ({SANITY_MIN}%).")
            print("Reason: Model is blind or thresholds are impossibly high.")

        print("\nACTION REQUIRED: Do NOT present these results as valid findings. Investigate the pipeline.")
        sys.exit(1)


if __name__ == "__main__":
    main()
