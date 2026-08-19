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

# --- Empty window policy ---
# When True, empty 5-second windows (zero events) are explicitly materialized as
# rows with event_count=0 and null/zero feature values in the window summary.
# This preserves temporal continuity for the sequence model (Prompt 45):
# the model must "see" silence as signal — a sudden gap from 50 events/window
# to 0 events/window is itself anomalous.  Dropping empty windows would corrupt
# the regular 5-second spacing and make consecutive silence invisible.
#
# When False, empty windows are absent from the dataset and must be
# reconstructed on demand.  Use only if the downstream model explicitly
# handles irregular time series (e.g. event-driven, not tick-driven).
#
# This constant is the SINGLE configurable point — no other module should
# independently decide whether to include or exclude empty windows.
MATERIALIZE_EMPTY_WINDOWS: bool = True

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
