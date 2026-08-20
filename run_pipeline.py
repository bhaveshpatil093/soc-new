#!/usr/bin/env python3
"""
TADS — Full Pipeline Orchestrator
==================================
Single entry-point that runs the entire July→August experiment end-to-end
against a REAL Elasticsearch cluster.

Usage:
    python run_pipeline.py                         # defaults (see below)
    python run_pipeline.py --index "logs-*"        # custom index pattern
    python run_pipeline.py --skip-ingest           # skip ES extraction (re-use existing Parquet)
    python run_pipeline.py --skip-training         # skip model training (re-use saved models)

Prerequisites:
    1. A valid .env file with ELASTIC_HOST, ELASTIC_USERNAME, ELASTIC_PASSWORD
    2. pip install -e .  (or the project's venv activated)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# ── Ensure project root on sys.path ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
RESULTS_DIR = ARTIFACTS_DIR


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def banner(msg: str) -> None:
    width = max(len(msg) + 4, 60)
    print("\n" + "=" * width)
    print(f"  {msg}")
    print("=" * width + "\n")


def run_cli(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a tads CLI command via the installed entry-point or python -m."""
    cmd = [sys.executable, "-m", "tads.cli.main"] + args
    print(f"  → {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=check)


def step_timer(label: str):
    """Context manager that prints elapsed time for a step."""
    class _Timer:
        def __enter__(self):
            self.t0 = time.time()
            return self
        def __exit__(self, *exc):
            elapsed = time.time() - self.t0
            print(f"  ✓ {label} completed in {elapsed:.1f}s\n")
    return _Timer()


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 1: Ingest from Elasticsearch
# ═══════════════════════════════════════════════════════════════════════════

def stage_ingest(index: str, batch_size: int) -> None:
    banner("STAGE 1: Ingesting from Elasticsearch")

    # July
    print("[1a] Extracting July data...")
    with step_timer("July ingestion"):
        run_cli([
            "ingest", "run",
            "--dataset", "july",
            "--index", index,
            "--start", "2025-07-01T00:00:00Z",
            "--end",   "2025-08-01T00:00:00Z",
            "--batch-size", str(batch_size),
            "--run-id", "july_full",
            "--dedup",
        ])

    # August
    print("[1b] Extracting August data...")
    with step_timer("August ingestion"):
        run_cli([
            "ingest", "run",
            "--dataset", "august",
            "--index", index,
            "--start", "2025-08-01T00:00:00Z",
            "--end",   "2025-09-01T00:00:00Z",
            "--batch-size", str(batch_size),
            "--run-id", "august_full",
            "--dedup",
        ])


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 2: Windowing & Feature Engineering
# ═══════════════════════════════════════════════════════════════════════════

def stage_windowing() -> None:
    banner("STAGE 2: Temporal Windowing")

    for dataset in ("july", "august"):
        print(f"[2a] Building window index for {dataset.upper()}...")
        with step_timer(f"{dataset} window index"):
            run_cli(["window", "index", "--dataset", dataset])

        print(f"[2b] Building window dataset for {dataset.upper()}...")
        with step_timer(f"{dataset} window dataset"):
            run_cli(["window", "build", "--dataset", dataset])


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 3: Dataset Profiling
# ═══════════════════════════════════════════════════════════════════════════

def stage_profiling() -> None:
    banner("STAGE 3: Dataset Profiling")

    for dataset, run_id in [("july", "july_full"), ("august", "august_full")]:
        print(f"Profiling {dataset.upper()}...")
        with step_timer(f"{dataset} profiling"):
            run_cli(["profile", "run", "--dataset", dataset, "--run-id", run_id], check=False)


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 4: Model Training (July only)
# ═══════════════════════════════════════════════════════════════════════════

def stage_training() -> None:
    banner("STAGE 4: Training Anomaly Detectors on July Baseline")

    import torch
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq

    np.random.seed(42)
    torch.manual_seed(42)

    from tads.models.detectors.isolation_forest import IsolationForestDetector
    from tads.models.detectors.pca import PCADetector
    from tads.models.detectors.statistical import RobustStatisticalDetector
    from tads.models.detectors.rarity import RarityDetector
    from tads.models.detectors.autoencoder import AutoencoderDetector
    from tads.models.detectors.sequence_lstm import SequenceLSTMDetector

    # Load July window dataset
    july_windows_path = PROJECT_ROOT / "data" / "july" / "windows" / "window_dataset.parquet"
    if not july_windows_path.exists():
        print(f"  ERROR: July window dataset not found at {july_windows_path}")
        print("  Make sure Stage 2 (Windowing) completed successfully.")
        sys.exit(1)

    print(f"  Loading July windows from {july_windows_path}...")
    july_data = pq.read_table(july_windows_path)
    print(f"  Loaded {len(july_data)} windows.")

    # Discover numeric columns (excluding timestamp cols) for continuous features
    numeric_cols = []
    cat_cols = []
    for field in july_data.schema:
        if field.name in ("window_start", "window_end"):
            continue
        if pa.types.is_floating(field.type) or pa.types.is_integer(field.type):
            numeric_cols.append(field.name)
        elif pa.types.is_string(field.type) or pa.types.is_large_string(field.type):
            cat_cols.append(field.name)

    print(f"  Continuous features ({len(numeric_cols)}): {numeric_cols[:10]}{'...' if len(numeric_cols) > 10 else ''}")
    print(f"  Categorical features ({len(cat_cols)}): {cat_cols[:10]}{'...' if len(cat_cols) > 10 else ''}")

    if not numeric_cols:
        print("  WARNING: No numeric columns found. Skipping continuous-feature detectors.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    detectors = {}

    if numeric_cols:
        detectors["IsolationForest"] = IsolationForestDetector(
            feature_columns=numeric_cols, n_jobs=1, version="1.0"
        )
        detectors["PCA"] = PCADetector(
            feature_columns=numeric_cols, target_explained_variance=0.95, version="1.0"
        )
        detectors["Statistical"] = RobustStatisticalDetector(
            feature_columns=numeric_cols, version="1.0"
        )
        detectors["Autoencoder"] = AutoencoderDetector(
            feature_columns=numeric_cols, hidden_dim=32, latent_dim=8,
            epochs=10, batch_size=256, version="1.0"
        )
        detectors["LSTM"] = SequenceLSTMDetector(
            feature_columns=numeric_cols, seq_len=10, hidden_dim=32,
            num_layers=1, epochs=5, batch_size=128, version="1.0"
        )
    if cat_cols:
        detectors["Rarity"] = RarityDetector(
            feature_columns=cat_cols, version="1.0"
        )

    for name, det in detectors.items():
        print(f"  Training {name}...")
        with step_timer(f"{name} training"):
            det.fit(july_data)
            det.fit_calibrator(july_data, threshold_evidence=0.95)
            model_path = MODELS_DIR / f"{name.lower()}.json"
            det.save(model_path)
            print(f"    Saved → {model_path}")

    # Save metadata for later stages
    meta = {
        "numeric_features": numeric_cols,
        "categorical_features": cat_cols,
        "detectors": list(detectors.keys()),
        "trained_at": datetime.now(UTC).isoformat(),
    }
    meta_path = MODELS_DIR / "training_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Training metadata → {meta_path}")


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 5: August Inference
# ═══════════════════════════════════════════════════════════════════════════

def stage_inference() -> None:
    banner("STAGE 5: August Inference")

    import torch
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq

    np.random.seed(42)
    torch.manual_seed(42)

    from tads.models.detectors.isolation_forest import IsolationForestDetector
    from tads.models.detectors.pca import PCADetector
    from tads.models.detectors.statistical import RobustStatisticalDetector
    from tads.models.detectors.rarity import RarityDetector
    from tads.models.detectors.autoencoder import AutoencoderDetector
    from tads.models.detectors.sequence_lstm import SequenceLSTMDetector
    from tads.inference.pipeline import AugustInferencePipeline

    # Load training metadata
    meta_path = MODELS_DIR / "training_meta.json"
    with open(meta_path) as f:
        meta = json.load(f)

    numeric_cols = meta["numeric_features"]
    cat_cols = meta["categorical_features"]

    # Reconstruct detectors and load saved state
    detectors = {}
    detector_classes = {
        "IsolationForest": lambda: IsolationForestDetector(feature_columns=numeric_cols, n_jobs=1, version="1.0"),
        "PCA": lambda: PCADetector(feature_columns=numeric_cols, target_explained_variance=0.95, version="1.0"),
        "Statistical": lambda: RobustStatisticalDetector(feature_columns=numeric_cols, version="1.0"),
        "Autoencoder": lambda: AutoencoderDetector(feature_columns=numeric_cols, hidden_dim=32, latent_dim=8, epochs=10, batch_size=256, version="1.0"),
        "LSTM": lambda: SequenceLSTMDetector(feature_columns=numeric_cols, seq_len=10, hidden_dim=32, num_layers=1, epochs=5, batch_size=128, version="1.0"),
        "Rarity": lambda: RarityDetector(feature_columns=cat_cols, version="1.0"),
    }

    for name in meta["detectors"]:
        model_path = MODELS_DIR / f"{name.lower()}.json"
        print(f"  Loading {name} from {model_path}...")
        det = detector_classes[name]()
        det.load(model_path)
        detectors[name] = det

    # Load August window dataset
    aug_windows_path = PROJECT_ROOT / "data" / "august" / "windows" / "window_dataset.parquet"
    if not aug_windows_path.exists():
        print(f"  ERROR: August window dataset not found at {aug_windows_path}")
        sys.exit(1)

    august_data = pq.read_table(aug_windows_path)
    print(f"  Loaded {len(august_data)} August windows.")

    # Run inference
    print("  Scoring all August windows...")
    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")

    with step_timer("August inference"):
        results = pipeline.score_all(august_data)

    # Save results
    results_path = RESULTS_DIR / "august_scored_windows.parquet"
    pq.write_table(results, results_path)
    print(f"  Scored results → {results_path}")

    # Also save July medians for the report stage
    july_windows_path = PROJECT_ROOT / "data" / "july" / "windows" / "window_dataset.parquet"
    july_data = pq.read_table(july_windows_path)

    july_medians = {}
    for col in numeric_cols:
        arr = july_data.column(col).to_numpy()
        arr = arr[~np.isnan(arr)]  # drop NaNs
        if len(arr) > 0:
            july_medians[col] = float(np.median(arr))

    with open(RESULTS_DIR / "july_medians.json", "w") as f:
        json.dump(july_medians, f, indent=2)
    print(f"  July medians → {RESULTS_DIR / 'july_medians.json'}")


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 6: Generate Top-100 Report
# ═══════════════════════════════════════════════════════════════════════════

def stage_report() -> None:
    banner("STAGE 6: Generating Top-100 Anomaly Report")

    import numpy as np
    import pyarrow.parquet as pq

    # Load scored results
    scored_path = RESULTS_DIR / "august_scored_windows.parquet"
    if not scored_path.exists():
        print(f"  ERROR: Scored results not found at {scored_path}")
        sys.exit(1)

    results = pq.read_table(scored_path)
    print(f"  Loaded {len(results)} scored windows.")

    # Load July medians
    medians_path = RESULTS_DIR / "july_medians.json"
    july_medians = {}
    if medians_path.exists():
        with open(medians_path) as f:
            july_medians = json.load(f)

    # Load training meta for feature lists
    meta_path = MODELS_DIR / "training_meta.json"
    with open(meta_path) as f:
        meta = json.load(f)

    # Load August window dataset for raw feature values
    aug_windows_path = PROJECT_ROOT / "data" / "august" / "windows" / "window_dataset.parquet"
    august_data = pq.read_table(aug_windows_path)

    # Extract top 100 by ensemble_evidence
    ens_ev = results.column("ensemble_evidence").to_numpy()
    threshold = 0.50  # lower threshold to ensure we get up to 100 real candidates
    valid_indices = np.where(ens_ev >= threshold)[0]

    if len(valid_indices) == 0:
        print("  WARNING: No anomalies found above threshold. Lowering to 0.0.")
        valid_indices = np.argsort(ens_ev)[::-1][:100]
    else:
        sorted_local = np.argsort(ens_ev[valid_indices])[::-1]
        valid_indices = valid_indices[sorted_local][:100]

    print(f"  Found {len(valid_indices)} qualifying candidates.")

    report_data = []
    numeric_cols = meta["numeric_features"]
    cat_cols = meta["categorical_features"]
    detector_names = meta["detectors"]

    for rank, idx in enumerate(valid_indices, 1):
        idx = int(idx)
        timestamp = august_data.column("window_start")[idx].as_py()
        evidence = float(ens_ev[idx])

        # Category
        category = "unknown"
        try:
            category = results.column("primary_category")[idx].as_py()
        except Exception:
            pass

        # Top detector
        top_detector = "unknown"
        try:
            top_detector = results.column("top_detector")[idx].as_py()
        except Exception:
            pass

        # Detector agreement
        agreed = []
        for name in detector_names:
            try:
                det_ev = results.column(f"evidence_{name}")[idx].as_py()
                if det_ev >= 0.90:
                    agreed.append(name)
            except Exception:
                pass

        # Top anomalous features
        top_features = ""
        try:
            top_features = results.column("explanation")[idx].as_py()
        except Exception:
            pass

        # July comparison
        july_comp = {}
        for feat in numeric_cols[:10]:  # cap at 10 features for readability
            try:
                val = float(august_data.column(feat)[idx].as_py())
                median = july_medians.get(feat, 0.0)
                ratio = val / median if median != 0 else 0.0
                july_comp[feat] = {"val": val, "median": median, "ratio": ratio}
            except Exception:
                pass

        # Affected entities
        entities = {}
        for col in cat_cols[:5]:
            try:
                entities[col] = august_data.column(col)[idx].as_py()
            except Exception:
                pass

        # Novel relationships
        novel = []
        try:
            rarity_ev = results.column("evidence_Rarity")[idx].as_py()
            if rarity_ev >= 0.95:
                parts = [f"{k}={v}" for k, v in entities.items()]
                novel.append(" | ".join(parts))
        except Exception:
            pass

        # Related events
        related_events = 0
        try:
            related_events = int(august_data.column("event_count")[idx].as_py())
        except Exception:
            pass

        row = {
            "rank": rank,
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
            "duration": "5s",
            "ensemble_evidence": evidence,
            "category": category or "unknown",
            "top_detector": top_detector or "unknown",
            "detector_agreement": agreed,
            "top_anomalous_features": top_features or "",
            "july_comparison": july_comp,
            "novel_relationships": novel,
            "affected_entities": entities,
            "related_events": related_events,
            "model_only_status": category in ("behavioural_anomaly", "statistical_anomaly"),
            "analyst_status": "Pending",
        }
        report_data.append(row)

    # ── Export JSON ──
    json_path = RESULTS_DIR / "top100_report.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"  JSON  → {json_path}")

    # ── Export Parquet ──
    import pyarrow as pa

    pq_data = []
    for row in report_data:
        flat = row.copy()
        flat["detector_agreement"] = json.dumps(row["detector_agreement"])
        flat["july_comparison"] = json.dumps(row["july_comparison"])
        flat["novel_relationships"] = json.dumps(row["novel_relationships"])
        flat["affected_entities"] = json.dumps(row["affected_entities"])
        pq_data.append(flat)

    pq_table = pa.Table.from_pylist(pq_data)
    parquet_path = RESULTS_DIR / "top100_report.parquet"
    pq.write_table(pq_table, parquet_path)
    print(f"  Parquet → {parquet_path}")

    # ── Export Markdown ──
    md_path = RESULTS_DIR / "top100_report.md"
    with open(md_path, "w") as f:
        f.write("# Top-100 August Anomalies Report\n\n")
        f.write(f"*Generated on {datetime.now(UTC).isoformat()}*\n\n")

        for row in report_data:
            f.write(f"## [{row['rank']}] {row['timestamp']}\n")
            f.write(f"- **Evidence:** {row['ensemble_evidence']:.4f}\n")
            f.write(f"- **Category:** {row['category']}\n")
            f.write(f"- **Duration:** {row['duration']}\n")
            f.write(f"- **Events:** {row['related_events']}\n")
            f.write(f"- **Model-Only:** {row['model_only_status']}\n")
            f.write(f"- **Analyst Status:** {row['analyst_status']}\n\n")

            f.write("### Detectors Agreed\n")
            f.write(f"{', '.join(row['detector_agreement']) or 'None'}\n\n")

            if row['top_anomalous_features']:
                f.write(f"### Explanation\n{row['top_anomalous_features']}\n\n")

            if row['novel_relationships']:
                f.write("### Novel Relationships\n")
                for nr in row['novel_relationships']:
                    f.write(f"- {nr}\n")
                f.write("\n")

            if row['affected_entities']:
                f.write("### Affected Entities\n")
                for k, v in row['affected_entities'].items():
                    f.write(f"- **{k}:** {v}\n")
                f.write("\n")

            if row['july_comparison']:
                f.write("### July Baseline Comparison\n")
                f.write("| Feature | Value | July Median | Ratio |\n")
                f.write("|---------|-------|-------------|-------|\n")
                for feat, comp in row['july_comparison'].items():
                    f.write(f"| {feat} | {comp['val']:.2f} | {comp['median']:.2f} | {comp['ratio']:.2f}x |\n")
                f.write("\n")

            f.write("---\n\n")

    print(f"  Markdown → {md_path}")


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 7: Generate Experiment Results Package
# ═══════════════════════════════════════════════════════════════════════════

def stage_experiment_package() -> None:
    banner("STAGE 7: Generating Experiment Results Package")

    with step_timer("Experiment package"):
        subprocess.run(
            [sys.executable, "generate_experiment_package.py"],
            cwd=str(PROJECT_ROOT), check=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 8: Launch Dashboard
# ═══════════════════════════════════════════════════════════════════════════

def stage_dashboard() -> None:
    banner("STAGE 8: Launching Investigation Dashboard")
    print("  Starting Streamlit at http://localhost:8501 ...")
    print("  Press Ctrl+C to stop.\n")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
         "--server.headless", "true", "--server.port", "8501"],
        cwd=str(PROJECT_ROOT),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="TADS — Run the full July→August anomaly detection pipeline"
    )
    parser.add_argument("--index", default="logs-*",
                        help="Elasticsearch index/data-stream pattern (default: logs-*)")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="ES scroll batch size (default: 5000)")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="Skip ES ingestion (re-use existing Parquet)")
    parser.add_argument("--skip-training", action="store_true",
                        help="Skip model training (re-use saved models)")
    parser.add_argument("--skip-dashboard", action="store_true",
                        help="Skip launching the Streamlit dashboard")
    args = parser.parse_args()

    overall_start = time.time()

    print("\n" + "█" * 60)
    print("  TADS — Temporal Anomaly Detection System")
    print("  Full Pipeline Orchestrator")
    print("█" * 60)

    # Stage 1: Ingest
    if not args.skip_ingest:
        stage_ingest(args.index, args.batch_size)
    else:
        print("\n⏭️  Skipping Stage 1 (Ingestion) — using existing Parquet data.")

    # Stage 2: Windowing
    if not args.skip_ingest:
        stage_windowing()
    else:
        print("⏭️  Skipping Stage 2 (Windowing) — using existing window datasets.")

    # Stage 3: Profiling
    if not args.skip_ingest:
        stage_profiling()
    else:
        print("⏭️  Skipping Stage 3 (Profiling).")

    # Stage 4: Training
    if not args.skip_training:
        stage_training()
    else:
        print("⏭️  Skipping Stage 4 (Training) — using saved model artifacts.")

    # Stage 5: Inference
    stage_inference()

    # Stage 6: Report
    stage_report()

    # Stage 7: Experiment package
    stage_experiment_package()

    # Summary
    total = time.time() - overall_start
    banner(f"PIPELINE COMPLETE — Total time: {total:.1f}s")

    # Stage 8: Dashboard
    if not args.skip_dashboard:
        stage_dashboard()
    else:
        print("⏭️  Skipping Stage 8 (Dashboard). Run manually:")
        print("    streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
