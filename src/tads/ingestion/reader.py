from collections.abc import AsyncIterator
from typing import Any

import structlog
from elastic_transport import ConnectionError as ESConnectionError
from elastic_transport import ConnectionTimeout
from elasticsearch import AsyncElasticsearch
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from tads.schema.settings import Settings

logger = structlog.get_logger()

class ReadOnlyElasticSource:
    """
    A strictly read-only wrapper around AsyncElasticsearch.
    Enforces that callers cannot execute write operations (index, update, delete)
    by deliberately restricting the exposed public API surface.
    """

    def __init__(
        self,
        settings: Settings,
        max_retries: int = 5,
        min_backoff_sec: float = 1.0,
        max_backoff_sec: float = 60.0,
    ) -> None:
        self._settings = settings
        self._max_retries = max_retries
        self._min_backoff_sec = min_backoff_sec
        self._max_backoff_sec = max_backoff_sec
        self._client: AsyncElasticsearch | None = None

        # Configure retry logic dynamically based on instance parameters
        self._retry_decorator = retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._min_backoff_sec, max=self._max_backoff_sec),
            retry=retry_if_exception_type((ESConnectionError, ConnectionTimeout)),
            reraise=True,
        )

    async def connect(self) -> None:
        """Initializes the underlying Elasticsearch connection."""
        if self._client is not None:
            return

        client_kwargs: dict[str, Any] = {
            "hosts": [str(self._settings.elastic_host)],
            "basic_auth": (
                self._settings.elastic_username,
                self._settings.elastic_password.get_secret_value()
            ),
            "request_timeout": self._settings.elastic_timeout,
            "verify_certs": self._settings.elastic_verify_tls,
        }

        if self._settings.elastic_ca_cert:
            client_kwargs["ca_certs"] = str(self._settings.elastic_ca_cert)

        self._client = AsyncElasticsearch(**client_kwargs)

    async def validate_connection(self) -> bool:
        """Pings the cluster to verify connectivity and authentication."""
        if not self._client:
            raise RuntimeError("Must call connect() before validate_connection()")

        # Wrap ping in retry decorator to handle transient network issues
        async def _ping_with_retry() -> bool:
            # ping() returns True/False and doesn't raise on connection error,
            # so we use info() to explicitly raise an exception we can catch and retry on.
            await self._client.info() # type: ignore
            return True

        try:
            return await self._retry_decorator(_ping_with_retry)()
        except Exception as e:
            logger.error("Failed to validate connection", error=str(e))
            return False

    async def discover_sources(self, pattern: str) -> list[str]:
        """
        Discovers all indices or data streams matching the given pattern.
        No default pattern is assumed; the caller must explicitly provide one.
        """
        if not self._client:
            raise RuntimeError("Must call connect() before discover_sources()")

        if not pattern or not pattern.strip():
            raise ValueError("A valid index pattern must be explicitly provided.")

        async def _discover() -> list[str]:
            # Use the cat indices API (or index resolution)
            res = await self._client.indices.get_alias(index=pattern, ignore_unavailable=True) # type: ignore
            return list(res.keys())

        return await self._retry_decorator(_discover)()

    async def discover_fields(self, index: str) -> dict[str, Any]:
        """
        Returns the field mappings for the specified index.
        """
        if not self._client:
            raise RuntimeError("Must call connect() before discover_fields()")

        if not index or not index.strip():
            raise ValueError("A valid index must be explicitly provided.")

        async def _mapping() -> dict[str, Any]:
            res = await self._client.indices.get_mapping(index=index) # type: ignore
            # simplify the return structure
            if index in res:
                return dict(res[index].get("mappings", {}))
            return dict(res)

        return await self._retry_decorator(_mapping)()

    async def count_events(self, index: str, query: dict[str, Any] | None = None) -> int:
        """
        Counts the number of documents matching the query in the explicit index.
        """
        if not self._client:
            raise RuntimeError("Must call connect() before count_events()")

        if not index or not index.strip():
            raise ValueError("A valid index must be explicitly provided.")

        actual_query = query or {"match_all": {}}

        async def _count() -> int:
            res = await self._client.count(index=index, body={"query": actual_query}) # type: ignore
            return int(res["count"])

        return await self._retry_decorator(_count)()

    async def stream_events(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        batch_size: int = 5000,
        keep_alive: str = "2m"
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Streams events using the scroll API or Point in Time (PIT) / search_after.
        Yields batches of documents to prevent memory exhaustion.
        """
        if not self._client:
            raise RuntimeError("Must call connect() before stream_events()")

        if not index or not index.strip():
            raise ValueError("A valid index must be explicitly provided.")

        actual_query = query or {"match_all": {}}

        # We wrap the initial search in a retry block
        async def _initial_search() -> Any:
            return await self._client.search( # type: ignore
                index=index,
                body={"query": actual_query},
                scroll=keep_alive,
                size=batch_size,
            )

        res = await self._retry_decorator(_initial_search)()
        scroll_id = res.get("_scroll_id")
        hits = res.get("hits", {}).get("hits", [])

        while hits:
            yield [h["_source"] for h in hits]

            # Wrap scroll fetch in retry
            async def _scroll(s_id: str | None = scroll_id) -> Any:
                return await self._client.scroll(scroll_id=s_id, scroll=keep_alive) # type: ignore

            res = await self._retry_decorator(_scroll)()
            scroll_id = res.get("_scroll_id")
            hits = res.get("hits", {}).get("hits", [])

        if scroll_id:
            import contextlib
            # Best effort clear scroll
            with contextlib.suppress(Exception):
                await self._client.clear_scroll(scroll_id=scroll_id)

    async def close(self) -> None:
        """Closes the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
