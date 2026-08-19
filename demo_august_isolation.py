import asyncio
import os
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.ingest import _run_extraction
from tads.storage.writer import ParquetStorage

async def main():
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password",
        elastic_timeout=1.0
    )
    
    base_dir = Path(__file__).resolve().parent
    
    # 1. Clean previous state
    for dataset in ["july", "august"]:
        for d in [base_dir / "data" / dataset, base_dir / "artifacts" / dataset]:
            if d.exists():
                shutil.rmtree(d)
        
    run_id = "test_orchestrator_august"
    batch_size = 50
    
    # Mock search
    async def mock_search(**kwargs):
        return {"hits": {"hits": []}}
        
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
        
        print("\n================ 1. ISOLATED AUGUST INGESTION ================")
        await _run_extraction(settings, "august", "logs-mock", "2026-08-01", "2026-09-01", batch_size, run_id)
        
        # Verify isolation
        assert not (base_dir / "data" / "july").exists(), "July data directory should NOT exist!"
        assert not (base_dir / "artifacts" / "july").exists(), "July artifacts directory should NOT exist!"
        assert (base_dir / "data" / "august" / "raw").exists(), "August data directory MUST exist!"
        assert (base_dir / "artifacts" / "august" / "manifests").exists(), "August manifests MUST exist!"
        print("-> Success: August extraction is completely isolated from July.")
        
    print("\n================ 2. CROSS-CONTAMINATION GUARD ================")
    writer = ParquetStorage(dataset="august")
    try:
        # Deliberately point August writer at the July partition
        july_partition_dir = base_dir / "data" / "july" / "raw" / "2026-07"
        writer._get_partition_dir(str(july_partition_dir))
        assert False, "The cross-contamination guard failed to fire!"
    except AssertionError as e:
        print(f"-> Success: Guard caught illegal access: {e}")

    print("\nSUCCESS: All dataset isolation tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
