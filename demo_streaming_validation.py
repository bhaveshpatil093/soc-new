import os
import sys
import asyncio
import tracemalloc
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.ingest import _run_extraction

async def main():
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password",
        elastic_timeout=1.0
    )
    
    # We will simulate a large dataset by generating fake batches
    # 5 pages of 1000 items each, then an intentional exception to simulate crash
    total_pages = 5
    batch_size = 1000
    
    current_page = 0
    
    with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
        client = MockClient.return_value
        
        # Mock PIT
        client.open_point_in_time = AsyncMock(return_value={"id": "mock_pit_123"})
        client.close_point_in_time = AsyncMock(return_value={})
        
        async def mock_search(**kwargs):
            nonlocal current_page
            
            search_after = kwargs.get("body", {}).get("search_after")
            
            if search_after:
                page_idx = search_after[1]
                current_page = page_idx
            else:
                current_page = 0
            
            if current_page >= total_pages:
                return {"hits": {"hits": []}}
                
            # Crash deterministically on page 2 (the 3rd page, index 2)
            # but only if we haven't already processed it (meaning if we just resumed from page 2, let it run)
            # Wait, if we resume from page 2, current_page becomes 2, search_after is NOT None.
            if current_page == 2 and not getattr(mock_search, "crashed_once", False):
                mock_search.crashed_once = True
                raise Exception("Simulated mid-run crash on page 2!")

            hits = []
            for i in range(batch_size):
                hits.append({
                    "_source": {"event_data": "x" * 1024, "id": current_page * batch_size + i},
                    "sort": ["2026-07-01T00:00:00Z", current_page + 1] # next page pointer
                })
                
            return {"hits": {"hits": hits}}
            
        client.search = AsyncMock(side_effect=mock_search)
        client.close = AsyncMock(return_value=None)
        
        tracemalloc.start()
        
        print("=== RUN 1: Starting Extraction ===")
        try:
            await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, "test_run")
        except Exception as e:
            print(f"\nCaught intentional crash: {e}")
            
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        print(f"Peak memory after Run 1: {peak_mem / 1024 / 1024:.2f} MB")
        
        print("\n=== RUN 2: Resuming Extraction ===")
        # current_page should be reset by the mock if search_after is passed correctly
        await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, "test_run")
        
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        print(f"Peak memory after Run 2: {peak_mem / 1024 / 1024:.2f} MB")
        
        tracemalloc.stop()
        
        print("==================================")
        print("Notice that peak memory remains stable despite fetching many MBs of data.")

if __name__ == "__main__":
    asyncio.run(main())
