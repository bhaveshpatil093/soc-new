import asyncio
import os
import shutil
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock
from elastic_transport import ConnectionError as ESConnectionError
from elastic_transport import ConnectionTimeout

from tads.schema.settings import Settings
from tads.cli.ingest import _run_extraction
from tads.storage.reader import ParquetReader

import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl

import structlog
logger = structlog.get_logger()

# Set up test environment
settings = Settings(
    elastic_host="https://mocked.local:9200",
    elastic_username="admin",
    elastic_password="password",
    elastic_timeout=1.0
)

base_dir = Path(__file__).resolve().parent
dataset = "july"
data_dir = base_dir / "data" / dataset / "raw" / "2026-07"
checkpoints_dir = base_dir / "artifacts" / dataset / "checkpoints"

manifests_dir = base_dir / "artifacts" / dataset / "manifests"

def cleanup():
    if data_dir.exists():
        shutil.rmtree(data_dir)
    if checkpoints_dir.exists():
        for p in checkpoints_dir.glob("*.json*"):
            p.unlink()
    if manifests_dir.exists():
        for p in manifests_dir.glob("*.json"):
            p.unlink()

def create_mock_client(total_pages=5, batch_size=100, fault_type=None, fault_page=2):
    """
    Creates a mock AsyncElasticsearch client that simulates the specified fault.
    """
    class MockClient:
        def __init__(self):
            self.current_page = 0
            self.crashed_once = False
            self.indices = AsyncMock()
            self.indices.get_alias = AsyncMock(return_value={"logs-mock": {}})
            self.indices.get_mapping = AsyncMock(return_value={"logs-mock": {"mappings": {"properties": {"@timestamp": {"type": "date"}}}}})
        
        async def open_point_in_time(self, **kwargs):
            return {"id": "mock_pit_123"}
            
        async def close_point_in_time(self, **kwargs):
            return {}
            
        async def count(self, **kwargs):
            return {"count": total_pages * batch_size}
            
        async def info(self, **kwargs):
            return {}
            
        async def search(self, **kwargs):
            search_after = kwargs.get("body", {}).get("search_after")
            if search_after:
                self.current_page = search_after[1]
            else:
                self.current_page = 0
                
            if self.current_page >= total_pages:
                return {"hits": {"hits": []}}
                
            # Inject faults
            if self.current_page == fault_page and not self.crashed_once:
                if fault_type == "network_interrupt":
                    self.crashed_once = True
                    raise ESConnectionError("Simulated Network Interruption")
                elif fault_type == "timeout":
                    self.crashed_once = True
                    raise ConnectionTimeout("Simulated Connection Timeout")
                    
            hits = []
            for i in range(batch_size):
                hits.append({
                    "_id": str(self.current_page * batch_size + i),
                    "_source": {
                        "event_data": f"data_{self.current_page}_{i}",
                        "@timestamp": "2026-07-01T00:00:00Z"
                    },
                    "sort": ["2026-07-01T00:00:00Z", self.current_page + 1]
                })
                
            return {"hits": {"hits": hits, "total": {"value": total_pages * batch_size}}}
            
        async def close(self):
            pass

    return MockClient()

