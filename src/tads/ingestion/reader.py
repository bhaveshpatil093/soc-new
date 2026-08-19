from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tads.schema.metadata import SourceMetadata

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
            "headers": self._settings.elastic_headers,
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

        return await self._retry_decorator(_ping_with_retry)()

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

    async def discover_source_metadata(self, index: str) -> "SourceMetadata":
        """
        Discovers detailed metadata for a given index, including field counts,
        timestamp candidates, min/max time bounds, and document count.
        """
        from tads.schema.metadata import SourceMetadata

        if not self._client:
            raise RuntimeError("Must call connect() before discover_source_metadata()")

        fields_mapping = await self.discover_fields(index)

        def get_date_fields(mapping: dict[str, Any], prefix: str = "") -> list[str]:
            date_fields: list[str] = []
            props = mapping.get("properties", {})
            for k, v in props.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if v.get("type") == "date":
                    date_fields.append(full_key)
                elif "properties" in v:
                    date_fields.extend(get_date_fields(v, full_key))
            return date_fields

        date_fields = get_date_fields(fields_mapping)
        primary_ts = "@timestamp" if "@timestamp" in date_fields else (date_fields[0] if date_fields else None)

        def count_fields(mapping: dict[str, Any]) -> int:
            count = 0
            for v in mapping.get("properties", {}).values():
                count += 1
                if "properties" in v:
                    count += count_fields(v)
            return count

        fields_count = count_fields(fields_mapping)

        earliest = None
        latest = None
        approx_count = None

        aggs = {}
        if primary_ts:
            aggs = {
                "min_ts": {"min": {"field": primary_ts, "format": "strict_date_optional_time"}},
                "max_ts": {"max": {"field": primary_ts, "format": "strict_date_optional_time"}}
            }

        async def _fetch_stats() -> dict[str, Any]:
            body = {"aggs": aggs} if aggs else {}
            # track_total_hits=True returns accurate count for small sets or bounded by 10k usually,
            # which is sufficient for "approximate_document_count"
            res = await self._client.search( # type: ignore
                index=index,
                size=0,
                track_total_hits=True,
                body=body
            )
            return dict(res)

        try:
            stats = await self._retry_decorator(_fetch_stats)()
            total = stats.get("hits", {}).get("total", {})
            approx_count = total.get("value") if isinstance(total, dict) else total

            aggs_result = stats.get("aggregations", {})
            if "min_ts" in aggs_result:
                earliest = aggs_result["min_ts"].get("value_as_string")
            if "max_ts" in aggs_result:
                latest = aggs_result["max_ts"].get("value_as_string")
        except Exception as e:
            logger.warning(f"Failed to fetch aggregations for {index}", error=str(e))

        return SourceMetadata(
            name=index,
            source_type="index",
            fields_count=fields_count,
            timestamp_candidates=date_fields,
            primary_timestamp_field=primary_ts,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
            approximate_document_count=approx_count
        )


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
        start_time: str,
        end_time: str,
        timestamp_field: str = "@timestamp",
        query: dict[str, Any] | None = None,
        batch_size: int = 5000,
        keep_alive: str = "2m",
        search_after: list[Any] | None = None,
        tiebreaker_field: str = "_id"
    ) -> AsyncIterator[tuple[list[dict[str, Any]], list[Any] | None]]:
        """
        Streams events using PIT (if supported) or search_after fallback.
        Yields tuples of (batch_of_documents, search_after_values).
        Time boundaries: start_time is inclusive (gte), end_time is exclusive (lt).
        """
        import contextlib

        if not self._client:
            raise RuntimeError("Must call connect() before stream_events()")

        if not index or not index.strip():
            raise ValueError("A valid index must be explicitly provided.")

        user_query = query or {"match_all": {}}

        # Combine user query with strict time bounds
        range_query = {
            "range": {
                timestamp_field: {
                    "gte": start_time,
                    "lt": end_time
                }
            }
        }

        full_query = {
            "bool": {
                "must": [user_query],
                "filter": [range_query]
            }
        }

        sort = [
            {timestamp_field: "asc"},
            {tiebreaker_field: "asc"}
        ]

        pit_id: str | None = None

        # Try to open PIT
        async def _open_pit() -> str | None:
            try:
                res = await self._client.open_point_in_time(index=index, keep_alive=keep_alive) # type: ignore
                return res.get("id")
            except Exception as e:
                logger.warning("PIT creation failed, falling back to standard search_after", error=str(e))
                return None

        pit_id = await self._retry_decorator(_open_pit)()

        current_search_after = search_after

        try:
            while True:
                async def _search_page(sa: list[Any] | None = None) -> dict[str, Any]:
                    body: dict[str, Any] = {
                        "query": full_query,
                        "sort": sort,
                        "size": batch_size
                    }
                    if sa:
                        body["search_after"] = sa

                    kwargs: dict[str, Any] = {"body": body}
                    if pit_id:
                        body["pit"] = {"id": pit_id, "keep_alive": keep_alive}
                        # When using PIT, index should not be specified
                    else:
                        kwargs["index"] = index

                    res = await self._client.search(**kwargs) # type: ignore
                    return dict(res)

                res = await self._retry_decorator(_search_page)(current_search_after)
                hits = res.get("hits", {}).get("hits", [])

                if not hits:
                    break

                # The search_after values for the next page come from the last document in the current page
                last_hit = hits[-1]
                next_search_after = last_hit.get("sort")

                # Yield full hits so _id and _source are preserved
                docs = hits

                yield docs, next_search_after

                current_search_after = next_search_after

                # If we got fewer hits than requested, we've reached the end
                if len(hits) < batch_size:
                    break

        finally:
            if pit_id:
                with contextlib.suppress(Exception):
                    await self._client.close_point_in_time(body={"id": pit_id})

    async def close(self) -> None:
        """Closes the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
