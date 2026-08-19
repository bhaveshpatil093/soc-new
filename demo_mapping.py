import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock

from tads.schema.settings import Settings
from tads.cli.discover import _run_mapping

async def main():
    settings = Settings(
        elastic_host="https://mocked.local:9200",
        elastic_username="admin",
        elastic_password="password"
    )
    
    with patch("tads.ingestion.reader.AsyncElasticsearch") as MockClient:
        client = MockClient.return_value
        
        async def mock_get_mapping(index):
            return {
                "logs-mock": {
                    "mappings": {
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "event": {
                                "properties": {
                                    "action": {"type": "keyword"},
                                    "category": {"type": "keyword"},
                                    "dataset": {"type": "keyword"}
                                }
                            },
                            "user": {
                                "properties": {
                                    "name": {"type": "keyword"}
                                }
                            },
                            "src_ip": {"type": "ip"},
                            "dest_ip": {"type": "ip"},
                            "computer_name": {"type": "keyword"},
                            # Non-canonical raw fields
                            "custom_id": {"type": "keyword"},
                            "http": {
                                "properties": {
                                    "request": {
                                        "properties": {
                                            "method": {"type": "keyword"},
                                            "body": {"type": "text"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        
        client.indices.get_mapping = AsyncMock(side_effect=mock_get_mapping)
        
        await _run_mapping(settings, "logs-mock")

if __name__ == "__main__":
    asyncio.run(main())
