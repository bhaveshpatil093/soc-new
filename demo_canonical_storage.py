import os
import shutil
from pathlib import Path

import duckdb
from tads.storage.writer import ParquetStorage
from tads.storage.reader import ParquetReader

def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data" / "raw"
    
    # Cleanup previous
    if data_dir.exists():
        shutil.rmtree(data_dir)
        
    writer = ParquetStorage(dataset="july", base_dir=data_dir)
    reader = ParquetReader(dataset="july", base_dir=data_dir)
    
    # 1. Write a healthy partition for 2026-07
    partition_good = "2026-07"
    batch_good = [
        {
            "_id": "doc1",
            "_source": {
                "@timestamp": "2026-07-01T12:00:00Z",
                "event": {"id": "e1", "category": ["authentication"]},
                "user": {"name": "alice"},
                "unknown_field": "some_value" # Should be packed into raw_extra
            }
        },
        {
            "_id": "doc2",
            "_source": {
                "@timestamp": "2026-07-01T12:01:00Z",
                "event": {"id": "e2", "category": ["network"]},
                "network": {"protocol": "tcp"}
            }
        }
    ]
    
    writer.write_batch(batch_good, partition=partition_good, run_id="run_good", batch_id="b1")
    writer.finalize_partition(partition_good, "run_good", total_docs=2)
    print(f"Finalized partition {partition_good}")

    # 2. Write a broken/interrupted partition for 2026-08 (no finalize)
    partition_bad = "2026-08"
    batch_bad = [
        {
            "_id": "doc3",
            "_source": {
                "@timestamp": "2026-08-01T12:00:00Z",
                "event": {"id": "e3"}
            }
        }
    ]
    
    writer.write_batch(batch_bad, partition=partition_bad, run_id="run_bad", batch_id="b1")
    # Intentional crash: we do NOT call finalize_partition
    print(f"Aborted partition {partition_bad} without finalizing.")
    
    # 3. Read and Validate
    print("\n--- Validating ---")
    
    try:
        reader.load_and_deduplicate(partition_bad)
        print("ERROR: Reader successfully loaded an unfinalized partition!")
    except RuntimeError as e:
        print(f"SUCCESS: Reader rejected unfinalized partition: {e}")
        
    # Read the good partition with DuckDB directly to verify schema and row counts
    con = duckdb.connect(database=':memory:')
    files_pattern = str(data_dir / partition_good / "*.parquet")
    
    # Verify row counts
    count = con.execute(f"SELECT count(*) FROM '{files_pattern}'").fetchone()[0]
    print(f"DuckDB count for {partition_good}: {count}")
    assert count == 2, "Row count mismatch"
    
    # Verify schema uniformity and explicit types
    schema_info = con.execute(f"DESCRIBE SELECT * FROM '{files_pattern}'").fetchall()
    schema_dict = {row[0]: row[1] for row in schema_info}
    
    print("\nDuckDB inferred schema:")
    for col, dtype in schema_dict.items():
        print(f"  {col}: {dtype}")
        
    assert schema_dict["_id"] == "VARCHAR"
    assert "TIMESTAMP" in schema_dict["@timestamp"]
    assert schema_dict["event_category"] == "VARCHAR[]"
    assert schema_dict["raw_extra"] == "VARCHAR"
    
    # Verify data packing
    raw_extra_doc1 = con.execute(f"SELECT raw_extra FROM '{files_pattern}' WHERE _id = 'doc1'").fetchone()[0]
    import json
    parsed_extra = json.loads(raw_extra_doc1)
    assert parsed_extra["unknown_field"] == "some_value", "raw_extra packing failed"
    
    print("\nSUCCESS: Canonical storage layer matches all constraints!")

if __name__ == "__main__":
    main()
