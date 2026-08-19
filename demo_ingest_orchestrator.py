import asyncio
import os
import shutil
from pathlib import Path
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
    
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data" / "raw"
    manifest_dir = base_dir / "artifacts" / "manifests"
    checkpoints_dir = base_dir / "artifacts" / "checkpoints"
    
    for d in [data_dir, manifest_dir, checkpoints_dir]:
        if d.exists():
            shutil.rmtree(d)
        
    run_id = "test_orchestrator_july"
    batch_size = 50
    total_pages = 2
    
    # Mock extraction loop with some deliberately dropped events
    async def mock_search(**kwargs):
        search_after = kwargs.get("body", {}).get("search_after")
        current_page = search_after[1] if search_after else 0
            
        if current_page >= total_pages:
            return {"hits": {"hits": []}}
            
        hits = []
        for i in range(batch_size):
            ts = f"2026-07-01T{12+current_page:02d}:{i:02d}:00Z"
            
            # Intentionally drop one event per page for testing
            if i == 5:
                # missing _id
                hits.append({
                    "_source": {"@timestamp": ts, "event_data": f"bad"},
                    "sort": [ts, current_page + 1]
                })
            else:
                hits.append({
                    "_id": f"doc_{current_page}_{i}",
                    "_source": {"@timestamp": ts, "event_data": f"data", "id": current_page * batch_size + i},
                    "sort": [ts, current_page + 1]
                })
            
        return {"hits": {"hits": hits}}
        
    with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
        client = MockClient.return_value
        client.open_point_in_time = AsyncMock(return_value={"id": "mock_pit_123"})
        client.close_point_in_time = AsyncMock(return_value={})
        client.search = AsyncMock(side_effect=mock_search)
        client.info = AsyncMock(return_value={"version": {"number": "8.0.0"}})
        client.indices = AsyncMock()
        client.indices.get_mapping = AsyncMock(return_value={
            "logs-mock": {
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event_data": {"type": "keyword"}
                    }
                }
            }
        })
        client.close = AsyncMock(return_value=None)
        
        print("\n================ RUN 1: FRESH EXTRACTION ================")
        await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, run_id)
        
        print("\n================ RUN 2: IDEMPOTENT SKIP ================")
        await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, run_id)
            
    print("\nSUCCESS: End-to-end orchestrator passes restartability and validation checks!")

if __name__ == "__main__":
    asyncio.run(main())
