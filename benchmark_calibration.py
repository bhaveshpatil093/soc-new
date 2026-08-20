"""
Validation Gate for Isolation Forest Calibration.

Demonstrates the full pipeline:
  raw_score → percentile → evidence → threshold → anomaly flag

Also investigates score stability across July halves (H1 vs H2).
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.calibration import EmpiricalCalibrator
from tads.models.detectors.isolation_forest import IsolationForestDetector

np.random.seed(42)


def generate_mock_features(
    start: datetime, n_windows: int, anomaly_frac: float = 0.0
) -> pa.Table:
    """Generate a feature matrix with diurnal patterns and optional anomalies."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]
    hours = np.array([t.hour for t in timestamps])
    is_day = (hours >= 8) & (hours <= 18)

    f1 = np.where(is_day, np.random.normal(50, 10, n_windows), np.random.normal(10, 3, n_windows))
    f2 = np.random.normal(5, 1, n_windows)
    f3 = np.random.poisson(2.0, n_windows).astype(float)

    if anomaly_frac > 0:
        n_anom = int(n_windows * anomaly_frac)
        idx = np.random.choice(n_windows, n_anom, replace=False)
        f1[idx] = np.random.uniform(200, 500, n_anom)
        f2[idx] = np.random.uniform(50, 100, n_anom)
        f3[idx] = np.random.uniform(100, 500, n_anom)

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
        "feature_3": f3.tolist(),
    })


