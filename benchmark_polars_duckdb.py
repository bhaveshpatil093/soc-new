import os
import time
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl
import duckdb
import numpy as np
from datetime import datetime, timedelta

def memory_usage_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def generate_synthetic_parquet(file_path: str, num_rows: int = 2_000_000):
    """Generates a synthetic Parquet file for benchmarking."""
    print(f"Generating {num_rows} rows of synthetic data...")
    
    # Generate in chunks to avoid high memory usage during generation
    chunk_size = 500_000
    schema = pa.schema([
        ('timestamp', pa.timestamp('us', tz='UTC')),
        ('source_ip', pa.string()),
        ('dest_port', pa.int32()),
        ('bytes_transferred', pa.float64())
    ])
    
    with pq.ParquetWriter(file_path, schema, compression='snappy') as writer:
        base_time = datetime(2025, 7, 1)
        for i in range(0, num_rows, chunk_size):
            # Deterministic pseudo-random generation
            np.random.seed(i)
            
            timestamps = [base_time + timedelta(seconds=x) for x in range(i, i + chunk_size)]
            source_ips = [f"192.168.1.{np.random.randint(1, 255)}" for _ in range(chunk_size)]
            dest_ports = np.random.randint(1, 65535, size=chunk_size).astype(np.int32)
            bytes_transferred = np.random.lognormal(mean=5.0, sigma=2.0, size=chunk_size)
            
            table = pa.Table.from_arrays(
                [
                    pa.array(timestamps, type=pa.timestamp('us', tz='UTC')),
                    pa.array(source_ips),
                    pa.array(dest_ports),
                    pa.array(bytes_transferred)
                ],
                schema=schema
            )
            writer.write_table(table)
            
    print(f"File size: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB")

def benchmark_polars(file_path: str):
    start_mem = memory_usage_mb()
    start_time = time.time()
    
    # LAZY execution: does not load the full dataset into memory
    lazy_df = pl.scan_parquet(file_path)
    
    # Filter and aggregate
    result = (
        lazy_df
        .filter(pl.col("dest_port") < 1024)
        .group_by("source_ip")
        .agg([
            pl.col("bytes_transferred").sum().alias("total_bytes"),
            pl.col("dest_port").count().alias("connection_count")
        ])
        .sort("total_bytes", descending=True)
        .limit(5)
        .collect() # Trigger streaming execution
    )
    
    end_time = time.time()
    end_mem = memory_usage_mb()
    
    print("\n--- Polars Lazy Evaluation ---")
    print(result)
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Memory delta: {end_mem - start_mem:.2f} MB")
    print(f"Peak memory approx: {end_mem:.2f} MB")

def benchmark_duckdb(file_path: str):
    start_mem = memory_usage_mb()
    start_time = time.time()
    
    # DuckDB can query parquet files directly without loading them fully
    con = duckdb.connect()
    
    query = f"""
        SELECT source_ip, SUM(bytes_transferred) as total_bytes, COUNT(dest_port) as connection_count
        FROM '{file_path}'
        WHERE dest_port < 1024
        GROUP BY source_ip
        ORDER BY total_bytes DESC
        LIMIT 5
    """
    
    result = con.execute(query).fetch_arrow_table() # Use arrow, not pandas
    
    end_time = time.time()
    end_mem = memory_usage_mb()
    
    print("\n--- DuckDB Embedded SQL ---")
    print(result)
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Memory delta: {end_mem - start_mem:.2f} MB")
    print(f"Peak memory approx: {end_mem:.2f} MB")

if __name__ == "__main__":
    file_path = "synthetic_benchmark.parquet"
    if not os.path.exists(file_path):
        generate_synthetic_parquet(file_path)
        
    print(f"Initial Memory: {memory_usage_mb():.2f} MB")
    benchmark_polars(file_path)
    benchmark_duckdb(file_path)
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
