# ──────────────────────────────────────────────────────────────────────────────
# TADS Investigation Dashboard
#
# DESIGN RULE: This package has ZERO imports from
#   tads.ingestion, tads.features, tads.models, tads.inference, tads.storage,
#   tads.baselines, tads.cli, tads.schema, tads.windowing
#
# It reads ONLY from pre-generated artifacts (Parquet / JSON) and may only
# APPEND analyst annotations. It never writes to model, feature, or baseline
# artifacts.
# ──────────────────────────────────────────────────────────────────────────────
