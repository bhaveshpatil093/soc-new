import json
import os
import shutil
from pathlib import Path
from datetime import datetime, UTC

import pyarrow as pa
import pyarrow.parquet as pq

from tads.profiling.profiler import DatasetProfiler
from tads.schema.canonical import SCHEMA_V1

def _generate_mock_dataset(base_dir: Path, dataset: str):
    data_dir = base_dir / "data" / dataset
    if data_dir.exists():
        shutil.rmtree(data_dir)
        
    p_dir = data_dir / "raw" / "2026-08-mock"
    p_dir.mkdir(parents=True, exist_ok=True)
    
    schema = SCHEMA_V1.generate_arrow_schema()
    
    # 10,000 synthetic records
    records = []
    
    for i in range(10000):
        # We purposely leave source_ip missing 25% of the time, and user_name missing 30% of the time
        rec = {
            "_id": f"event_{dataset}_{i}",
            "@timestamp": datetime.now(UTC),
            "raw_timestamp": "ts",
            "host_name": f"host_{i % 5}",  # 5 unique hosts
            "process_name": f"proc_{i % 10}", # 10 unique processes
            "event_category": "network" if i % 2 == 0 else "authentication",
            "event_outcome": "success" if i % 10 != 0 else "failure",
            "message": "dummy message"
        }
        
        # 25% missing source_ip
        if i % 100 >= 25:
            rec["source_ip"] = f"192.168.1.{i % 255}"
            
        # 30% missing user_name
        if i % 100 >= 30:
            rec["user_name"] = f"user_{i % 50}"
            
        records.append(rec)
        
    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, p_dir / "compacted.parquet", compression="ZSTD")
    print(f"Generated {dataset} dataset mock with 10,000 records.")


def main():
    print("=== Demo: Scalable Dataset Profiler ===")
    
    base_dir = Path(__file__).resolve().parent
    
    # 1. Generate July and August mocks
    _generate_mock_dataset(base_dir, "july")
    _generate_mock_dataset(base_dir, "august")
    
    # 2. Run Profiler for July
    print("\n--- Profiling July ---")
    july_profiler = DatasetProfiler(dataset="july", run_id="july_demo_run", base_dir=base_dir)
    july_profile = july_profiler.profile()
    july_profiler.print_summary(july_profile)
    
    # 3. Run Profiler for August
    print("\n--- Profiling August ---")
    august_profiler = DatasetProfiler(dataset="august", run_id="august_demo_run", base_dir=base_dir)
    august_profile = august_profiler.profile()
    august_profiler.print_summary(august_profile)
    
    # Assert missingness flagging logic
    assert july_profile["missingness"]["source_ip"]["flagged_review"] == True, "source_ip (>20% missing) should be flagged!"
    assert july_profile["missingness"]["user_name"]["flagged_review"] == True, "user_name (>20% missing) should be flagged!"
    assert july_profile["missingness"]["event_category"]["flagged_review"] == False, "event_category (0% missing) should NOT be flagged!"
    
    print("\nSUCCESS: Profiler accurately scanned multi-dataset partitions, computed unique/volume/missingness, and correctly flagged high-missingness fields.")

if __name__ == "__main__":
    main()
