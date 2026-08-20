"""
Validation benchmark for the August Inference Pipeline.

Demonstrates:
1. Training all detectors on July data and persisting them.
2. Loading the frozen artifacts into a read-only inference pipeline.
3. Running the validation gate on a tiny August sample (version verification).
4. Running full August inference and producing evidence for every window.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
from tabulate import tabulate

from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector

# ---------------------------------------------------------------------------
# Data generation (identical code path for July and August)
# ---------------------------------------------------------------------------

def generate_features(
    n_windows: int,
    start: datetime,
) -> pa.Table:
    """
    Generate feature windows.  This function is called for BOTH July and
    August data — guaranteeing the feature-computation code path is
    identical.
    """
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    f1 = np.random.normal(50, 10, n_windows)
    f2 = np.random.exponential(scale=5, size=n_windows)
    f3 = np.random.poisson(lam=3, size=n_windows).astype(float)
    f4 = np.random.normal(0, 5, n_windows)

    users = ["alice", "bob", "charlie", "david", "eve"]
    hosts = ["host-A", "host-B", "host-C"]

    u_col = np.random.choice(users, size=n_windows, p=[0.4, 0.3, 0.15, 0.1, 0.05])
    h_col = np.random.choice(hosts, size=n_windows, p=[0.6, 0.3, 0.1])

    return pa.table({
        "window_start": timestamps,
        "feature_1": f1.tolist(),
        "feature_2": f2.tolist(),
        "feature_3": f3.tolist(),
        "feature_4": f4.tolist(),
        "user": u_col.tolist(),
        "host": h_col.tolist(),
    })


def main() -> None:
    np.random.seed(42)

    cont_features = ["feature_1", "feature_2", "feature_3", "feature_4"]
    cat_features = ["user", "host"]

    # ------------------------------------------------------------------
    # PHASE A: Train on July and persist frozen artifacts
    # ------------------------------------------------------------------
    print("=== PHASE A: Train on July ===")

    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_features(10000, start=july_start)

    detectors_to_train = {
        "IForest": IsolationForestDetector(
            feature_columns=cont_features, n_jobs=1, version="if-v1"
        ),
        "PCA": PCADetector(
            feature_columns=cont_features,
            target_explained_variance=0.95,
            version="pca-v1",
        ),
        "Statistical": RobustStatisticalDetector(
            feature_columns=cont_features, version="stat-v1"
        ),
        "Rarity": RarityDetector(
            feature_columns=cat_features, version="rarity-v1"
        ),
    }

    with tempfile.TemporaryDirectory() as artifact_dir:
        artifact_path = Path(artifact_dir)

        for name, det in detectors_to_train.items():
            print(f"  Training {name}...")
            det.fit(july_data)
            det.fit_calibrator(july_data, threshold_evidence=0.95)

            # Choose extension based on detector type
            ext = ".joblib" if hasattr(det, "_pca") else ".json"
            det.save(artifact_path / f"{name}{ext}")

        print(f"\n  Saved {len(detectors_to_train)} frozen July artifacts to {artifact_path}")

        # ------------------------------------------------------------------
        # PHASE B: Load frozen artifacts into read-only pipeline
        # ------------------------------------------------------------------
        print("\n=== PHASE B: Load Frozen Artifacts ===")

        loaded_detectors = {
            "IForest": IsolationForestDetector(feature_columns=[]),
            "PCA": PCADetector(feature_columns=[]),
            "Statistical": RobustStatisticalDetector(feature_columns=[]),
            "Rarity": RarityDetector(feature_columns=[]),
        }

        for name, det in loaded_detectors.items():
            ext = ".joblib" if hasattr(det, "_pca") else ".json"
            det.load(artifact_path / f"{name}{ext}")
            print(f"  Loaded {name} (version={det.version})")

        pipeline = AugustInferencePipeline(
            detectors=loaded_detectors,
            pipeline_version="aug-inference-v1",
            ensemble_strategy="max",
        )

        # ------------------------------------------------------------------
        # PHASE C: Validation Gate — tiny August sample
        # ------------------------------------------------------------------
        print("\n=== PHASE C: Validation Gate (Tiny August Sample) ===")

        august_sample_start = datetime(2025, 8, 1, tzinfo=UTC)
        august_sample = generate_features(10, start=august_sample_start)

        expected_versions = {
            "IForest": "if-v1",
            "PCA": "pca-v1",
            "Statistical": "stat-v1",
            "Rarity": "rarity-v1",
        }

        import logging
        logging.basicConfig(level=logging.INFO, format="  %(message)s")

        sample_results = pipeline.run_sample_verification(
            august_sample, expected_versions
        )

        print("\n  Sample results (10 windows):")
        table_rows = []
        headers = ["Win", "IForest", "PCA", "Stat", "Rarity", "Ensemble", "Flag", "Agree", "Disagg", "Top", "Category"]

        # Sort by ensemble evidence to clearly show a high and low evidence window
        ens_ev_col = sample_results.column("ensemble_evidence").to_numpy()
        sorted_indices = np.argsort(ens_ev_col)[::-1] # descending

        # We will show the highest evidence window, the lowest evidence window, and maybe one more.
        indices_to_show = [sorted_indices[0], sorted_indices[-1]]

        for i in indices_to_show:
            row = [
                i,
                f"{sample_results.column('evidence_IForest').to_numpy()[i]:.3f}",
                f"{sample_results.column('evidence_PCA').to_numpy()[i]:.3f}",
                f"{sample_results.column('evidence_Statistical').to_numpy()[i]:.3f}",
                f"{sample_results.column('evidence_Rarity').to_numpy()[i]:.3f}",
                f"{sample_results.column('ensemble_evidence').to_numpy()[i]:.3f}",
                sample_results.column("ensemble_flagged").to_numpy(zero_copy_only=False)[i],
                sample_results.column("detector_agreement").to_numpy()[i],
                f"{sample_results.column('detector_disagreement').to_numpy()[i]:.3f}",
                sample_results.column("top_detector").to_pylist()[i],
                sample_results.column("primary_category").to_pylist()[i],
            ]
            table_rows.append(row)

        print(tabulate(table_rows, headers=headers, tablefmt="github"))

        # ------------------------------------------------------------------
        # PHASE D: Full August inference
        # ------------------------------------------------------------------
        print("\n=== PHASE D: Full August Inference ===")

        august_start = datetime(2025, 8, 1, tzinfo=UTC)
        august_data = generate_features(5000, start=august_start)

        full_results = pipeline.score_all(august_data)

        print(f"\n  Total August windows scored: {len(august_data)}")

        ens_ev = full_results.column("ensemble_evidence").to_numpy()
        ens_flags = full_results.column("ensemble_flagged").to_numpy(zero_copy_only=False)

        print(f"  Ensemble evidence range: [{np.min(ens_ev):.4f}, {np.max(ens_ev):.4f}]")
        print(f"  Ensemble mean evidence:  {np.mean(ens_ev):.4f}")
        print(f"  Flagged windows:         {int(np.sum(ens_flags))} / {len(ens_flags)}"
              f" ({np.mean(ens_flags) * 100:.2f}%)")

        # Per-detector stats
        print("\n  Per-detector August evidence summary:")
        det_rows = []
        for name in loaded_detectors:
            ev = full_results.column(f"evidence_{name}").to_numpy()
            det_rows.append([
                name,
                f"{np.min(ev):.4f}",
                f"{np.median(ev):.4f}",
                f"{np.mean(ev):.4f}",
                f"{np.percentile(ev, 95):.4f}",
                f"{np.max(ev):.4f}",
            ])
        print(tabulate(det_rows, headers=["Detector", "Min", "Median", "Mean", "P95", "Max"],
                        tablefmt="github"))

        # Save manifest
        pipeline.save_manifest(artifact_path / "manifest.json")
        print("\n  Pipeline manifest saved.")

        print("\n✅ August inference pipeline validation complete.")


if __name__ == "__main__":
    main()