async def run_scenario(scenario_name: str, total_pages=5, batch_size=100, setup_func=None, teardown_func=None, fault_type=None, expect_crash=False):
    print(f"\n{'='*60}\nRunning Scenario: {scenario_name}\n{'='*60}")
    cleanup()
    run_id = f"run_{scenario_name}"
    
    mock_client_inst = create_mock_client(total_pages, batch_size, fault_type=fault_type, fault_page=2)
    
    with patch("tads.ingestion.reader.AsyncElasticsearch", return_value=mock_client_inst):
        patchers = setup_func() if setup_func else []
        for p in patchers: p.start()
        
        crashed = False
        print("--- Attempt 1 ---")
        try:
            await _run_extraction(settings, dataset, "logs-mock", "2026-07-01", "2026-08-01", batch_size, run_id, False)
        except BaseException as e:
            print(f"Caught expected crash: {type(e).__name__}: {e}")
            crashed = True
            
        for p in patchers: p.stop()
        if teardown_func: teardown_func()
        
        if expect_crash and not crashed:
            print("ERROR: Expected crash but pipeline succeeded.")
            
        if expect_crash:
            print("--- Attempt 2 (Resume) ---")
            try:
                # Disable faults for resume by re-patching with a clean client (or just let the same mock proceed since crashed_once is True)
                await _run_extraction(settings, dataset, "logs-mock", "2026-07-01", "2026-08-01", batch_size, run_id, False)
            except Exception as e:
                print(f"Failed on resume: {e}")

    # Verify deduplication
    try:
        reader = ParquetReader(dataset=dataset, base_dir=base_dir)
        import polars as pl
        
        # We must create a fake manifest so reader thinks it's finalized
        manifest_path = data_dir / f"manifest_{run_id}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump({"finalized": True}, f)
            
        raw_lf = pl.scan_parquet(data_dir / f"{run_id}_batch_*.parquet")
        raw_count = raw_lf.select(pl.len()).collect().item()
        
        dedup_lf = reader.load_and_deduplicate("2026-07", unique_id_field="_id")
        dedup_count = dedup_lf.select(pl.len()).collect().item()
        
        print(f"  Raw rows on disk: {raw_count}")
        print(f"  Deduplicated rows: {dedup_count}")
        print(f"  Expected rows: {total_pages * batch_size}")
        
        if dedup_count == total_pages * batch_size:
            print("  [PASS] No data loss or duplication.")
        else:
            print("  [FAIL] Data mismatch!")
    except Exception as e:
        print(f"  [ERROR] Validation failed: {e}")

