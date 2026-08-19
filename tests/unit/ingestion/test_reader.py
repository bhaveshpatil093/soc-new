from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

import pytest

from tads.ingestion.reader import ReadOnlyElasticSource
from tads.schema.settings import Settings


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        elastic_host="https://es.example.com:9200",
        elastic_username="admin",
        elastic_password="supersecretpassword",
    )

def test_public_api_surface_is_strictly_read_only(mock_settings: Settings) -> None:
    """
    Enforces that the abstraction only exposes explicitly approved read-only methods.
    If a developer tries to add .index(), .delete(), or .update() to this class,
    this test will fail.
    """
    source = ReadOnlyElasticSource(settings=mock_settings)

    # Get all public attributes (not starting with _)
    public_api = [attr for attr in dir(source) if not attr.startswith("_")]

    # The explicitly allowed read-only methods per engineering requirements
    allowed_methods = {
        "connect",
        "validate_connection",
        "discover_sources",
        "discover_fields",
        "count_events",
        "stream_events",
        "close",  # graceful teardown helper
    }

    # Assert there are no unexpected public methods/properties
    unexpected = set(public_api) - allowed_methods
    assert not unexpected, f"Found unauthorized methods on ReadOnlyElasticSource: {unexpected}"

    # Assert we didn't forget any required methods
    missing = allowed_methods - set(public_api)
    assert not missing, f"Missing required methods on ReadOnlyElasticSource: {missing}"

@pytest.mark.asyncio
async def test_connect_initializes_client(mock_settings: Settings) -> None:
    """Test that connecting instantiates the underlying private client."""
    source = ReadOnlyElasticSource(settings=mock_settings)
    assert source._client is None

    with patch("tads.ingestion.reader.AsyncElasticsearch") as mock_es:
        await source.connect()
        assert source._client is not None
        mock_es.assert_called_once()

@pytest.mark.asyncio
async def test_discover_sources_requires_explicit_pattern(mock_settings: Settings) -> None:
    """Test that index selection is explicit and has no silent defaults."""
    source = ReadOnlyElasticSource(settings=mock_settings)
    await source.connect()

    # Must fail if no pattern is provided
    with pytest.raises(ValueError, match="valid index pattern must be explicitly provided"):
        await source.discover_sources("")

    with pytest.raises(ValueError, match="valid index pattern must be explicitly provided"):
        await source.discover_sources("   ")

@pytest.mark.asyncio
async def test_stream_events_requires_explicit_index(mock_settings: Settings) -> None:
    """Test that querying requires an explicit index name."""
    source = ReadOnlyElasticSource(settings=mock_settings)
    await source.connect()

    # Using stream_events asynchronously creates an async generator, we must catch
    # the exception when we try to iterate or instantiate it.
    # Actually, the check happens before the yield in our implementation,
    # but since it's an async generator, the ValueError is raised when iterating.

    async def drain(agen: AsyncIterator[Any]) -> None:
        async for _ in agen:
            pass

    with pytest.raises(ValueError, match="valid index must be explicitly provided"):
        await drain(source.stream_events(""))
