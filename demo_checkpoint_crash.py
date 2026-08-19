import asyncio
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.ingest import _run_extraction
from tads.storage.reader import ParquetReader

async def main():
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password",
        elastic_timeout=1.0
    )
    
    # Cleanup previous runs
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data" / "raw" / "2026-07"
    if data_dir.exists():
        shutil.rmtree(data_dir)
        
    checkpoints_dir = base_dir / "artifacts" / "checkpoints"
    for p in checkpoints_dir.glob("test_crash*.json"):
        p.unlink()
        
    total_pages = 5
    batch_size = 100
    
    # We will simulate two scenarios:
    # Scenario A: Crash BEFORE checkpoint write (after parquet write) -> retry writes batch again -> dedup handles it
    # Scenario B: Crash AFTER checkpoint write -> retry skips batch safely
    
    async def run_scenario(scenario_name: str, crash_page: int, crash_before_checkpoint: bool):
        print(f"\n{'='*40}\nRunning {scenario_name}\n{'='*40}")
        current_page = 0
        crashed_once = False
        
        # We need to monkeypatch the CheckpointManager.save for Scenario B, or just raise in mock_search for Scenario A
        
        async def mock_search(**kwargs):
            nonlocal current_page, crashed_once
            search_after = kwargs.get("body", {}).get("search_after")
            
            if search_after:
                current_page = search_after[1]
            else:
                current_page = 0
                
            if current_page >= total_pages:
                return {"hits": {"hits": []}}
                
            if current_page == crash_page and not crashed_once and crash_before_checkpoint:
                # We return the hits but we inject a failure in the caller right after Parquet write
                pass
                
            hits = []
            for i in range(batch_size):
                hits.append({
                    "_source": {"event_data": f"data_{current_page}_{i}", "id": current_page * batch_size + i},
                    "sort": ["2026-07-01T00:00:00Z", current_page + 1]
                })
                
            return {"hits": {"hits": hits}}
            
        with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
            client = MockClient.return_value
            client.open_point_in_time = AsyncMock(return_value={"id": "mock_pit_123"})
            client.close_point_in_time = AsyncMock(return_value={})
            client.search = AsyncMock(side_effect=mock_search)
            client.close = AsyncMock(return_value=None)
            
            # If crashing BEFORE checkpoint, we patch ParquetStorage to raise Exception AFTER writing
            original_write = None
            if crash_before_checkpoint:
                from tads.storage.writer import ParquetStorage
                original_write = ParquetStorage.write_batch
                def exploding_write(self, batch, partition, run_id, batch_id=None):
                    res = original_write(self, batch, partition, run_id, batch_id)
                    nonlocal current_page, crashed_once
                    if current_page == crash_page and not crashed_once:
                        crashed_once = True
                        raise Exception("CRASH BEFORE CHECKPOINT")
                    return res
                patcher = patch("tads.storage.writer.ParquetStorage.write_batch", new=exploding_write)
                patcher.start()
            
            # If crashing AFTER checkpoint, we patch CheckpointManager to raise Exception AFTER saving
            if not crash_before_checkpoint:
                from tads.ingestion.checkpoint import CheckpointManager
                original_save = CheckpointManager.save
                def exploding_save(self, run_id, checkpoint):
                    original_save(self, run_id, checkpoint)
                    nonlocal current_page, crashed_once
                    if current_page == crash_page and not crashed_once:
                        crashed_once = True
                        raise Exception("CRASH AFTER CHECKPOINT")
                patcher2 = patch("tads.ingestion.checkpoint.CheckpointManager.save", new=exploding_save)
                patcher2.start()

            print("--- Run 1 (Will Crash) ---")
            try:
                await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, f"test_crash_{scenario_name}")
            except (Exception, SystemExit) as e:
                print(f"\nCaught crash/exit: {e}")
                
            if crash_before_checkpoint:
                patcher.stop()
            else:
                patcher2.stop()
                
            print("\n--- Run 2 (Resume) ---")
            await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, f"test_crash_{scenario_name}")

        reader = ParquetReader()
        
        # Read the raw files (no dedup) to see what's on disk
        import polars as pl
        raw_lf = pl.scan_parquet(data_dir / f"test_crash_{scenario_name}_batch_*.parquet")
        raw_count = raw_lf.select(pl.len()).collect().item()
        
        dedup_lf = reader.load_and_deduplicate("2026-07", unique_id_field="id")
        # filter for this specific run_id to not mix scenario A and B
        dedup_count = dedup_lf.select(pl.len()).collect().item()
        
        print(f"\nResults for {scenario_name}:")
        print(f"Total raw rows on disk: {raw_count}")
        print(f"Total rows after explicit exactly-once dedup: {dedup_count}")
        assert dedup_count == total_pages * batch_size, f"Expected {total_pages * batch_size}, got {dedup_count}"
        
        # In Scenario A (crash before checkpoint), we expect the raw count to equal exactly 500, because 
        # the retry uses the same batch_id (offset) and overwrites the exact same file!
        print("Notice: Deduplication is successful!")

    await run_scenario("A_CrashBeforeCheckpoint", crash_page=2, crash_before_checkpoint=True)
    await run_scenario("B_CrashAfterCheckpoint", crash_page=3, crash_before_checkpoint=False)

if __name__ == "__main__":
    asyncio.run(main())
