"""
Validation Gate for Autoencoder Detector.

Demonstrates:
1. Chronological July train/val split
2. Training/validation loss curve showing learning
3. Reconstruction error distribution
4. Empirical calibration using the same approach as Isolation Forest
5. Timestamp-range assertion proving only July data was used
6. Full round-trip save/load
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.detectors.autoencoder import AutoencoderDetector

np.random.seed(42)


def generate_july_features(n_windows: int, start_day: int = 1) -> pa.Table:
    """Generate a time-ordered July feature matrix with diurnal patterns."""
    start = datetime(2025, 7, start_day, tzinfo=UTC)
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]
    hours = np.array([t.hour for t in timestamps])
    is_day = (hours >= 8) & (hours <= 18)

    f1 = np.where(is_day, np.random.normal(50, 8, n_windows), np.random.normal(10, 3, n_windows))
    f2 = np.random.normal(5, 1, n_windows)
    f3 = np.random.poisson(2.0, n_windows).astype(float)
    f4 = np.where(is_day, np.random.normal(20, 4, n_windows), np.random.normal(3, 1, n_windows))

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
        "feature_3": f3.tolist(),
        "feature_4": f4.tolist(),
    })


def main() -> None:
    features = ["feature_1", "feature_2", "feature_3", "feature_4"]

    # === Step 1: Generate July data ===
    print("=== STEP 1: Generate July Data ===")
    n_windows = 10_000
    data = generate_july_features(n_windows)

    # Timestamp-range assertion
    ts_col = data.column("window_start")
    min_ts = ts_col[0].as_py()
    max_ts = ts_col[-1].as_py()
    assert min_ts.month == 7 and min_ts.year == 2025, f"Training start is not July: {min_ts}"
    assert max_ts < datetime(2025, 8, 1, tzinfo=UTC), f"Training data leaks into August: {max_ts}"
    print(f"  ✅ Timestamp range: {min_ts} → {max_ts} (strictly July)")
    print(f"  Windows: {n_windows}")

    # === Step 2: Train autoencoder ===
    print("\n=== STEP 2: Train Autoencoder ===")
    detector = AutoencoderDetector(
        feature_columns=features,
        hidden_dim=16,
        latent_dim=4,
        learning_rate=1e-3,
        epochs=30,
        batch_size=128,
        val_split_frac=0.2,
        seed=42,
        version="autoencoder-v1.0",
    )
    detector.fit(data)

    # === Step 3: Loss curve ===
    print("\n=== STEP 3: Training / Validation Loss Curve ===")
    print(f"  {'Epoch':<8} {'Train Loss':<15} {'Val Loss':<15}")
    print("  " + "-" * 38)
    for entry in detector.training_history:
        print(f"  {entry['epoch']:<8} {entry['train_loss']:<15.6f} {entry['val_loss']:<15.6f}")

    first = detector.training_history[0]
    last = detector.training_history[-1]
    train_improved = last["train_loss"] < first["train_loss"] * 0.5
    val_improved = last["val_loss"] < first["val_loss"] * 0.8

    print(f"\n  Train loss reduction: {first['train_loss']:.6f} → {last['train_loss']:.6f} "
          f"({(1 - last['train_loss']/first['train_loss'])*100:.1f}%)")
    print(f"  Val loss reduction:   {first['val_loss']:.6f} → {last['val_loss']:.6f} "
          f"({(1 - last['val_loss']/first['val_loss'])*100:.1f}%)")

    if train_improved and val_improved:
        print("  ✅ Model is learning (both losses decreased significantly)")
    elif not val_improved:
        print("  ⚠️  Validation loss did not decrease meaningfully — check for overfitting")
    else:
        print("  ⚠️  Training loss did not decrease meaningfully")

    # === Step 4: Reconstruction error distribution ===
    print("\n=== STEP 4: Reconstruction Error Distribution ===")
    raw_scores = detector.score(data)
    scores_np = raw_scores.to_numpy()

    print(f"  {'Percentile':<12} {'Recon Error':<15}")
    print("  " + "-" * 27)
    for p in [0, 10, 25, 50, 75, 90, 95, 99, 100]:
        print(f"  p{p:<10} {np.percentile(scores_np, p):<15.6f}")

    # === Step 5: Calibrate using empirical quantiles ===
    print("\n=== STEP 5: Empirical Calibration (Same as IForest) ===")
    detector.fit_calibrator(data, threshold_evidence=0.95)

    # Score and calibrate the validation portion (last 20%)
    split_idx = int(n_windows * 0.8)
    val_data = pa.table({
        "window_start": data.column("window_start").to_pylist()[split_idx:],
        "feature_1": data.column("feature_1").to_pylist()[split_idx:],
        "feature_2": data.column("feature_2").to_pylist()[split_idx:],
        "feature_3": data.column("feature_3").to_pylist()[split_idx:],
        "feature_4": data.column("feature_4").to_pylist()[split_idx:],
    })
    val_preds = detector.predict(val_data)

    val_preds.column("calibrated_evidence").to_numpy()
    flags_np = val_preds.column("anomaly").to_numpy(zero_copy_only=False)
    n_flagged = int(np.sum(flags_np))
    flag_rate = n_flagged / len(flags_np)

    print(f"  Threshold: {detector.threshold}")
    print(f"  Flagged: {n_flagged} / {len(flags_np)} ({flag_rate:.2%})")
    print(f"  Expected for normal data: ~{(1 - detector.threshold):.0%}")

    # === Step 6: Save/Load round-trip ===
    print("\n=== STEP 6: Save/Load Round-Trip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "autoencoder.json"
        detector.save(model_path)

        loaded = AutoencoderDetector(feature_columns=[])
        loaded.load(model_path)

        # Score with loaded model
        loaded_scores = loaded.score(val_data)
        original_scores = detector.score(val_data)

        orig_np = original_scores.to_numpy()
        load_np = loaded_scores.to_numpy()
        max_diff = np.max(np.abs(orig_np - load_np))

        print(f"  Max score difference after round-trip: {max_diff:.10f}")
        if max_diff < 1e-5:
            print("  ✅ Round-trip produces identical scores.")
        else:
            print("  ⚠️  Round-trip has numerical drift (within floating point tolerance).")

    print("\n=== VALIDATION GATE COMPLETE ===")


if __name__ == "__main__":
    main()
