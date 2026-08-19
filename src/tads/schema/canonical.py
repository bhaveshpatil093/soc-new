from collections.abc import Callable
from typing import Any

import pyarrow as pa
from pydantic import BaseModel, Field


class CanonicalField(BaseModel):
    name: str = Field(..., description="Flat column name in the canonical schema (e.g. source_ip)")
    arrow_type: Any = Field(..., description="PyArrow data type")
    nullable: bool = Field(..., description="Whether the field is optional")
    source_mapping: list[str] = Field(..., description="List of dot-notation paths in source to check (priority order)")
    normalization_rule: str = Field(..., description="Human readable description of transformation")
    validation_rule: str = Field(..., description="Human readable description of validation logic")

    # Optional runtime hooks
    validator: Callable[[Any], bool] | None = Field(default=None, exclude=True)
    normalizer: Callable[[Any], Any] | None = Field(default=None, exclude=True)


class CanonicalSchema(BaseModel):
    version: int = Field(..., description="Schema version identifier")
    fields: list[CanonicalField] = Field(..., description="List of all defined fields")

    def generate_arrow_schema(self) -> pa.Schema:
        """Dynamically builds the PyArrow schema from the canonical definitions."""
        arrow_fields = []
        for field in self.fields:
            arrow_fields.append(pa.field(field.name, field.arrow_type, nullable=field.nullable))

        # Add the required extra payload catch-all
        arrow_fields.append(pa.field("raw_extra", pa.string(), nullable=True))

        return pa.schema(arrow_fields)

# ============================================================
# Helpers
# ============================================================
def validate_ip(ip_str: str) -> bool:
    if not isinstance(ip_str, str):
        return False
    # Extremely basic IP validation just to prove the validation rule functions
    # (In a real system, use ipaddress module)
    import ipaddress
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def normalize_list(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v) for v in val]
    return [str(val)] if val is not None else []

# ============================================================
# SCHEMA V1
# ============================================================

SCHEMA_V1 = CanonicalSchema(
    version=1,
    fields=[
        CanonicalField(
            name="_id",
            arrow_type=pa.string(),
            nullable=False,
            source_mapping=["_id"],
            normalization_rule="String coercion",
            validation_rule="Must not be empty",
            validator=lambda x: bool(x)
        ),
        CanonicalField(
            name="@timestamp",
            arrow_type=pa.timestamp('us', tz='UTC'),
            nullable=False,
            source_mapping=["@timestamp", "timestamp"],
            normalization_rule="Robust parsing into UTC datetime",
            validation_rule="Must be a valid historical timestamp (not future, not absurdly old)",
            # Complex timestamp normalization happens directly in coerce_hit_to_canonical
        ),
        CanonicalField(
            name="raw_timestamp",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=[], # We explicitly handle this in raw.py
            normalization_rule="String coercion of the original timestamp value",
            validation_rule="None",
        ),
        CanonicalField(
            name="event_id",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["event.id", "id"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="event_action",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["event.action", "action"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="event_category",
            arrow_type=pa.list_(pa.string()),
            nullable=True,
            source_mapping=["event.category", "category"],
            normalization_rule="Ensure list of strings",
            validation_rule="None",
            normalizer=normalize_list
        ),
        CanonicalField(
            name="event_type",
            arrow_type=pa.list_(pa.string()),
            nullable=True,
            source_mapping=["event.type", "type"],
            normalization_rule="Ensure list of strings",
            validation_rule="None",
            normalizer=normalize_list
        ),
        CanonicalField(
            name="event_outcome",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["event.outcome", "outcome"],
            normalization_rule="String coercion, lowercase",
            validation_rule="success, failure, unknown",
            normalizer=lambda x: str(x).lower() if x else None
        ),
        CanonicalField(
            name="user_name",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["user.name", "user"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="user_id",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["user.id"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="source_ip",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["source.ip", "src_ip"],
            normalization_rule="String coercion",
            validation_rule="Must be a valid IPv4 or IPv6 string",
            validator=validate_ip
        ),
        CanonicalField(
            name="source_port",
            arrow_type=pa.int64(),
            nullable=True,
            source_mapping=["source.port", "src_port"],
            normalization_rule="Integer coercion",
            validation_rule="Must be between 0 and 65535",
            validator=lambda x: isinstance(x, int) and 0 <= x <= 65535,
            normalizer=lambda x: int(x) if x is not None else None
        ),
        CanonicalField(
            name="destination_ip",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["destination.ip", "dest_ip", "dst_ip"],
            normalization_rule="String coercion",
            validation_rule="Must be a valid IPv4 or IPv6 string",
            validator=validate_ip
        ),
        CanonicalField(
            name="destination_port",
            arrow_type=pa.int64(),
            nullable=True,
            source_mapping=["destination.port", "dest_port", "dst_port"],
            normalization_rule="Integer coercion",
            validation_rule="Must be between 0 and 65535",
            validator=lambda x: isinstance(x, int) and 0 <= x <= 65535,
            normalizer=lambda x: int(x) if x is not None else None
        ),
        CanonicalField(
            name="host_name",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["host.name", "hostname"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="host_ip",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["host.ip"],
            normalization_rule="String coercion",
            validation_rule="Must be a valid IPv4 or IPv6 string",
            validator=validate_ip
        ),
        CanonicalField(
            name="process_name",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["process.name", "proc_name"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="process_command_line",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["process.command_line", "command_line"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="process_parent_name",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["process.parent.name", "parent_process_name"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="network_protocol",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["network.protocol", "protocol"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="file_path",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["file.path"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="log_level",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["log.level", "level"],
            normalization_rule="String coercion, uppercase",
            validation_rule="None",
            normalizer=lambda x: str(x).upper() if x else None
        ),
        CanonicalField(
            name="message",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["message", "msg"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
        CanonicalField(
            name="agent_id",
            arrow_type=pa.string(),
            nullable=True,
            source_mapping=["agent.id"],
            normalization_rule="String coercion",
            validation_rule="None",
        ),
    ]
)
