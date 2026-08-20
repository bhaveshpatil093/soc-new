"""
Comprehensive benchmarking suite for all July-based anomaly detectors.
"""

from __future__ import annotations

import gc
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
from tabulate import tabulate

from tads.models.detectors.autoencoder import AutoencoderDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.sequence_lstm import SequenceLSTMDetector
from tads.models.detectors.statistical import RobustStatisticalDetector


def generate_benchmark_data(days: int = 15, windows_per_day: int = 1000) -> list[pa.Table]:
    """
    Generate synthetic data for benchmark. 
    Returns a list of daily pa.Tables.
    Features: 5 continuous (mixed normal/heavy tail), 3 categorical.
    """
    start = datetime(2025, 7, 1, tzinfo=UTC)
    
    daily_tables = []
    
    # Base categorical distributions
    users = ["alice", "bob", "charlie", "david", "eve"]
    hosts = ["host-A", "host-B", "host-C"]
    cmds = ["cmd.exe", "powershell.exe", "bash"]
    
    for day in range(days):
        timestamps = [start + timedelta(days=day, seconds=i * 5) for i in range(windows_per_day)]
        
        # Continuous
        f1 = np.random.normal(50, 10, windows_per_day)
        f2 = np.random.exponential(scale=5, size=windows_per_day)
        
        # Temporal dependency for f3 (sine + noise) to help LSTM
        t = np.arange(windows_per_day)
        f3 = 10 * np.sin(2 * np.pi * t / 100) + np.random.normal(0, 0.5, windows_per_day)
        
        # Highly correlated for PCA
        latent = np.random.normal(0, 5, windows_per_day)
        f4 = latent + np.random.normal(0, 1, windows_per_day)
        f5 = -latent + np.random.normal(0, 1, windows_per_day)
        
        # Categorical
        u_col = np.random.choice(users, size=windows_per_day, p=[0.4, 0.3, 0.15, 0.1, 0.05])
        h_col = np.random.choice(hosts, size=windows_per_day, p=[0.6, 0.3, 0.1])
        c_col = np.random.choice(cmds, size=windows_per_day, p=[0.7, 0.2, 0.1])
        
        # Add slight daily non-stationarity noise so flag rates vary a bit
        f1 += np.random.normal(0, day * 0.1, windows_per_day)
        
        # Inject strong non-stationarity in validation days to trigger pathological behavior
        if day >= 10:
            # During validation, feature_2 slowly diverges completely from training
            f2 += (day - 10) * 15.0
            
        
        table = pa.table({
            "window_start": timestamps,
            "feature_1": f1.tolist(),
            "feature_2": f2.tolist(),
            "feature_3": f3.tolist(),
            "feature_4": f4.tolist(),
            "feature_5": f5.tolist(),
            "user": u_col.tolist(),
            "host": h_col.tolist(),
            "command": c_col.tolist(),
        })
        daily_tables.append(table)
        
    return daily_tables


def main() -> None:
    np.random.seed(42)
    
    print("=== Generating Benchmark Data (15 days) ===")
    daily_tables = generate_benchmark_data(days=15, windows_per_day=2000)
    
    train_tables = daily_tables[:10]  # Days 1-10
    val_tables = daily_tables[10:]    # Days 11-15
    
    train_data = pa.concat_tables(train_tables)
    
    cont_features = ["feature_1", "feature_2", "feature_3", "feature_4", "feature_5"]
    cat_features = ["user", "host", "command"]
    
    models = {
        "IsolationForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1, version="1.0"),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95, version="1.0"),
        "RobustStatistical": RobustStatisticalDetector(feature_columns=cont_features, version="1.0"),
        "Autoencoder": AutoencoderDetector(feature_columns=cont_features, hidden_dim=8, latent_dim=3, epochs=10, batch_size=256, version="1.0"),
        "SequenceLSTM": SequenceLSTMDetector(feature_columns=cont_features, seq_len=10, hidden_dim=16, num_layers=1, epochs=5, batch_size=128, version="1.0"),
        "Rarity": RarityDetector(feature_columns=cat_features, version="1.0"),
    }
    
    results = []
    
    print(f"\nTraining set: 10 days ({len(train_data)} windows)")
    print(f"Validation set: 5 days (2000 windows/day)")
    print("-" * 80)
    
    for name, detector in models.items():
        print(f"\nBenchmarking {name}...")
        gc.collect()
        tracemalloc.start()
        
        # --- TRAIN ---
        t0 = time.time()
        detector.fit(train_data)
        detector.fit_calibrator(train_data, threshold_evidence=0.95)
        t_train = time.time() - t0
        
        _, peak_mem_train = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Artifact size
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.bin"
            detector.save(path)
            artifact_mb = path.stat().st_size / (1024 * 1024)
            
        # --- INFERENCE ---
        daily_flag_rates = []
        inf_times = []
        
        for val_day_data in val_tables:
            t0 = time.time()
            preds = detector.predict(val_day_data)
            t_inf = time.time() - t0
            
            inf_times.append(t_inf / len(val_day_data))  # time per window
            
            flags = preds.column("anomaly").to_numpy(zero_copy_only=False)
            daily_flag_rates.append(np.mean(flags))
            
        avg_inf_ms_per_window = np.mean(inf_times) * 1000
        mean_flag_rate = np.mean(daily_flag_rates) * 100
        std_flag_rate = np.std(daily_flag_rates) * 100
        
        # Stability note
        if std_flag_rate > 5.0:
            stability = "POOR (High daily variance)"
        elif mean_flag_rate < 0.5:
            stability = "PATHOLOGICAL (Near 0%)"
        elif mean_flag_rate > 95.0:
            stability = "PATHOLOGICAL (Near 100%)"
        else:
            stability = "STABLE"
            
        results.append({
            "Detector": name,
            "Train Time (s)": round(t_train, 2),
            "Inf Time (ms/win)": round(avg_inf_ms_per_window, 4),
            "Train Mem Peak (MB)": round(peak_mem_train / (1024 * 1024), 2),
            "Artifact Size (MB)": round(artifact_mb, 2),
            "Val Flag Rate (%)": f"{mean_flag_rate:.2f} ± {std_flag_rate:.2f}",
            "Stability": stability,
        })
        
    print("\n\n=== BENCHMARK REPORT ===\n")
    headers = "keys"
    print(tabulate(results, headers=headers, tablefmt="github"))
    
    # Save to artifact directory
    md_table = tabulate(results, headers=headers, tablefmt="github")
    
    # Generate feature sensitivity notes (conceptual for this script, we can print explain() for 1 window)
    print("\n=== FEATURE SENSITIVITY CHECK ===")
    sample_window = val_tables[-1].slice(0, 1)
    for name, detector in models.items():
        try:
            exps = detector.explain(sample_window)
            print(f"{name:<20}: {exps[0].as_py()}")
        except Exception as e:
            print(f"{name:<20}: Error extracting explanation: {e}")
            
if __name__ == "__main__":
    main()
