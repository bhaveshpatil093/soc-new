import asyncio
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta

from tads.storage.writer import ParquetStorage

def main():
    print("=== Demo: Timestamp Normalization & Quarantine ===")
    
    base_dir = Path(__file__).resolve().parent
    dataset = "july"
    
    # 1. Clean previous state
    data_dir = base_dir / "data" / dataset
    artifacts_dir = base_dir / "artifacts" / dataset
    
    if data_dir.exists():
        shutil.rmtree(data_dir)
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
        
    writer = ParquetStorage(dataset=dataset, base_dir=base_dir)
    
    now = datetime.now(UTC)
    future_time = (now + timedelta(hours=2)).isoformat()
    
    # Synthetic Batch
    batch = [
        # 1. Valid ISO 8601
        {
            "_id": "valid_1",
            "_source": {"@timestamp": "2026-08-19T10:00:00Z", "event_data": "iso8601"}
        },
        # 2. Valid Epoch (seconds)
        {
            "_id": "valid_2",
            "_source": {"@timestamp": 1692439200, "event_data": "epoch_seconds"}
        },
        # 3. Invalid Timestamp format
        {
            "_id": "invalid_1",
            "_source": {"@timestamp": "not_a_date_at_all", "event_data": "bad_format"}
        },
        # 4. Future Timestamp
        {
            "_id": "future_1",
            "_source": {"@timestamp": future_time, "event_data": "from_the_future"}
        },
        # 5. Out of Range Timestamp
        {
            "_id": "old_1",
            "_source": {"@timestamp": "1999-12-31T23:59:59Z", "event_data": "too_old"}
        },
        # 6. Duplicate Timestamp (Same _id and timestamp as valid_1)
        {
            "_id": "valid_1",
            "_source": {"@timestamp": "2026-08-19T10:00:00Z", "event_data": "im_a_duplicate"}
        },
        # 7. Another valid one to make sure batch writes
        {
            "_id": "valid_3",
            "_source": {"@timestamp": 1692439300000, "event_data": "epoch_millis"}
        }
    ]
    
    run_id = "test_timestamp_run"
    partition = "2026-08"
    
    file_path, dropped = writer.write_batch(batch, partition, run_id)
    
    print("\n--- Writer Dropped Stats ---")
    for reason, count in dropped.items():
        print(f"{reason}: {count}")
        
    assert dropped.get("INVALID_TIMESTAMP") == 1
    assert dropped.get("FUTURE_TIMESTAMP") == 1
    assert dropped.get("OUT_OF_RANGE_TIMESTAMP") == 1
    assert dropped.get("DUPLICATE_TIMESTAMP") == 1
    
    print("\n--- Quarantine File Contents ---")
    quarantine_file = writer.quarantine_dir / f"{run_id}_rejected.jsonl"
    assert quarantine_file.exists(), "Quarantine file was not created!"
    
    with open(quarantine_file, "r") as f:
        for line in f:
            q_rec = json.loads(line)
            print(f"[{q_rec['reason']}] {q_rec['error_msg']}")
            
    # Verify that the parquet file contains the good records and the duplicate
    # (Duplicate was tracked but not dropped by writer)
    import polars as pl
    df = pl.read_parquet(file_path)
    print(f"\nSuccessfully written rows to Parquet: {len(df)}")
    assert len(df) == 4, "Expected 4 rows (3 valid + 1 duplicate to be deduped later)"
    
    print("\nSUCCESS: All normalizations, tracking, and quarantining functioned perfectly!")
    
if __name__ == "__main__":
    main()
