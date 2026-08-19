"""
TADS Constants

Project-wide constants encoding key constraints.
These values are the source of truth for constraint enforcement.
Changing any value here requires updating corresponding tests.
"""

from __future__ import annotations

from typing import Literal

# ============================================================
# Constraint #7: Primary temporal unit = 5-second window
# ============================================================
WINDOW_SIZE_SECONDS: int = 5
WINDOW_SIZE_MS: int = WINDOW_SIZE_SECONDS * 1000
ALLOWED_LATENESS_SECONDS: int = 60

# ============================================================
# Constraint #1, #2: READ-ONLY Kibana proxy access to ES
# Only these HTTP method + endpoint combinations are allowed.
# ============================================================
ES_ALLOWED_HTTP_METHODS: frozenset[str] = frozenset({"GET", "POST"})

# POST is only allowed for these endpoint patterns (search operations)
ES_ALLOWED_POST_ENDPOINTS: frozenset[str] = frozenset({
    "_search",
    "_msearch",
    "_scroll",
    "_pit",
    "_async_search",
    "_field_caps",
})

# These endpoints are NEVER allowed regardless of HTTP method
ES_FORBIDDEN_ENDPOINTS: frozenset[str] = frozenset({
    "_bulk",
    "_update",
    "_update_by_query",
    "_delete",
    "_delete_by_query",
    "_index",
    "_create",
    "_ilm",
    "_reindex",
    "_rollover",
    "_shrink",
    "_split",
    "_clone",
    "_close",
    "_open",
    "_aliases",
    "_mapping",  # PUT mapping is mutation
    "_settings",  # PUT settings is mutation
    "_template",
    "_index_template",
    "_component_template",
    "_snapshot",
    "_restore",
    "_ingest",
    "_enrich",
    "_transform",
    "_watch",
    "_slm",
})

# ============================================================
# Constraint #12: Normalization source must be "training"
# ============================================================
VALID_NORMALIZATION_SOURCES: frozenset[str] = frozenset({"training"})
FORBIDDEN_NORMALIZATION_SOURCES: frozenset[str] = frozenset({
    "batch",
    "evaluation",
    "current",
    "inference",
})

# ============================================================
# Constraint #16: Data format
# ============================================================
DATA_FORMAT: str = "parquet"
FORBIDDEN_DATA_FORMATS: frozenset[str] = frozenset({"csv", "tsv", "xlsx", "xls"})

# ============================================================
# Constraint #20: Reproducibility
# ============================================================
DEFAULT_SEED: int = 42
HASH_ALGORITHM: str = "sha256"
NUMERICAL_TOLERANCE: float = 1e-6

# ============================================================
# Constraint #19: Priority order for trade-off decisions
# ============================================================
PRIORITY_ORDER: tuple[str, ...] = (
    "correctness",
    "scientific_validity",
    "scalability",
    "detection_quality",
)

# ============================================================
# Data periods (Constraints #5, #6)
# ============================================================
TRAINING_PERIOD_LABEL: str = "july_baseline"
EVALUATION_PERIOD_LABEL: str = "august_unseen"

# ============================================================
# Parquet configuration (Constraints #15, #16)
# ============================================================
PARQUET_COMPRESSION: str = "zstd"
PARQUET_COMPRESSION_LEVEL: int = 3
PARQUET_ROW_GROUP_SIZE: int = 100_000

# ============================================================
# Dataset Isolation namespaces
# ============================================================

DatasetType = Literal["july", "august"]
