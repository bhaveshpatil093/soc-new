"""
Validation benchmark for RobustStatisticalDetector.

Demonstrates:
1. Robust statistical training on July data.
2. Calibration mapping.
3. Feature-level and window-level evidence correctness via deliberate injection.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.detectors.statistical import RobustStatisticalDetector


def generate_mock_features(n_windows: int, start_day: int = 1) -> pa.Table:
    """Generate mock feature matrix."""
    start = datetime(2025, 7, start_day, tzinfo=UTC)
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    # Normally distributed feature
    f1 = np.random.normal(50, 10, n_windows)

    # Heavy-tailed feature (exponential)
    f2 = np.random.exponential(scale=5, size=n_windows)

    # Poisson feature
    f3 = np.random.poisson(2.0, n_windows).astype(float)

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
        "feature_3": f3.tolist(),
    })


def main() -> None:
    np.random.seed(42)

    print("=== STEP 1: Generate July Data ===")
    n_train = 10000
    n_val = 10

    train_data = generate_mock_features(n_train, start_day=1)
    val_data = generate_mock_features(n_val, start_day=15)

    features = ["feature_1", "feature_2", "feature_3"]

    print("\n=== STEP 2: Train RobustStatisticalDetector ===")
    detector = RobustStatisticalDetector(feature_columns=features, version="stat-v1")
    detector.fit(train_data)

    print("\n=== STEP 3: Calibration ===")
    detector.fit_calibrator(train_data, threshold_evidence=0.99)

    print("\n=== STEP 4: Validation Gate - Feature Level Evidence ===")

    # We will inject an extreme value into feature_2 (heavy tailed) in window index 5.
    val_f1 = val_data.column("feature_1").to_numpy().copy()
    val_f2 = val_data.column("feature_2").to_numpy().copy()
    val_f3 = val_data.column("feature_3").to_numpy().copy()

    target_idx = 5
    injected_value = 5000.0  # Extremely unlikely for an exponential with scale=5
    val_f2[target_idx] = injected_value

    injected_data = pa.table({
        "window_start": val_data.column("window_start"),
        "feature_1": val_f1.tolist(),
        "feature_2": val_f2.tolist(),
        "feature_3": val_f3.tolist(),
    })

    preds = detector.predict(injected_data)
    explanations = detector.explain(injected_data)

    flags = preds.column("anomaly").to_numpy(zero_copy_only=False)
    scores = preds.column("raw_score").to_numpy()
    evidence = preds.column("calibrated_evidence").to_numpy()

    for i in range(len(injected_data)):
        print(f"Window {i}:")
        print(f"  Raw Score (Max Z): {scores[i]:.2f}")
        print(f"  Evidence: {evidence[i]:.4f}")
        print(f"  Flagged: {flags[i]}")
        print(f"  Explanation: {explanations[i].as_py()}")

    print("\nVerifying injection...")
    assert flags[target_idx], "Injected window was not flagged!"
    assert "feature_2" in explanations[target_idx].as_py(), "Explanation did not attribute to the injected feature!"

    print("✅ Validation Gate Passed: The injected anomaly was caught and correctly attributed to feature_2.")

    print("\n=== STEP 5: Save/Load Round-Trip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "stat.json"
        detector.save(model_path)

        loaded = RobustStatisticalDetector(feature_columns=[])
        loaded.load(model_path)

        loaded_scores = loaded.score(injected_data)

        max_diff = np.max(np.abs(scores - loaded_scores.to_numpy()))

        print(f"  Max score difference after round-trip: {max_diff:.10f}")
        assert max_diff < 1e-5, "Round-trip failed."
        print("  ✅ Round-trip successful.")


if __name__ == "__main__":
    main()
