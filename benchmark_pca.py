"""
Validation benchmark for PCA Reconstruction Detector.

Demonstrates:
1. Dynamic dimensionality reduction (components and explained variance).
2. Stable reconstruction error on a July validation split.
3. Comparative evaluation against Isolation Forest and Autoencoder on score
   distributions and calibrated flag rates.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.detectors.autoencoder import AutoencoderDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector


def generate_mock_features(n_windows: int, start_day: int = 1) -> pa.Table:
    """Generate a highly correlated feature matrix."""
    start = datetime(2025, 7, start_day, tzinfo=UTC)
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    # 3 latent factors
    latent1 = np.random.normal(0, 5, n_windows)
    latent2 = np.random.normal(10, 2, n_windows)
    latent3 = np.random.normal(-5, 10, n_windows)

    # 10 correlated features generated from the 3 latent factors
    f = {}
    for i in range(10):
        f[f"feature_{i}"] = (
            np.random.uniform(-1, 1) * latent1 +
            np.random.uniform(-1, 1) * latent2 +
            np.random.uniform(-1, 1) * latent3 +
            np.random.normal(0, 0.5, n_windows) # noise
        ).tolist()

    # Add timestamps
    f["window_start"] = timestamps
    return pa.table(f)


def main() -> None:
    np.random.seed(42)

    print("=== STEP 1: Generate July Data ===")
    n_train = 10000
    n_val = 2000

    # We create 10 features, but they are all driven by only 3 latent factors.
    # We expect PCA to retain around 3-4 components to capture 95% variance.
    train_data = generate_mock_features(n_train, start_day=1)
    val_data = generate_mock_features(n_val, start_day=15)

    features = [f"feature_{i}" for i in range(10)]

    print("\n=== STEP 2: Train PCA Detector ===")
    pca_detector = PCADetector(
        feature_columns=features,
        target_explained_variance=0.95,
        version="pca-v1",
    )
    pca_detector.fit(train_data)

    print("\n=== STEP 3: Validation Gate - Dimensionality & Stability ===")
    print(f"  Target Explained Variance: {pca_detector.target_explained_variance * 100:.1f}%")
    print(f"  Retained Components:       {pca_detector.n_components_}")
    print(f"  Actual Explained Variance: {pca_detector.explained_variance_ratio_ * 100:.2f}%")

    val_scores = pca_detector.score(val_data).to_numpy()

    print("\n  Reconstruction Error Distribution (Validation):")
    print(f"    p0:   {np.min(val_scores):.6f}")
    print(f"    p50:  {np.median(val_scores):.6f}")
    print(f"    p95:  {np.percentile(val_scores, 95):.6f}")
    print(f"    p100: {np.max(val_scores):.6f}")

    # Sanity check: Ensure reconstruction error doesn't blow up
    assert np.max(val_scores) < 100.0, "Pathological blow-up in reconstruction error detected!"
    print("\n  ✅ Reconstruction error is stable and well-behaved on the validation split.")

    print("\n=== STEP 4: Comparative Benchmark (PCA vs IForest vs Autoencoder) ===")

    print("\n  Training IForest...")
    iforest = IsolationForestDetector(feature_columns=features, n_jobs=1, version="if-v1")
    iforest.fit(train_data)

    print("  Training Autoencoder...")
    ae = AutoencoderDetector(
        feature_columns=features,
        hidden_dim=8,
        latent_dim=3,
        epochs=10,
        batch_size=256,
        version="ae-v1"
    )
    ae.fit(train_data)

    # Calibrate all models with 0.95 threshold evidence
    print("\n  Calibrating models (Threshold Evidence = 0.95)...")
    threshold = 0.95
    pca_detector.fit_calibrator(train_data, threshold_evidence=threshold)
    iforest.fit_calibrator(train_data, threshold_evidence=threshold)
    ae.fit_calibrator(train_data, threshold_evidence=threshold)

    # Predict on validation data
    pca_preds = pca_detector.predict(val_data)
    iforest_preds = iforest.predict(val_data)
    ae_preds = ae.predict(val_data)

    print("\n  Validation Flag Rates:")
    print("  (Expected rate for perfectly stationary normal data: ~5.00%)")
    print("  " + "-" * 50)
    models = [
        ("PCA", pca_preds),
        ("Isolation Forest", iforest_preds),
        ("Autoencoder", ae_preds),
    ]

    for name, preds in models:
        flags = preds.column("anomaly").to_numpy(zero_copy_only=False)
        flag_rate = np.mean(flags)
        print(f"  {name:<18} : {flag_rate * 100:.2f}% flagged")

    print("\n=== STEP 5: Save/Load Round-Trip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "pca.joblib"
        pca_detector.save(model_path)

        loaded = PCADetector(feature_columns=[])
        loaded.load(model_path)

        loaded_scores = loaded.score(val_data)

        max_diff = np.max(np.abs(val_scores - loaded_scores.to_numpy()))

        print(f"  Max score difference after round-trip: {max_diff:.10f}")
        assert max_diff < 1e-5, "Round-trip failed."
        print("  ✅ Round-trip successful.")


if __name__ == "__main__":
    main()
