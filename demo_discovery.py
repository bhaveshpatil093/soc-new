import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.discover import _run_discovery

async def main():
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password",
        elastic_timeout=1.0
    )
    
    # We patch AsyncElasticsearch to return fake discovery data
    with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
        client = MockClient.return_value
        
        # 1. Alias/Indices
        client.indices.get_alias = AsyncMock(return_value={
            "logs-july-2026": {},
            "logs-broken-no-time": {}
        })
        
        # 2. Mappings
        async def mock_get_mapping(index):
            if index == "logs-july-2026":
                return {
                    "logs-july-2026": {
                        "mappings": {
                            "properties": {
                                "@timestamp": {"type": "date"},
                                "event": {
                                    "properties": {
                                        "action": {"type": "keyword"}
                                    }
                                }
                            }
                        }
                    }
                }
            elif index == "logs-broken-no-time":
                return {
                    "logs-broken-no-time": {
                        "mappings": {
                            "properties": {
                                "message": {"type": "text"},
                                "random_metric": {"type": "long"}
                            }
                        }
                    }
                }
            return {}
        client.indices.get_mapping = AsyncMock(side_effect=mock_get_mapping)
        
        # 3. Search Aggregations
        async def mock_search(index, **kwargs):
            if index == "logs-july-2026":
                return {
                    "hits": {
                        "total": {"value": 150000, "relation": "eq"}
                    },
                    "aggregations": {
                        "min_ts": {"value_as_string": "2026-07-01T00:00:00.000Z"},
                        "max_ts": {"value_as_string": "2026-07-31T23:59:59.999Z"}
                    }
                }
            elif index == "logs-broken-no-time":
                return {
                    "hits": {
                        "total": 42
                    }
                }
        client.search = AsyncMock(side_effect=mock_search)
        
        print("\n=== RUNNING DISCOVERY ===")
        await _run_discovery(settings, "logs-*")
        print("=========================\n")

if __name__ == "__main__":
    asyncio.run(main())
