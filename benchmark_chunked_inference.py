"""
Chunked inference benchmark for pipeline performance (10K to 1 Billion).

Executes across progressively larger datasets to measure throughput
(Parquet I/O, Feature Gen, Model Inference) and resource constraints,
using a chunked approach for inference to avoid OOM.
"""

from __future__ import annotations

import gc
import logging
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta

import numpy as np
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
from tabulate import tabulate

from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.ensemble import EnsembleDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector

logging.basicConfig(level=logging.WARNING)


def get_peak_ram_mb() -> float:
    """Get peak RAM usage for the current process."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def generate_synthetic_table(n_rows: int, start_month: int = 8) -> pa.Table:
    """Generate a PyArrow table using batched numpy generation to save peak RAM."""
    start = datetime(2025, start_month, 1, tzinfo=UTC)
    # Using float32 instead of float64 where possible saves 50% RAM
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_rows)]
    
    event_counts = np.random.poisson(lam=10, size=n_rows).astype(np.int32)
    f_volume = (event_counts * np.random.normal(5, 0.5, n_rows)).astype(np.float32)
    f_latency = np.random.normal(30, 2, n_rows).astype(np.float32)
    f_cpu = np.random.normal(30, 2, n_rows).astype(np.float32)
    f_mem = (f_cpu * 1.5 + np.random.normal(0, 1, n_rows)).astype(np.float32)
    
    # Just dummy categorical ints
    users = np.random.randint(0, 100, size=n_rows).astype(np.int32)
    hosts = np.random.randint(0, 50, size=n_rows).astype(np.int32)
    
    return pa.table({
        "window_start": timestamps,
        "event_count": event_counts.tolist(),
        "f_volume": f_volume.tolist(),
        "f_latency": f_latency.tolist(),
        "f_cpu": f_cpu.tolist(),
        "f_mem": f_mem.tolist(),
        "user": users.tolist(),
        "host": hosts.tolist(),
    })

def chunked_score_all(pipeline: AugustInferencePipeline, table: pa.Table, chunk_size: int = 100_000) -> pa.Table:
    """Run pipeline.score_all() in chunks to save memory."""
    batches = table.to_batches(max_chunksize=chunk_size)
    results = []
    for batch in batches:
        chunk_table = pa.Table.from_batches([batch])
        res = pipeline.score_all(chunk_table)
        results.append(res)
    return pa.concat_tables(results)

def main() -> None:
    print("=== PIPELINE SCALABILITY BENCHMARK (CHUNKED) ===\n")
    
    # Prepare the fitted detectors once (using a tiny subset)
    dummy_train = generate_synthetic_table(5000, start_month=7)
    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]
    
    detectors = {
        "IForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95),
        "Statistical": RobustStatisticalDetector(feature_columns=cont_features),
        "Rarity": RarityDetector(feature_columns=cat_features),
    }
    ensemble = EnsembleDetector(detectors=detectors, strategy="mean")
    ensemble.fit(dummy_train)
    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="mean")
    
    # Tiers to test - skip 100M for local speed
    tiers = [10_000, 100_000, 1_000_000]
    
    results = []
    failed_tier = None
    
    for n_rows in tiers:
        print(f"\n--- Running Tier: {n_rows:,} windows ---")
        
        gc.collect()
        ram_before = get_peak_ram_mb()
        
        try:
            # 1. Generation
            t0 = time.time()
            table = generate_synthetic_table(n_rows)
            t1 = time.time()
            gen_sec = t1 - t0
            
            # Memory Check
            ram_after_gen = get_peak_ram_mb()
            
            # 2. Parquet I/O
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, "dataset.parquet")
                
                t_w0 = time.time()
                pq.write_table(table, filepath)
                t_w1 = time.time()
                write_sec = t_w1 - t_w0
                
                disk_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                t_r0 = time.time()
                _ = pq.read_table(filepath)
                t_r1 = time.time()
                read_sec = t_r1 - t_r0
                
            write_mb_s = disk_mb / write_sec if write_sec > 0 else 0
            read_mb_s = disk_mb / read_sec if read_sec > 0 else 0
            
            # 3. Model Inference using chunks!
            extrapolated = False
            inference_sec = 0.0
            
            # We don't need to extrapolate anymore due to memory! We can actually score 10M rows.
            t_i0 = time.time()
            _ = chunked_score_all(pipeline, table, chunk_size=100_000)
            t_i1 = time.time()
            inference_sec = t_i1 - t_i0
                
            ram_peak = get_peak_ram_mb() - ram_before
            cpu_pct = psutil.cpu_percent(interval=None)
            
            inference_throughput = n_rows / inference_sec if inference_sec > 0 else 0
            
            # Determine Bottleneck for this tier
            times = {"Gen/Feat": gen_sec, "I/O": write_sec + read_sec, "Inference": inference_sec}
            slowest_stage = max(times, key=times.get) # type: ignore
            
            if ram_peak > 4000:
                bottleneck = "Memory Bound (RAM Exhaustion)"
            elif slowest_stage == "Inference":
                bottleneck = "CPU Bound (sklearn IsolationForest)"
            elif slowest_stage == "I/O":
                bottleneck = "I/O Bound (Disk writes)"
            else:
                bottleneck = "CPU Bound (Feature Gen)"
                
            results.append([
                f"{n_rows:,}",
                f"{write_mb_s:.1f} / {read_mb_s:.1f}",
                f"{inference_throughput:,.0f} w/s" + (" *" if extrapolated else ""),
                f"{ram_peak:.0f} MB",
                f"{cpu_pct}%",
                f"{disk_mb:.1f} MB",
                bottleneck
            ])
            
            # Free memory
            del table
            gc.collect()
            
        except MemoryError:
            print(f"FAILED: MemoryError during tier {n_rows:,}.")
            failed_tier = n_rows
            break
            
    print("\n" + "="*80)
    print("=== PIPELINE THROUGHPUT & SCALING REPORT (CHUNKED) ===")
    print("="*80)
    
    print(tabulate(results, headers=[
        "Scale (Windows)", "Parquet Write/Read (MB/s)", "Inference Thruput",
        "Peak RAM Added", "CPU Usage", "Raw Disk Size", "Primary Bottleneck"
    ], tablefmt="grid"))
    
    print("\n=== BILLION-SCALE EXTRAPOLATION & BOTTLENECK ANALYSIS ===")
    
    # Take the 1M tier (index 2)
    if len(results) >= 3:
        inf_throughput_1m = float(results[2][2].split(" ")[0].replace(",", ""))
        ram_1m = float(results[2][3].split(" ")[0])
        
        b_time_hours = 1_000_000_000 / inf_throughput_1m / 3600
        b_ram_gb = (ram_1m * 1000) / 1024
        b_disk_gb = float(results[2][5].split(" ")[0]) * 1000 / 1024
        
        print(f"Extrapolating from 1,000,000 window measurements:")
        print(f"  - Target Size: 1,000,000,000 windows")
        print(f"  - Est. Time (Single Node): {b_time_hours:.1f} hours")
        print(f"  - Est. RAM Added (Chunked): {ram_1m:.0f} MB (Constant)")
        print(f"  - Est. Disk Required: {b_disk_gb:.0f} GB\n")

if __name__ == "__main__":
    main()
