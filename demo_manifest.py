import asyncio
import os
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.ingest import _run_extraction
from tads.ingestion.manifest import compute_schema_hash, compute_file_checksum

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
    
    if data_dir.exists():
        shutil.rmtree(data_dir)
    if manifest_dir.exists():
        shutil.rmtree(manifest_dir)
    if checkpoints_dir.exists():
        shutil.rmtree(checkpoints_dir)
        
    run_id = "test_manifest_run"
    batch_size = 50
    total_pages = 2
    
    # Mock extraction loop
    async def mock_search(**kwargs):
        search_after = kwargs.get("body", {}).get("search_after")
        if search_after:
            current_page = search_after[1]
        else:
            current_page = 0
            
        if current_page >= total_pages:
            return {"hits": {"hits": []}}
            
        hits = []
        for i in range(batch_size):
            ts = f"2026-07-01T{12+current_page:02d}:{i:02d}:00Z"
            hits.append({
                "_id": f"doc_{current_page}_{i}",
                "_source": {"@timestamp": ts, "event_data": f"data_{current_page}_{i}", "id": current_page * batch_size + i},
                "sort": [ts, current_page + 1]
            })
            
        return {"hits": {"hits": hits}}
        
    with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
        client = MockClient.return_value
        client.open_point_in_time = AsyncMock(return_value={"id": "mock_pit_123"})
        client.close_point_in_time = AsyncMock(return_value={})
        client.search = AsyncMock(side_effect=mock_search)
        client.close = AsyncMock(return_value=None)
        
        try:
            await _run_extraction(settings, "logs-mock", "2026-07-01", "2026-08-01", batch_size, run_id)
        except SystemExit as e:
            print(f"Exited: {e}")
            
    # Now read the manifest and validate
    manifest_path = manifest_dir / f"{run_id}.json"
    assert manifest_path.exists(), "Manifest was not created"
    
    import json
    with open(manifest_path) as f:
        manifest = json.load(f)
        
    print(f"Manifest:\n{json.dumps(manifest, indent=2)}")
    
    # Validation 1: Schema Hash recomputation
    actual_schema_hash = compute_schema_hash()
    assert actual_schema_hash == manifest["schema_hash"], "Schema hash mismatch"
    
    # Validation 2: File checksum recomputation
    checksums = manifest["checksums"]
    assert len(checksums) == 2, "Expected 2 batch files"
    
    for rel_path, expected_checksum in checksums.items():
        abs_path = data_dir / rel_path
        assert abs_path.exists(), f"File {abs_path} is missing!"
        actual_checksum = compute_file_checksum(abs_path)
        assert actual_checksum == expected_checksum, f"Checksum mismatch for {rel_path}"
        
    assert manifest["status"] == "COMPLETED"
    assert manifest["event_count"] == 100
    
    print("\nSUCCESS: Manifest cryptographically verified against disk!")

if __name__ == "__main__":
    asyncio.run(main())