def main() -> None:
    features = ["feature_1", "feature_2", "feature_3"]

    # --- Step 1: Generate July data split into train (H1) and val (H2) ---
    print("=== STEP 1: Generate July Data ===")
    h1_start = datetime(2025, 7, 1, tzinfo=UTC)
    h2_start = datetime(2025, 7, 16, tzinfo=UTC)
    n_train = 10_000
    n_val = 5_000

    train_data = generate_mock_features(h1_start, n_train, anomaly_frac=0.005)
    val_data = generate_mock_features(h2_start, n_val, anomaly_frac=0.005)
    print(f"  Training windows (H1): {n_train}")
    print(f"  Validation windows (H2): {n_val}")

    # --- Step 2: Fit the Isolation Forest on H1 ---
    print("\n=== STEP 2: Fit Isolation Forest on H1 ===")
    detector = IsolationForestDetector(
        feature_columns=features, n_jobs=1, version="iforest-v1.0"
    )
    detector.fit(train_data)

    # --- Step 3: Score H1 (training set) to build calibration CDF ---
    print("\n=== STEP 3: Score H1 to Build Calibration CDF ===")
    h1_raw_scores = detector.score(train_data)
    h1_scores_np = h1_raw_scores.to_numpy()

    print(f"  H1 raw score range: [{h1_scores_np.min():.4f}, {h1_scores_np.max():.4f}]")
    print(f"  H1 raw score median: {np.median(h1_scores_np):.4f}")

    # --- Step 4: Fit the Empirical Calibrator on H1 scores ---
    print("\n=== STEP 4: Fit Empirical Calibrator ===")
    calibrator = EmpiricalCalibrator(
        model_version="iforest-v1.0", threshold_evidence=0.95
    )
    calibrator.fit(h1_raw_scores, data=train_data)

    # --- Step 5: Score the July validation split (H2) ---
    print("\n=== STEP 5: Score July Validation Split (H2) ===")
    h2_raw_scores = detector.score(val_data)
    h2_evidence = calibrator.calibrate(h2_raw_scores)
    h2_flags = calibrator.flag(h2_evidence)

    h2_scores_np = h2_raw_scores.to_numpy()
    h2_evidence_np = h2_evidence.to_numpy()
    h2_flags_np = h2_flags.to_numpy(zero_copy_only=False)

    # --- Step 6: Full Pipeline Report ---
    print("\n" + "=" * 65)
    print("  FULL PIPELINE: raw_score → evidence → threshold → anomaly")
    print("=" * 65)

    print("\n--- Raw Score Distribution (H2 Validation) ---")
    for p in [0, 10, 25, 50, 75, 90, 95, 99, 100]:
        print(f"  p{p:<3}: {np.percentile(h2_scores_np, p):.4f}")

    print("\n--- Evidence Distribution (H2 Validation) ---")
    print("  (evidence = percentile rank within H1 empirical CDF)")
    for p in [0, 10, 25, 50, 75, 90, 95, 99, 100]:
        print(f"  p{p:<3}: {np.percentile(h2_evidence_np, p):.4f}")

    n_flagged = int(np.sum(h2_flags_np))
    flag_rate = n_flagged / len(h2_flags_np)
    print(f"\n--- Threshold = {calibrator.threshold_evidence} ---")
    print(f"  Flagged: {n_flagged} / {len(h2_flags_np)} ({flag_rate:.2%})")
    print(f"  Expected for normal data: ~{(1 - calibrator.threshold_evidence):.0%}")

    # --- Step 7: Score Stability Across July Halves ---
    print("\n" + "=" * 65)
    print("  SCORE STABILITY: H1 vs H2")
    print("=" * 65)

    h1_evidence = calibrator.calibrate(h1_raw_scores)
    h1_evidence_np = h1_evidence.to_numpy()

    print(f"\n  {'Metric':<20} {'H1 (Train)':<15} {'H2 (Val)':<15} {'Drift':<10}")
    print("  " + "-" * 60)
    for label, p in [("Median evidence", 50), ("p90 evidence", 90), ("p95 evidence", 95), ("p99 evidence", 99)]:
        v1 = np.percentile(h1_evidence_np, p)
        v2 = np.percentile(h2_evidence_np, p)
        drift = abs(v2 - v1)
        print(f"  {label:<20} {v1:<15.4f} {v2:<15.4f} {drift:<10.4f}")

    h1_flag_rate = np.mean(h1_evidence_np >= calibrator.threshold_evidence)
    h2_flag_rate = flag_rate
    print(f"\n  H1 flag rate: {h1_flag_rate:.2%}")
    print(f"  H2 flag rate: {h2_flag_rate:.2%}")
    print(f"  Flag rate drift: {abs(h2_flag_rate - h1_flag_rate):.2%}")

    stability_ok = abs(h2_flag_rate - h1_flag_rate) < 0.05
    if stability_ok:
        print("\n  ✅ Score mapping is STABLE across July halves (drift < 5%).")
    else:
        print("\n  ⚠️  LIMITATION: Score mapping shows notable drift between H1 and H2.")
        print("     This may indicate non-stationarity within July itself.")

    # --- Step 8: Calibrator Save/Load Round-Trip ---
    print("\n=== STEP 8: Calibrator Round-Trip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        cal_path = Path(tmpdir) / "calibration.json"
        calibrator.save(cal_path)

        loaded_cal = EmpiricalCalibrator(model_version="", threshold_evidence=0.0)
        loaded_cal.load(cal_path)

        h2_evidence_reloaded = loaded_cal.calibrate(h2_raw_scores)
        assert h2_evidence.equals(h2_evidence_reloaded), "Round-trip mismatch!"
        assert loaded_cal.model_version == "iforest-v1.0"
        assert loaded_cal.threshold_evidence == 0.95
        print("  ✅ Calibrator round-trips exactly.")

    # --- Step 9: Mathematical Meaning ---
    print("\n" + "=" * 65)
    print("  MATHEMATICAL MEANING")
    print("=" * 65)
    print("""
  evidence(s) = |{s_july : s_july <= s}| / |S_july|

  Evidence of 0.95 means:
    "This window's raw Isolation Forest score exceeds 95% of all
     July training windows' raw scores."

  It is NOT a probability of being anomalous. It is a percentile rank
  within the empirical CDF of July's own score distribution.

  The frozen threshold (0.95) means: "Flag any window whose score is
  more extreme than 95% of July." On perfectly stationary July-like data,
  this should flag approximately 5% of windows.
""")


if __name__ == "__main__":
    main()
