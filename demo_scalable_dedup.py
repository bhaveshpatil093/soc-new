import json
import os
import shutil
from pathlib import Path
from datetime import datetime, UTC

import pyarrow as pa
import pyarrow.parquet as pq

from tads.storage.dedup import PartitionDeduplicator
from tads.schema.canonical import SCHEMA_V1

def main():
    print("=== Demo: Scalable Deduplication ===")
    
    base_dir = Path(__file__).resolve().parent
    dataset = "july"
    
    # 1. Clean previous state
    data_dir = base_dir / "data" / dataset
    if data_dir.exists():
        shutil.rmtree(data_dir)
        
    partition = "2026-08-dedup-test"
    p_dir = base_dir / "data" / dataset / "raw" / partition
    p_dir.mkdir(parents=True, exist_ok=True)
    
    schema = SCHEMA_V1.generate_arrow_schema()
    
    # Generate some dummy data
    records = []
    
    # 10 Distinct Events
    for i in range(10):
        records.append({
            "_id": f"distinct_{i}",
            "@timestamp": datetime.now(UTC),
            "raw_timestamp": "timestamp",
        })
        
    # 5 Exact Duplicates (identical _id)
    for i in range(5):
        records.append({
            "_id": f"dup_{i}",
            "@timestamp": datetime.now(UTC),
            "raw_timestamp": "timestamp",
        })
        # Add the duplicate itself (same _id)
        records.append({
            "_id": f"dup_{i}",
            "@timestamp": datetime.now(UTC),
            "raw_timestamp": "timestamp",
        })
        
    # 3 Legitimately Repeated Events (different _id, but same content)
    for i in range(3):
        ts = datetime.now(UTC)
        records.append({
            "_id": f"legit_orig_{i}",
            "@timestamp": ts,
            "raw_timestamp": "timestamp",
            "event_action": "repeated_action"
        })
        records.append({
            "_id": f"legit_repeat_{i}",
            "@timestamp": ts,
            "raw_timestamp": "timestamp",
            "event_action": "repeated_action"
        })
        
    # Total Input: 10 + (5*2) + (3*2) = 10 + 10 + 6 = 26 records
    # Duplicates to remove: 5 (the exact copies of dup_i)
    # Retained expected: 21 (10 distinct + 5 dup_i base + 6 legit repeated)
    
    table = pa.Table.from_pylist(records, schema=schema)
    
    # Write as two separate batches to simulate distributed writing
    pq.write_table(table.slice(0, 13), p_dir / "run_batch_1.parquet", compression="ZSTD")
    pq.write_table(table.slice(13), p_dir / "run_batch_2.parquet", compression="ZSTD")
    
    print(f"Prepared raw partition with 26 records in 2 batch files.")
    
    dedup = PartitionDeduplicator(dataset=dataset, base_dir=base_dir)
    metrics = dedup.compact_partition(partition)
    
    print("\n--- Deduplication Metrics ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")
        
    assert metrics["input_count"] == 26
    assert metrics["duplicates_found"] == 5
    assert metrics["retained_count"] == 21
    assert round(metrics["duplicate_ratio_percent"], 2) == round((5/26)*100, 2)
    
    # Ensure uncompacted files are gone
    import glob
    assert len(glob.glob(str(p_dir / "*_batch_*.parquet"))) == 0, "Batch files were not cleaned up!"
    assert (p_dir / "compacted.parquet").exists(), "Compacted file is missing!"
    
    print("\nSUCCESS: Deduplication exactly targeted _id duplicates and retained legitimate repeats.")

if __name__ == "__main__":
    main()
