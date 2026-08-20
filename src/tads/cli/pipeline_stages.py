import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import click
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch

from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.autoencoder import AutoencoderDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.sequence_lstm import SequenceLSTMDetector
from tads.models.detectors.statistical import RobustStatisticalDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
RESULTS_DIR = ARTIFACTS_DIR


@click.group(name="pipeline")
def pipeline_group() -> None:
    """Pipeline stages for orchestrator."""
    pass


@pipeline_group.command(name="train")
def train_cmd() -> None:
    """Train models on July baseline."""
    np.random.seed(42)
    torch.manual_seed(42)

    july_windows_path = PROJECT_ROOT / "data" / "july" / "windows" / "window_dataset.parquet"
    if not july_windows_path.exists():
        click.secho(f"ERROR: July window dataset not found at {july_windows_path}", fg="red")
        raise click.Abort()

    click.echo(f"Loading July windows from {july_windows_path}...")
    july_data = pq.read_table(july_windows_path)

    numeric_cols = []
    cat_cols = []
    for field in july_data.schema:
        if field.name in ("window_start", "window_end"):
            continue
        if pa.types.is_floating(field.type) or pa.types.is_integer(field.type):
            numeric_cols.append(field.name)
        elif pa.types.is_string(field.type) or pa.types.is_large_string(field.type):
            cat_cols.append(field.name)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    detectors = {}

    if numeric_cols:
        detectors["IsolationForest"] = IsolationForestDetector(feature_columns=numeric_cols, n_jobs=1, version="1.0")
        detectors["PCA"] = PCADetector(feature_columns=numeric_cols, target_explained_variance=0.95, version="1.0")
        detectors["Statistical"] = RobustStatisticalDetector(feature_columns=numeric_cols, version="1.0")
        detectors["Autoencoder"] = AutoencoderDetector(feature_columns=numeric_cols, hidden_dim=32, latent_dim=8, epochs=10, batch_size=256, version="1.0")
        detectors["LSTM"] = SequenceLSTMDetector(feature_columns=numeric_cols, seq_len=10, hidden_dim=32, num_layers=1, epochs=5, batch_size=128, version="1.0")
    if cat_cols:
        detectors["Rarity"] = RarityDetector(feature_columns=cat_cols, version="1.0")

    for name, det in detectors.items():
        click.echo(f"Training {name}...")
        det.fit(july_data)
        det.fit_calibrator(july_data, threshold_evidence=0.95)
        model_path = MODELS_DIR / f"{name.lower()}.json"
        det.save(model_path)

    meta = {
        "numeric_features": numeric_cols,
        "categorical_features": cat_cols,
        "detectors": list(detectors.keys()),
        "trained_at": datetime.now(UTC).isoformat(),
    }
    with open(MODELS_DIR / "training_meta.json", "w") as f:
        json.dump(meta, f, indent=2)


@pipeline_group.command(name="infer")
def infer_cmd() -> None:
    """Run inference on August data."""
    np.random.seed(42)
    torch.manual_seed(42)

    meta_path = MODELS_DIR / "training_meta.json"
    with open(meta_path) as f:
        meta = json.load(f)

    numeric_cols = meta["numeric_features"]
    cat_cols = meta["categorical_features"]

    detector_classes = {
        "IsolationForest": lambda: IsolationForestDetector(feature_columns=numeric_cols, n_jobs=1, version="1.0"),
        "PCA": lambda: PCADetector(feature_columns=numeric_cols, target_explained_variance=0.95, version="1.0"),
        "Statistical": lambda: RobustStatisticalDetector(feature_columns=numeric_cols, version="1.0"),
        "Autoencoder": lambda: AutoencoderDetector(feature_columns=numeric_cols, hidden_dim=32, latent_dim=8, epochs=10, batch_size=256, version="1.0"),
        "LSTM": lambda: SequenceLSTMDetector(feature_columns=numeric_cols, seq_len=10, hidden_dim=32, num_layers=1, epochs=5, batch_size=128, version="1.0"),
        "Rarity": lambda: RarityDetector(feature_columns=cat_cols, version="1.0"),
    }

    detectors = {}
    for name in meta["detectors"]:
        model_path = MODELS_DIR / f"{name.lower()}.json"
        det = detector_classes[name]()
        det.load(model_path)
        detectors[name] = det

    aug_windows_path = PROJECT_ROOT / "data" / "august" / "windows" / "window_dataset.parquet"
    if not aug_windows_path.exists():
        click.secho(f"ERROR: August window dataset not found at {aug_windows_path}", fg="red")
        raise click.Abort()

    august_data = pq.read_table(aug_windows_path)
    click.echo(f"Scoring {len(august_data)} August windows...")

    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)

    pq.write_table(results, RESULTS_DIR / "august_scored_windows.parquet")

    # Save July medians
    july_windows_path = PROJECT_ROOT / "data" / "july" / "windows" / "window_dataset.parquet"
    july_data = pq.read_table(july_windows_path)
    july_medians = {}
    for col in numeric_cols:
        arr = july_data.column(col).to_numpy()
        arr = arr[~np.isnan(arr)]
        if len(arr) > 0:
            july_medians[col] = float(np.median(arr))

    with open(RESULTS_DIR / "july_medians.json", "w") as f:
        json.dump(july_medians, f, indent=2)


@pipeline_group.command(name="report")
def report_cmd() -> None:
    """Generate reports."""
    import subprocess
    import sys
    
    # Run the generate_top100_report script
    subprocess.run([sys.executable, str(PROJECT_ROOT / "generate_top100_report.py")], check=True)
    
    # Run the generate_experiment_package script
    subprocess.run([sys.executable, str(PROJECT_ROOT / "generate_experiment_package.py")], check=True)


@pipeline_group.command(name="dashboard")
def dashboard_cmd() -> None:
    """Launch Streamlit dashboard."""
    import subprocess
    import sys
    
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
         "--server.headless", "true", "--server.port", "8501"],
        cwd=str(PROJECT_ROOT)
    )
