import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tads.schema.canonical import SCHEMA_V1
from tads.windowing.indexer import WindowIndexer

def _generate_mock_dataset(base_dir: Path, dataset: str) -> None:
    data_dir = base_dir / "data" / dataset
    if data_dir.exists():
        shutil.rmtree(data_dir)
        
    p_dir = data_dir / "raw" / "2026-08-mock"
    p_dir.mkdir(parents=True, exist_ok=True)
    
    schema = SCHEMA_V1.generate_arrow_schema()
    records = []
    
    # Generate some standard sequential timestamps
    start_time = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
    for i in range(10):
        # 12:00:00 -> 12:00:10 (crosses 3 boundaries)
        ts = start_time + timedelta(seconds=i)
        records.append({
            "_id": f"event_{i}",
            "@timestamp": ts,
            "raw_timestamp": ts.isoformat(),
            "message": "test"
        })
        
    # Generate Day Boundary (2026-08-01 23:59:58 -> 2026-08-02 00:00:02)
    day_bound = datetime(2026, 8, 1, 23, 59, 58, tzinfo=UTC)
    for i in range(5):
        ts = day_bound + timedelta(seconds=i)
        records.append({
            "_id": f"event_day_{i}",
            "@timestamp": ts,
            "raw_timestamp": ts.isoformat(),
            "message": "day boundary"
        })
        
    # Generate DST Transition Boundary Simulation
    # Assuming standard UTC timestamps don't physically "transition" like naive timestamps do, 
    # but the epoch boundaries should remain mathematically perfect.
    # November 1, 2026, 01:59:58 AM EDT -> 01:00:02 AM EST (UTC 05:59:58 -> 06:00:02)
    dst_bound = datetime(2026, 11, 1, 5, 59, 58, tzinfo=UTC)
    for i in range(5):
        ts = dst_bound + timedelta(seconds=i)
        records.append({
            "_id": f"event_dst_{i}",
            "@timestamp": ts,
            "raw_timestamp": ts.isoformat(),
            "message": "dst boundary"
        })
        
    # Exact Boundary Snap Test
    records.append({
        "_id": "event_exact_5",
        "@timestamp": datetime(2026, 8, 1, 15, 0, 5, 0, tzinfo=UTC),
        "raw_timestamp": "exact",
        "message": "exact boundary"
    })
    
    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, p_dir / "compacted.parquet", compression="ZSTD")
    print(f"Generated {dataset} dataset mock with {len(records)} boundary-intensive records.")

def main() -> None:
    print("=== Demo: Scalable Semantic Window Indexer ===")
    base_dir = Path(__file__).resolve().parent
    
    _generate_mock_dataset(base_dir, "july")
    
    indexer = WindowIndexer(dataset="july", base_dir=base_dir)
    results = indexer.generate_index()
    
    event_idx_path = results['event_index']
    win_sum_path = results['window_summary']
    
    print("\n--- Event Index Preview (_id -> window_id) ---")
    conn = duckdb.connect()
    conn.execute("SET TimeZone='UTC'")
    print(conn.execute(f"SELECT * FROM '{event_idx_path}' LIMIT 5").fetchall())
    
    print("\n--- Window Summary Preview (window_id -> start/end) ---")
    print(conn.execute(f"SELECT * FROM '{win_sum_path}' LIMIT 5").fetchall())
    
    print("\n--- Day Boundary Verification ---")
    day_bound_events = conn.execute(f"""
        SELECT e._id, w.window_start, w.window_end 
        FROM '{event_idx_path}' e
        JOIN '{win_sum_path}' w ON e.window_id = w.window_id
        WHERE e._id LIKE 'event_day_%'
        ORDER BY e._id
    """).fetchall()
    for row in day_bound_events:
        print(f"{row[0]:<15} | {row[1]} | {row[2]}")
    
    print("\n--- Exact Boundary Verification ---")
    exact_bound_events = conn.execute(f"""
        SELECT e._id, w.window_start, w.window_end 
        FROM '{event_idx_path}' e
        JOIN '{win_sum_path}' w ON e.window_id = w.window_id
        WHERE e._id = 'event_exact_5'
    """).fetchall()
    for row in exact_bound_events:
        print(f"{row[0]:<15} | {row[1]} | {row[2]}")
    
    # Assert Exact boundary mapped to the NEW window
    assert str(exact_bound_events[0][1]) == '2026-08-01 15:00:05+00:00'
    assert str(exact_bound_events[0][2]) == '2026-08-01 15:00:10+00:00'
    
    print("\nSUCCESS: Window Indexer successfully aggregated exact UTC boundaries and day-crossings deterministically!")

if __name__ == "__main__":
    main()
