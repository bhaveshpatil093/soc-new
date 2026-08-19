from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from tads.ingestion.checkpoint import CheckpointManager, ExtractionCheckpoint
from tads.ingestion.reader import ReadOnlyElasticSource
from tads.schema.settings import Settings


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        elastic_host="https://localhost:9200",
        elastic_username="test",
        elastic_password="password"
    )

class TestCheckpointManager:

    def test_checkpoint_save_and_load(self, tmp_path: Path) -> None:
        manager = CheckpointManager(checkpoint_dir=tmp_path)
        run_id = "test_run"

        checkpoint = ExtractionCheckpoint(
            source="logs-test",
            time_range={"start": "2026-07-01", "end": "2026-08-01"},
            search_after=["2026-07-02T12:00:00Z", "id123"],
            partition="2026-07",
            event_count=500,
            timestamp="2026-08-19T12:00:00Z",
            software_version="0.1.0"
        )

        # Save it
        manager.save(run_id, checkpoint)

        # Load it
        loaded = manager.load(run_id)
        assert loaded is not None
        assert loaded.source == "logs-test"
        assert loaded.search_after == ["2026-07-02T12:00:00Z", "id123"]
        assert loaded.event_count == 500

        # Check clear
        manager.clear(run_id)
        assert manager.load(run_id) is None

class TestReaderStreaming:

    @pytest.mark.asyncio
    async def test_stream_events_sends_correct_time_bounds(self, mock_settings: Settings) -> None:
        with patch("tads.ingestion.reader.AsyncElasticsearch") as mock_client:
            client = mock_client.return_value
            client.open_point_in_time = AsyncMock(return_value={"id": "pit_123"})

            # Return empty hits to finish immediately
            client.search = AsyncMock(return_value={"hits": {"hits": []}})
            client.close_point_in_time = AsyncMock()

            source = ReadOnlyElasticSource(settings=mock_settings)
            await source.connect()

            stream = source.stream_events(
                index="idx",
                start_time="2026-07-01T00:00:00Z",
                end_time="2026-08-01T00:00:00Z"
            )

            async for _ in stream:
                pass

            # Verify search call contains correct range
            client.search.assert_called_once()
            call_args = client.search.call_args[1]

            body = call_args["body"]
            assert "query" in body

            filter_clause = body["query"]["bool"]["filter"][0]
            range_clause = filter_clause["range"]["@timestamp"]

            assert range_clause["gte"] == "2026-07-01T00:00:00Z"
            assert range_clause["lt"] == "2026-08-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_stream_events_yields_batches(self, mock_settings: Settings) -> None:
        with patch("tads.ingestion.reader.AsyncElasticsearch") as mock_client:
            client = mock_client.return_value
            client.open_point_in_time = AsyncMock(return_value={"id": "pit_123"})
            client.close_point_in_time = AsyncMock()

            # Return 2 pages, then empty
            async def mock_search(**kwargs: Any) -> dict[str, Any]:
                sa = kwargs.get("body", {}).get("search_after")
                if not sa:
                    return {
                        "hits": {
                            "hits": [
                                {"_source": {"id": 1}, "sort": ["time1", "1"]},
                                {"_source": {"id": 2}, "sort": ["time2", "2"]}
                            ]
                        }
                    }
                elif sa == ["time2", "2"]:
                    return {
                        "hits": {
                            "hits": [
                                {"_source": {"id": 3}, "sort": ["time3", "3"]}
                            ]
                        }
                    }
                return {"hits": {"hits": []}}

            client.search = AsyncMock(side_effect=mock_search)

            source = ReadOnlyElasticSource(settings=mock_settings)
            await source.connect()

            # batch_size=2 will match the first page exactly, then trigger next fetch
            stream = source.stream_events(index="idx", start_time="a", end_time="b", batch_size=2)

            batches = []
            async for batch, sa in stream:
                batches.append((batch, sa))

            assert len(batches) == 2

            assert len(batches[0][0]) == 2
            assert batches[0][1] == ["time2", "2"]

            assert len(batches[1][0]) == 1
            assert batches[1][1] == ["time3", "3"]
