import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from dateutil.parser import parse as dateutil_parse

from tads.schema.canonical import SCHEMA_V1

# Define the canonical raw schema dynamically from the Pydantic definition.
CANONICAL_RAW_SCHEMA = SCHEMA_V1.generate_arrow_schema()

def _resolve_dot_notation(doc: dict[str, Any], path: str) -> Any:
    """Helper to traverse nested dicts using dot notation."""
    parts = path.split('.')
    current = doc
    for p in parts:
        if isinstance(current, dict) and p in current:
            current = current[p]
        else:
            return None
    return current

def normalize_timestamp(ts_val: Any) -> datetime:
    """
    Parses various timestamp formats (Epochs, ISO8601, native ES) and explicitly sets tzinfo=UTC.
    Raises ValueError on parsing failure, future bounds violation, or out-of-range bounds.
    """
    if ts_val is None:
        raise ValueError("MISSING_TIMESTAMP: timestamp value is None")

    dt = None
    if isinstance(ts_val, (int, float)):
        # Epoch handling. Check if it's millis or seconds.
        # 1e11 seconds is in year 5138, so anything larger is assumed to be millis.
        if ts_val > 1e11:
            ts_val = ts_val / 1000.0
        try:
            dt = datetime.fromtimestamp(ts_val, tz=UTC)
        except Exception as e:
            raise ValueError(f"INVALID_TIMESTAMP_FORMAT: Could not parse epoch {ts_val}") from e
    elif isinstance(ts_val, str):
        try:
            # Elasticsearch Z format handling
            if ts_val.endswith("Z"):
                ts_val_fixed = ts_val[:-1] + "+00:00"
                try:
                    dt = datetime.fromisoformat(ts_val_fixed)
                except ValueError:
                    dt = dateutil_parse(ts_val_fixed)
            else:
                try:
                    dt = datetime.fromisoformat(ts_val)
                except ValueError:
                    dt = dateutil_parse(ts_val)

            dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        except Exception as e:
            raise ValueError(f"INVALID_TIMESTAMP_FORMAT: Could not parse string {ts_val}") from e
    else:
        raise ValueError(f"INVALID_TIMESTAMP_FORMAT: Unsupported type {type(ts_val)}")

    # Bounds checking
    now = datetime.now(UTC)
    if dt > now + timedelta(hours=1):
        raise ValueError(f"FUTURE_TIMESTAMP: parsed {dt} is beyond tolerance of current time {now}")

    out_of_range_limit = datetime(2000, 1, 1, tzinfo=UTC)
    if dt < out_of_range_limit:
        raise ValueError(f"OUT_OF_RANGE_TIMESTAMP: parsed {dt} is older than limit {out_of_range_limit}")

    return dt

def compute_deterministic_id(record: dict[str, Any]) -> str:
    """
    Constructs a stable SHA-256 fingerprint from explicit canonical fields.
    Used as a fallback when Elasticsearch `_id` is missing or unstable.
    """
    # Use explicitly defined set of core fields
    fields = [
        str(record.get("@timestamp", "")),
        str(record.get("host_name", "") or record.get("host_ip", "")),
        str(record.get("event_category", "")),
        str(record.get("event_action", "")),
        str(record.get("process_name", "")),
    ]

    # Normalize message (strip whitespace, lowercase) to prevent trivial differences from breaking the hash
    msg = str(record.get("message", "")).strip().lower()
    fields.append(msg)

    fingerprint = "|".join(fields)
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

def coerce_hit_to_canonical(hit: dict[str, Any]) -> dict[str, Any]:
    """
    Takes a raw Elasticsearch hit and coerces it into a flat dictionary
    that strictly conforms to CANONICAL_RAW_SCHEMA based on SCHEMA_V1 rules.
    Unknown fields are stuffed into `raw_extra` as a JSON string.
    """
    _id = hit.get("_id")
    # We no longer raise an error for missing _id here. We generate it at the end if missing.

    source = hit.get("_source", {})

    # We must have a timestamp
    ts_val = source.pop("@timestamp", None)
    if not ts_val:
        # Check source_mapping fallbacks for timestamp just in case
        for f in SCHEMA_V1.fields:
            if f.name == "@timestamp":
                for path in f.source_mapping:
                    ts_val = _resolve_dot_notation(source, path)
                    if ts_val:
                        break
                break

    if not ts_val:
        raise ValueError("MISSING_TIMESTAMP: Hit is missing required field '@timestamp'")

    dt = normalize_timestamp(ts_val)

    canonical_record = {
        "@timestamp": dt,
        "raw_timestamp": str(ts_val),
    }

    if _id:
        canonical_record["_id"] = str(_id)

    # Keep track of fields we explicitly captured so we don't put them in raw_extra
    captured_paths = {"@timestamp"}

    for field in SCHEMA_V1.fields:
        if field.name in ("_id", "@timestamp", "raw_timestamp"):
            continue

        val = None
        for path in field.source_mapping:
            val = _resolve_dot_notation(source, path)
            if val is not None:
                captured_paths.add(path.split('.')[0]) # Simplified tracking
                break

        # Normalize
        if field.normalizer and val is not None:
            try:
                val = field.normalizer(val)
            except Exception:
                val = None
        elif val is not None:
            # Default coercion to string if no specific normalizer but field is a string
            import pyarrow as pa
            if pa.types.is_string(field.arrow_type):
                val = str(val)

        # Validate
        if field.validator and val is not None and not field.validator(val):
            raise ValueError(f"Hit {_id} failed validation rule '{field.validation_rule}' for field '{field.name}' with value '{val}'")

        if val is None and not field.nullable:
            raise ValueError(f"Hit {_id} is missing required field '{field.name}'")

        canonical_record[field.name] = val

    # Cleanup the top level source dict for raw_extra
    for top_key in captured_paths:
        source.pop(top_key, None)

    if source:
        canonical_record["raw_extra"] = json.dumps(source, default=str)
    else:
        canonical_record["raw_extra"] = None

    if not _id:
        canonical_record["_id"] = compute_deterministic_id(canonical_record)
    else:
        canonical_record["_id"] = str(_id)

    return canonical_record
