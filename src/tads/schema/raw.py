import json
from typing import Any

import pyarrow as pa

# Define the canonical raw schema.
# All extraction batches will be coerced to this schema before being written to Parquet.
CANONICAL_RAW_SCHEMA = pa.schema([
    pa.field("_id", pa.string(), nullable=False),
    pa.field("@timestamp", pa.timestamp('us', tz='UTC'), nullable=False),
    pa.field("event_id", pa.string(), nullable=True),
    pa.field("event_dataset", pa.string(), nullable=True),
    pa.field("event_category", pa.list_(pa.string()), nullable=True),
    pa.field("event_type", pa.list_(pa.string()), nullable=True),
    pa.field("user_name", pa.string(), nullable=True),
    pa.field("user_id", pa.string(), nullable=True),
    pa.field("source_ip", pa.string(), nullable=True),
    pa.field("destination_ip", pa.string(), nullable=True),
    pa.field("network_protocol", pa.string(), nullable=True),
    pa.field("raw_extra", pa.string(), nullable=True),  # JSON serialized unknown fields
])

def coerce_hit_to_canonical(hit: dict[str, Any]) -> dict[str, Any]:
    """
    Takes a raw Elasticsearch hit and coerces it into a flat dictionary
    that strictly conforms to CANONICAL_RAW_SCHEMA.
    Unknown fields are stuffed into `raw_extra` as a JSON string.
    """
    _id = hit.get("_id")
    if not _id:
        raise ValueError("Hit is missing required field '_id'")

    source = hit.get("_source", {})

    # We must have a timestamp. Often it's @timestamp, but discovery might have mapped it.
    # For now, we strictly require @timestamp in the source document.
    ts = source.pop("@timestamp", None)
    if not ts:
        # Fallback to check if it's in a different field, though prompt implies we map it
        raise ValueError(f"Hit {_id} is missing required field '@timestamp'")

    try:
        from datetime import datetime
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
    except Exception as e:
        raise ValueError(f"Hit {_id} has invalid '@timestamp' format: {ts}") from e

    # Extract known fields (flattened for PyArrow)
    event_dict = source.pop("event", {}) if isinstance(source.get("event"), dict) else {}
    user_dict = source.pop("user", {}) if isinstance(source.get("user"), dict) else {}
    src_dict = source.pop("source", {}) if isinstance(source.get("source"), dict) else {}
    dst_dict = source.pop("destination", {}) if isinstance(source.get("destination"), dict) else {}
    net_dict = source.pop("network", {}) if isinstance(source.get("network"), dict) else {}

    canonical_record = {
        "_id": str(_id),
        "@timestamp": dt,
        "event_id": str(event_dict.get("id")) if event_dict.get("id") is not None else None,
        "event_dataset": str(event_dict.get("dataset")) if event_dict.get("dataset") is not None else None,
        "event_category": event_dict.get("category"),  # Should be a list of strings
        "event_type": event_dict.get("type"),          # Should be a list of strings
        "user_name": str(user_dict.get("name")) if user_dict.get("name") is not None else None,
        "user_id": str(user_dict.get("id")) if user_dict.get("id") is not None else None,
        "source_ip": str(src_dict.get("ip")) if src_dict.get("ip") is not None else None,
        "destination_ip": str(dst_dict.get("ip")) if dst_dict.get("ip") is not None else None,
        "network_protocol": str(net_dict.get("protocol")) if net_dict.get("protocol") is not None else None,
    }

    # Any remaining fields in `source` were not explicitly captured above.
    # Pack them into raw_extra to avoid PyArrow schema inference crashes while preserving data.
    if source:
        canonical_record["raw_extra"] = json.dumps(source)
    else:
        canonical_record["raw_extra"] = None

    return canonical_record
