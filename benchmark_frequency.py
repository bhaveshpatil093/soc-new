"""
Benchmark memory usage of frequency-baseline construction.
Demonstrates bounded memory usage for high-cardinality relationships via DuckDB,
and safety limits for InMemory models.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import psutil
import pyarrow as pa
from tads.baselines.frequencies import DuckDBFrequencyBaseline, InMemoryFrequencyBaseline


def get_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def benchmark_in_memory() -> None:
    print("--- InMemoryFrequencyBaseline Benchmark ---")
    start_mem = get_memory_mb()
    baseline = InMemoryFrequencyBaseline(["user_name"], max_keys=200000)

    print("Generating 100,000 unique keys...")
    from datetime import UTC, datetime
    july_time = datetime(2025, 7, 15, tzinfo=UTC)
    data = pa.table({
        "window_start": [july_time] * 100000,
        "user_name": [f"user_{i}" for i in range(100000)]
    })

    baseline.fit(data)
    end_mem = get_memory_mb()
    print(f"Memory overhead for 100k keys: {end_mem - start_mem:.2f} MB")
    
    print("Testing safety cap...")
    data_large = pa.table({
        "window_start": [july_time] * 150000,
        "user_name": [f"user_overflow_{i}" for i in range(150000)]
    })
    try:
        baseline.fit(data_large)
        print("ERROR: Did not raise MemoryError!")
    except MemoryError as e:
        print(f"Safety cap worked: {e}")
    print()


def benchmark_duckdb() -> None:
    print("--- DuckDBFrequencyBaseline Benchmark ---")
    
    # Restrict duckdb memory intentionally so it spills to disk
    # We pass it as a query since baseline abstracts the connection
    baseline = DuckDBFrequencyBaseline(["user_name", "source_ip"])
    baseline._con.execute("PRAGMA memory_limit='100MB'")
    
    # We will feed 5 million records in chunks
    # 5M records * ~20 bytes = ~100MB of raw strings
    chunk_size = 1_000_000
    chunks = 5
    
    start_mem = get_memory_mb()
    start_time = time.perf_counter()
    
    for i in range(chunks):
        print(f"Fitting chunk {i+1}/{chunks} (1M records)...")
        # generate highly unique pairs
        from datetime import UTC, datetime
        july_time = datetime(2025, 7, 15, tzinfo=UTC)
        data = pa.table({
            "window_start": [july_time] * chunk_size,
            "user_name": [f"user_{j % 500}" for j in range(chunk_size)],
            "source_ip": [f"192.168.{j % 255}.{j % 255}" for j in range(chunk_size)]
        })
        baseline.fit(data)
        
    fit_time = time.perf_counter() - start_time
    fit_mem = get_memory_mb()
    print(f"Memory overhead after fitting 5M records: {fit_mem - start_mem:.2f} MB")
    print(f"Time to fit 5M records: {fit_time:.2f} s")
    
    # Save phase
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print(f"Saving to {tmp_path} (compacting & exporting to Parquet)...")
        save_start = time.perf_counter()
        baseline.save(tmp_path, "user_ip_freq")
        save_time = time.perf_counter() - save_start
        print(f"Time to compact & save: {save_time:.2f} s")
        
        parquet_size = (tmp_path / "user_ip_freq.parquet").stat().st_size / (1024 * 1024)
        print(f"Resulting Parquet file size: {parquet_size:.2f} MB")
        
        # Load and point query
        print("Loading and benchmarking point queries...")
        baseline_infer = DuckDBFrequencyBaseline(["user_name", "source_ip"])
        baseline_infer.load(tmp_path, "user_ip_freq")
        
        q_start = time.perf_counter()
        for _ in range(1000):
            _ = baseline_infer.get_frequency("user_100", "192.168.10.10")
        q_time = time.perf_counter() - q_start
        print(f"Time for 1,000 point lookups: {q_time:.4f} s ({q_time/1000 * 1000000:.0f} µs/lookup)")
        
        # Verify correctness
        assert baseline_infer.get_frequency("user_100", "192.168.10.10") > 0
    print()

def main() -> None:
    benchmark_in_memory()
    benchmark_duckdb()

if __name__ == "__main__":
    main()
