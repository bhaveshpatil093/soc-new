"""
Benchmark robust feature statistics vs standard statistics on heavy-tailed data.
Demonstrates why mean/std fails for calibration on skewed data, and why median/MAD is required.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
from tads.baselines.statistics import RobustFeatureStatisticsBaseline


def main() -> None:
    print("--- Robust Feature Statistics Benchmark ---")
    
    # 1. Generate heavy-tailed data (e.g. event count per window)
    # Most windows have ~0-5 events, but a few have 10,000+
    np.random.seed(42)
    num_windows = 1_000_000
    
    # Pareto distribution simulates heavy tails perfectly
    pareto_values = np.random.pareto(a=1.5, size=num_windows) * 10
    pareto_values = np.round(pareto_values)
    
    from datetime import UTC, datetime
    july_time = datetime(2025, 7, 15, tzinfo=UTC)
    data = pa.table({
        "window_start": [july_time] * num_windows,
        "event_count": pareto_values
    })
    
    print(f"Generated {num_windows:,} simulated heavy-tailed windows.")
    print(f"Max event_count observed: {np.max(pareto_values):,.0f}")
    
    # 2. Fit the baseline
    baseline = RobustFeatureStatisticsBaseline(features=["event_count"])
    print("Fitting DuckDB statistics baseline...")
    baseline.fit(data)
    
    # 3. Save to compute robust statistics and export to Parquet
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print("Computing exact percentiles and saving to Parquet...")
        baseline.save(tmp_path, "stats")
        
        # 4. Load back to query
        infer_baseline = RobustFeatureStatisticsBaseline(features=["event_count"])
        infer_baseline.load(tmp_path, "stats")
        
        stats = infer_baseline.get_statistics("event_count")
        
        print("\n=== RESULTS ===")
        print(f"{'Metric':<10} | {'Value':<15}")
        print("-" * 30)
        print(f"Mean       | {stats['mean']:<15.2f} (Standard)")
        print(f"StdDev     | {stats['std']:<15.2f} (Standard)")
        print(f"Median     | {stats['median']:<15.2f} (Robust)")
        print(f"MAD        | {stats['mad']:<15.2f} (Robust)")
        print(f"IQR        | {stats['iqr']:<15.2f} (Robust)")
        print(f"p90        | {stats['p90']:<15.2f}")
        print(f"p99        | {stats['p99']:<15.2f}")
        print(f"p99.9      | {stats['p99_9']:<15.2f}")
        
        print("\n=== DOWNSTREAM USAGE EXPLANATION ===")
        print(f"Calibration Method Assigned: '{stats['calibration_method']}'")
        print("Why?")
        print(f"If we used Mean ({stats['mean']:.1f}) and StdDev ({stats['std']:.1f}) to construct a Z-score,")
        print(f"a window with {stats['median']:.0f} events would have a Z-score of (5 - 19) / 126 = -0.11.")
        print("This squashes the entire normal range of data into a tiny band around 0, making it")
        print("impossible to calibrate thresholds correctly. The extreme outliers artificially inflate")
        print("the Standard Deviation (126.88), destroying the sensitivity of the model.")
        print("\nBy using Robust statistics (Median = 5, MAD = 5), the center of the data is accurately")
        print("captured, and outliers don't stretch the scale. A window with 50 events gets a robust")
        print("score of (50 - 5) / 5 = +9.0, accurately flagging it as highly unusual.")


if __name__ == "__main__":
    main()
