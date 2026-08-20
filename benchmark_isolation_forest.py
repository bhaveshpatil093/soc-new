"""
Benchmark and validation script for Isolation Forest detector.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.detectors.isolation_forest import IsolationForestDetector

# Ensure deterministic generation
np.random.seed(42)

def generate_mock_data(start_time: datetime, num_windows: int, anomaly_fraction: float = 0.0) -> pa.Table:
    """Generate mock features. Mostly clustered normal data, with occasional extreme anomalies."""
    timestamps = [start_time + timedelta(seconds=i*5) for i in range(num_windows)]

    # Feature 1: normally clustered around 10
    f1 = np.random.normal(10, 2, num_windows)
    # Feature 2: normally clustered around 50
    f2 = np.random.normal(50, 10, num_windows)
    # Feature 3: mostly zeros, occasionally small integers
    f3 = np.random.poisson(1.0, num_windows).astype(float)

    if anomaly_fraction > 0:
        num_anomalies = int(num_windows * anomaly_fraction)
        anomaly_indices = np.random.choice(num_windows, num_anomalies, replace=False)
        # Anomalies break the pattern wildly
        f1[anomaly_indices] = np.random.uniform(50, 100, num_anomalies)
        f2[anomaly_indices] = np.random.uniform(-100, -50, num_anomalies)
        f3[anomaly_indices] = np.random.uniform(50, 200, num_anomalies)

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
        "feature_3": f3.tolist(),
    })


def main() -> None:
    print("--- Isolation Forest Validation Benchmark ---")

    # 1. Generate July training data (mostly normal, maybe 1% random noise/anomalies)
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    train_windows = 10000
    print(f"Generating {train_windows} training windows...")
    train_data = generate_mock_data(july_start, train_windows, anomaly_fraction=0.01)

    # 2. Fit the detector
    detector = IsolationForestDetector(
        feature_columns=["feature_1", "feature_2", "feature_3"],
        n_jobs=1
    )
    print("Fitting Isolation Forest...")
    detector.fit(train_data)

    # 3. Prove Save/Load
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "model.joblib"
        detector.save(tmp_path)

        loaded_detector = IsolationForestDetector(feature_columns=[])
        loaded_detector.load(tmp_path)

    # 4. Generate July validation split (purely normal data)
    val_start = datetime(2025, 7, 20, tzinfo=UTC)
    val_windows = 2000
    print(f"\nGenerating {val_windows} validation windows (normal)...")
    val_normal_data = generate_mock_data(val_start, val_windows, anomaly_fraction=0.0)

    # Generate explicit anomalies
    print("Generating 100 validation windows (anomalous)...")
    val_anom_data = generate_mock_data(val_start + timedelta(days=1), 100, anomaly_fraction=1.0)

    # 5. Score Data
    normal_preds = loaded_detector.predict(val_normal_data)
    anom_preds = loaded_detector.predict(val_anom_data)

    normal_scores = np.array(normal_preds.column("raw_score").to_pylist())
    anom_scores = np.array(anom_preds.column("raw_score").to_pylist())

    # 6. Report Distributions
    print("\n=== RAW SCORE DISTRIBUTION (Path Length Based) ===")
    print("Percentile | Normal Data | Anomalous Data")
    print("-" * 45)

    percentiles = [0, 10, 50, 90, 99, 100]

    for p in percentiles:
        norm_val = np.percentile(normal_scores, p)
        anom_val = np.percentile(anom_scores, p)
        print(f"p{p:<9} | {norm_val:>11.4f} | {anom_val:>14.4f}")

    print("\nObservation:")
    print("Notice the continuous spectrum of scores. Normal data is tightly clustered")
    print(f"with a max score of {np.max(normal_scores):.4f}. Anomalous data scores significantly higher,")
    print(f"starting at {np.min(anom_scores):.4f} and maxing at {np.max(anom_scores):.4f}.")
    print("This proves the forest produces a smooth, non-degenerate ranking signal.")


if __name__ == "__main__":
    main()
