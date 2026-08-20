"""
Validation benchmark for SequenceLSTMDetector.

Demonstrates:
1. Causal no-leakage property: changing future data does not affect past predictions.
2. Minimal baseline comparison: compares MSE of LSTM prediction vs a naive "predict the mean" baseline.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from tads.models.detectors.sequence_lstm import SequenceLSTMDetector


def generate_mock_sequence_features(n_windows: int, start_day: int = 1) -> pa.Table:
    """Generate a time-ordered feature matrix."""
    # We will generate a simple sine wave + noise for one feature to make it predictable
    # by a sequence model, and a random walk for another.
    start = datetime(2025, 7, start_day, tzinfo=UTC)
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    t = np.arange(n_windows)

    # Feature 1: Predictable sine wave (period = 100 windows)
    f1 = 10 * np.sin(2 * np.pi * t / 100) + np.random.normal(0, 0.5, n_windows)

    # Feature 2: Autoregressive AR(1) process (predictable from previous step)
    f2 = np.zeros(n_windows)
    for i in range(1, n_windows):
        f2[i] = 0.8 * f2[i-1] + np.random.normal(0, 1.0)

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
    })


def main() -> None:
    # Deterministic execution
    np.random.seed(42)
    torch.manual_seed(42)

    print("=== STEP 1: Generate July Sequence Data ===")
    n_train = 5000
    n_val = 1000

    train_data = generate_mock_sequence_features(n_train, start_day=1)
    val_data = generate_mock_sequence_features(n_val, start_day=15)

    features = ["feature_1", "feature_2"]

    print("\n=== STEP 2: Train SequenceLSTMDetector ===")
    detector = SequenceLSTMDetector(
        feature_columns=features,
        seq_len=20,
        hidden_dim=16,
        num_layers=1,
        epochs=15,          # Lower epochs for benchmark speed
        batch_size=128,
        learning_rate=0.01,
        version="lstm-v1",
    )

    detector.fit(train_data)

    print("\n=== STEP 3: Baseline Comparison (LSTM vs Predict-Mean) ===")
    # Evaluate on validation data
    lstm_scores_pa = detector.score_batched(val_data)
    lstm_scores = lstm_scores_pa.to_numpy()

    # Exclude the first `seq_len` windows which don't have full context
    valid_idx = detector.seq_len
    lstm_mse = np.mean(lstm_scores[valid_idx:])

    # Baseline: Naive predict-the-mean (using July training means)
    train_f1 = train_data.column("feature_1").to_numpy()
    train_f2 = train_data.column("feature_2").to_numpy()
    np.mean(train_f1)
    np.mean(train_f2)

    val_f1 = val_data.column("feature_1").to_numpy()
    val_f2 = val_data.column("feature_2").to_numpy()

    # We standardize the validation data using the detector's standardizer to compare apples to apples
    val_raw = np.column_stack([val_f1, val_f2])
    val_std = detector._standardize(val_raw, fit=False)

    # Mean in standardized space is 0 (since it was standardized to mean=0)
    naive_mse_per_window = np.mean((val_std - 0.0)**2, axis=1)
    naive_mse = np.mean(naive_mse_per_window[valid_idx:])

    print(f"  Naive Predict-Mean MSE: {naive_mse:.4f}")
    print(f"  LSTM Prediction MSE:    {lstm_mse:.4f}")

    if lstm_mse < naive_mse:
        print("  ✅ Sequence model successfully learned temporal transitions and outperformed the naive baseline.")
    else:
        print("  ⚠️ Sequence model did not outperform naive baseline.")


    print("\n=== STEP 4: Validation Gate - Causal No-Leakage Property ===")

    # To prove no leakage, we will take a validation sequence, score it.
    # Then we will corrupt data at position t+1, and assert that the score at position t is IDENTICAL.

    original_scores = detector.score(val_data).to_numpy()

    # Let's target position t = 500
    t = 500
    # Copy val_data
    corrupt_f1 = val_f1.copy()
    corrupt_f2 = val_f2.copy()

    # Corrupt data at t+1 (the future relative to t)
    corrupt_f1[t+1] = 999999.0
    corrupt_f2[t+1] = -999999.0

    corrupt_data = pa.table({
        "window_start": val_data.column("window_start"),
        "feature_1": corrupt_f1.tolist(),
        "feature_2": corrupt_f2.tolist(),
    })

    corrupt_scores = detector.score(corrupt_data).to_numpy()

    # The score at position t represents the prediction error for window t
    # (predicted from context [t-seq_len : t-1]).
    # In score(), score for window t is the MSE between model's prediction
    # given context before t, and actual window t.
    # If we corrupt data at t+1, the score at t should remain identical,
    # because predicting window t uses windows < t, and the target is t.
    # t+1 is not involved.
    score_t_orig = original_scores[t]
    score_t_corr = corrupt_scores[t]

    # The score at t+1 will obviously change because the target at t+1 changed.
    score_t1_orig = original_scores[t+1]
    score_t1_corr = corrupt_scores[t+1]

    print(f"  Original score at t={t}: {score_t_orig:.8f}")
    print(f"  Corrupted score at t={t}: {score_t_corr:.8f}")

    assert np.isclose(score_t_orig, score_t_corr, atol=1e-7), "Temporal leakage detected! Future data affected past prediction."

    print(f"  Original score at t={t+1}: {score_t1_orig:.8f}")
    print(f"  Corrupted score at t={t+1}: {score_t1_corr:.8f}")
    assert not np.isclose(score_t1_orig, score_t1_corr, atol=1e-7), "Score at t+1 should change!"

    print("  ✅ Causal no-leakage property successfully demonstrated.")


    print("\n=== STEP 5: Calibrate & Save/Load ===")
    detector.fit_calibrator(train_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "lstm.json"
        detector.save(model_path)

        loaded = SequenceLSTMDetector(feature_columns=[])
        loaded.load(model_path)

        loaded_scores = loaded.score(val_data)

        orig_np = original_scores
        load_np = loaded_scores.to_numpy()
        max_diff = np.max(np.abs(orig_np - load_np))

        print(f"  Max score difference after round-trip: {max_diff:.10f}")
        assert max_diff < 1e-5, "Round-trip failed."
        print("  ✅ Round-trip successful.")


if __name__ == "__main__":
    main()
