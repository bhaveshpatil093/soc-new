
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    """Metadata describing an automatically discovered data source in Elasticsearch."""

    name: str = Field(..., description="The name of the index or data stream")
    source_type: str = Field(..., description="Type of source (e.g., 'index', 'data_stream', 'alias')")
    fields_count: int = Field(..., description="Total number of mapped fields in the source")
    timestamp_candidates: list[str] = Field(
        default_factory=list,
        description="List of fields identified as 'date' type suitable for windowing"
    )
    primary_timestamp_field: str | None = Field(
        default=None,
        description="The field selected for temporal aggregations (usually @timestamp or first candidate)"
    )
    earliest_timestamp: str | None = Field(
        default=None,
        description="ISO8601 string of the earliest document timestamp (if determinable)"
    )
    latest_timestamp: str | None = Field(
        default=None,
        description="ISO8601 string of the latest document timestamp (if determinable)"
    )
    approximate_document_count: int | None = Field(
        default=None,
        description="Approximate document count retrieved safely (e.g., track_total_hits max limit or exact if small)"
    )