async def main():
    # 1. Network interruption (mid-extraction)
    await run_scenario("1_Network_Interruption", fault_type="network_interrupt")
    
    # 2. Elasticsearch timeout
    await run_scenario("2_Elasticsearch_Timeout", fault_type="timeout")
    
    # 3. Process crash (kill -9 mid-stage)
    # We crash right after parquet write but before checkpoint
    def setup_crash_process():
        original_write = None
        from tads.storage.writer import ParquetStorage
        original_write = ParquetStorage.write_batch
        crashed_once = False
        call_count = 0
        def exploding_write(self, batch, partition, run_id, batch_id=None):
            nonlocal call_count, crashed_once
            call_count += 1
            res = original_write(self, batch, partition, run_id, batch_id)
            if call_count == 2 and not crashed_once:
                crashed_once = True
                raise RuntimeError("KILL -9 SIMULATION")
            return res
        return [patch("tads.storage.writer.ParquetStorage.write_batch", new=exploding_write)]
    
    await run_scenario("3_Process_Crash", setup_func=setup_crash_process, expect_crash=True)
    
    # 4. Machine restart (same effectively as Process crash, but let's crash after checkpoint)
    def setup_restart():
        from tads.ingestion.checkpoint import CheckpointManager
        original_save = CheckpointManager.save
        crashed_once = False
        def exploding_save(self, run_id, checkpoint):
            original_save(self, run_id, checkpoint)
            nonlocal crashed_once
            if checkpoint.event_count == 300 and not crashed_once:
                crashed_once = True
                raise SystemExit("MACHINE RESTART SIMULATION")
        return [patch("tads.ingestion.checkpoint.CheckpointManager.save", new=exploding_save)]
        
    await run_scenario("4_Machine_Restart", setup_func=setup_restart, expect_crash=True)
    
    # 5. Disk-full condition
    def setup_disk_full():
        import pyarrow.parquet as pq
        original_write = pq.write_table
        crashed_once = False
        call_count = 0
        def exploding_write(table, where, *args, **kwargs):
            nonlocal call_count, crashed_once
            call_count += 1
            if call_count == 2 and not crashed_once:
                crashed_once = True
                raise OSError("No space left on device")
            return original_write(table, where, *args, **kwargs)
        return [patch("tads.storage.writer.pq.write_table", new=exploding_write)]
        
    await run_scenario("5_Disk_Full", setup_func=setup_disk_full, expect_crash=True)
    
    # 6. Corrupt partition
    print(f"\n{'='*60}\nRunning Scenario: 6_Corrupt_Partition\n{'='*60}")
    cleanup()
    run_id = "run_6_Corrupt_Partition"
    mock_client_inst = create_mock_client(total_pages=2, batch_size=100)
    with patch("tads.ingestion.reader.AsyncElasticsearch", return_value=mock_client_inst):
        await _run_extraction(settings, dataset, "logs-mock", "2026-07-01", "2026-08-01", 100, run_id, False)
        
    # Corrupt the parquet file
    pq_files = list(data_dir.glob("*.parquet"))
    with open(pq_files[0], "r+b") as f:
        f.truncate(10) # Truncate severely
        
    try:
        reader = ParquetReader(dataset=dataset, base_dir=base_dir)
        manifest_path = data_dir / f"manifest_{run_id}.json"
        with open(manifest_path, "w") as f: json.dump({"finalized": True}, f)
        
        dedup_lf = reader.load_and_deduplicate("2026-07", unique_id_field="_id")
        dedup_count = dedup_lf.select(pl.len()).collect().item()
        print("  [FAIL] Pipeline silently ignored corruption!")
    except BaseException as e:
        print(f"  [PASS] Failed loudly on corrupted file: {type(e).__name__}: {e}")

    # 7. Incomplete checkpoint
    print(f"\n{'='*60}\nRunning Scenario: 7_Incomplete_Checkpoint\n{'='*60}")
    cleanup()
    run_id = "run_7_Incomplete_Checkpoint"
    
    def setup_incomplete_cp():
        import os
        original_replace = os.replace
        crashed_once = False
        def exploding_replace(src, dst):
            nonlocal crashed_once
            if "run_7_Incomplete_Checkpoint" in str(dst) and not crashed_once:
                # We leave the .tmp file dangling and raise exception
                crashed_once = True
                raise OSError("Interrupted during os.replace")
            return original_replace(src, dst)
        return [patch("tads.ingestion.checkpoint.os.replace", new=exploding_replace)]
        
    mock_client_inst = create_mock_client(total_pages=3, batch_size=100)
    with patch("tads.ingestion.reader.AsyncElasticsearch", return_value=mock_client_inst):
        patchers = setup_incomplete_cp()
        patchers[0].start()
        try:
            await _run_extraction(settings, dataset, "logs-mock", "2026-07-01", "2026-08-01", 100, run_id, False)
        except Exception as e:
            print(f"Caught expected crash: {e}")
        patchers[0].stop()
        
        print("--- Attempt 2 (Resume) ---")
        await _run_extraction(settings, dataset, "logs-mock", "2026-07-01", "2026-08-01", 100, run_id, False)
        
    try:
        reader = ParquetReader(dataset=dataset, base_dir=base_dir)
        manifest_path = data_dir / f"manifest_{run_id}.json"
        with open(manifest_path, "w") as f: json.dump({"finalized": True}, f)
        
        raw_lf = pl.scan_parquet(data_dir / f"{run_id}_batch_*.parquet")
        raw_count = raw_lf.select(pl.len()).collect().item()
        
        dedup_lf = reader.load_and_deduplicate("2026-07", unique_id_field="_id")
        dedup_count = dedup_lf.select(pl.len()).collect().item()
        print(f"  Raw rows on disk: {raw_count}")
        print(f"  Deduplicated rows: {dedup_count}")
        print(f"  Expected rows: 300")
        
        if dedup_count == 300:
            print("  [PASS] No data loss or duplication from incomplete checkpoint.")
        else:
            print("  [FAIL] Data mismatch!")
    except Exception as e:
        print(f"  [ERROR] Validation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
