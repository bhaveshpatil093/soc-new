import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock
from elasticsearch.exceptions import AuthenticationException, NotFoundError

from tads.cli.ingest import _run_test_connection
from tads.schema.settings import Settings

async def run_scenario(name, mock_setup):
    print(f"\n{'='*50}")
    print(f"SCENARIO: {name}")
    print(f"{'='*50}")
    
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password",
        elastic_timeout=1.0
    )
    
    # We patch ReadOnlyElasticSource methods to simulate the cluster
    with patch("tads.cli.ingest.ReadOnlyElasticSource") as MockSource:
        instance = MockSource.return_value
        # Defaults
        instance.connect = AsyncMock()
        instance.validate_connection = AsyncMock(return_value=True)
        instance.discover_sources = AsyncMock(return_value=["logs-july-2026"])
        instance.discover_fields = AsyncMock(return_value={"properties": {"@timestamp": {"type": "date"}}})
        instance.count_events = AsyncMock(return_value=42)
        instance.close = AsyncMock()
        
        # Apply specific scenario overrides
        mock_setup(instance)
        
        try:
            await _run_test_connection(settings, "*")
        except SystemExit as e:
            print(f"\n=> EXIT CODE: {e.code}")
            return
            
        print("\n=> EXIT CODE: 0")

def setup_401(instance):
    instance.validate_connection.side_effect = AuthenticationException("401 Unauthorized", {}, {})

def setup_404(instance):
    instance.discover_sources.side_effect = NotFoundError("404 Not Found", {}, {})
    
def setup_success(instance):
    pass # Defaults are already success

async def main():
    await run_scenario("Authentication Failure (401)", setup_401)
    await run_scenario("Index Not Found (404)", setup_404)
    await run_scenario("Success Condition", setup_success)

if __name__ == "__main__":
    asyncio.run(main())
