"""
Validation benchmark for RarityDetector.

Demonstrates:
1. Rarity training on categorical July relationships.
2. An unseen relationship produces elevated rarity evidence.
3. A previously seen relationship produces low rarity evidence.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from tads.models.detectors.rarity import RarityDetector


def generate_mock_categorical_features(n_windows: int, start_day: int = 1) -> pa.Table:
    """Generate mock categorical relationship matrix."""
    start = datetime(2025, 7, start_day, tzinfo=UTC)
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    # User-Host relationships
    # We define 5 common pairs
    common_pairs = [
        ("alice", "host-A"),
        ("bob", "host-B"),
        ("charlie", "host-C"),
        ("alice", "host-B"),
        ("david", "host-D"),
    ]

    # Randomly assign pairs to windows
    indices = np.random.choice(len(common_pairs), size=n_windows)

    users = [common_pairs[i][0] for i in indices]
    hosts = [common_pairs[i][1] for i in indices]

    # Process commands (mostly "cmd.exe" and "powershell.exe")
    cmds = np.random.choice(["cmd.exe", "powershell.exe"], size=n_windows, p=[0.8, 0.2])

    return pa.table({
        "window_start": timestamps,
        "user": users,
        "host": hosts,
        "command": cmds.tolist(),
    })


def main() -> None:
    np.random.seed(42)

    print("=== STEP 1: Generate July Categorical Data ===")
    n_train = 10000
    n_val = 10

    train_data = generate_mock_categorical_features(n_train, start_day=1)
    val_data = generate_mock_categorical_features(n_val, start_day=15)

    features = ["user", "host", "command"]

    print("\n=== STEP 2: Train RarityDetector ===")
    detector = RarityDetector(feature_columns=features, version="rarity-v1")
    detector.fit(train_data)

    print("\n=== STEP 3: Calibration ===")
    detector.fit_calibrator(train_data, threshold_evidence=0.99)

    print("\n=== STEP 4: Validation Gate - Rarity Evidence ===")

    # Target window 5 for a completely novel relationship
    target_idx = 5

    val_user = val_data.column("user").to_pylist()
    val_host = val_data.column("host").to_pylist()
    val_cmd = val_data.column("command").to_pylist()

    # Inject a novel user-host pair in window 5
    val_user[target_idx] = "eve"
    val_host[target_idx] = "host-UNKNOWN"
    val_cmd[target_idx] = "mimikatz.exe"

    injected_data = pa.table({
        "window_start": val_data.column("window_start"),
        "user": val_user,
        "host": val_host,
        "command": val_cmd,
    })

    preds = detector.predict(injected_data)
    explanations = detector.explain(injected_data)

    flags = preds.column("anomaly").to_numpy(zero_copy_only=False)
    scores = preds.column("raw_score").to_numpy()
    evidence = preds.column("calibrated_evidence").to_numpy()

    for i in range(len(injected_data)):
        print(f"Window {i}:")
        print(f"  User: {val_user[i]}, Host: {val_host[i]}, Command: {val_cmd[i]}")
        print(f"  Raw Score (Surprisal): {scores[i]:.2f}")
        print(f"  Evidence: {evidence[i]:.4f}")
        print(f"  Flagged: {flags[i]}")
        print(f"  Explanation: {explanations[i].as_py()}")
        print("-" * 40)

    print("\nVerifying injection...")
    assert flags[target_idx], "Novel relationship was not flagged!"
    assert "UNSEEN" in explanations[target_idx].as_py(), "Explanation did not identify the relationship as UNSEEN!"
    assert not flags[0], "Previously seen relationship should NOT be flagged!"

    print("✅ Validation Gate Passed: The unseen relationship produced elevated rarity evidence, "
          "while the seen relationship produced low rarity evidence.")

    print("\n=== STEP 5: Save/Load Round-Trip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "rarity.json"
        detector.save(model_path)

        loaded = RarityDetector(feature_columns=[])
        loaded.load(model_path)

        loaded_scores = loaded.score(injected_data)

        max_diff = np.max(np.abs(scores - loaded_scores.to_numpy()))

        print(f"  Max score difference after round-trip: {max_diff:.10f}")
        assert max_diff < 1e-5, "Round-trip failed."
        print("  ✅ Round-trip successful.")


if __name__ == "__main__":
    main()
