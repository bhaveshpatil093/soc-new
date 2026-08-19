import json
from datetime import datetime
from typing import Any

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

def coerce_hit_to_canonical(hit: dict[str, Any]) -> dict[str, Any]:
    """
    Takes a raw Elasticsearch hit and coerces it into a flat dictionary
    that strictly conforms to CANONICAL_RAW_SCHEMA based on SCHEMA_V1 rules.
    Unknown fields are stuffed into `raw_extra` as a JSON string.
    """
    _id = hit.get("_id")
    if not _id:
        raise ValueError("Hit is missing required field '_id'")

    source = hit.get("_source", {})

    # We must have a timestamp
    ts = source.pop("@timestamp", None)
    if not ts:
        # Check source_mapping fallbacks for timestamp just in case
        for f in SCHEMA_V1.fields:
            if f.name == "@timestamp":
                for path in f.source_mapping:
                    ts = _resolve_dot_notation(source, path)
                    if ts:
                        break
                break

    if not ts:
        raise ValueError(f"Hit {_id} is missing required field '@timestamp'")

    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
    except Exception as e:
        raise ValueError(f"Hit {_id} has invalid '@timestamp' format: {ts}") from e

    canonical_record = {
        "_id": str(_id),
        "@timestamp": dt,
    }

    # Keep track of fields we explicitly captured so we don't put them in raw_extra
    captured_paths = {"@timestamp"}

    for field in SCHEMA_V1.fields:
        if field.name in ("_id", "@timestamp"):
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
        canonical_record["raw_extra"] = json.dumps(source)
    else:
        canonical_record["raw_extra"] = None

    return canonical_record
