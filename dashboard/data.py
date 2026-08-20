"""
Thin reader layer for pre-computed TADS artifacts.

NO imports from tads.* are permitted in this module.
Only stdlib, pandas, pyarrow, and json are used.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
ANNOTATIONS_FILE = ARTIFACTS_DIR / "analyst_annotations.json"


# ── Experiment-level metadata ──────────────────────────────────────────────

def load_experiment_results() -> dict:
    """Load the full EXPERIMENT-TADS-V1 results JSON."""
    path = ARTIFACTS_DIR / "EXPERIMENT-TADS-V1_results.json"
    with open(path) as f:
        return json.load(f)


# ── Top-100 report ────────────────────────────────────────────────────────

def load_top100_parquet() -> pd.DataFrame:
    """Load the Top-100 Parquet and deserialise JSON-encoded columns."""
    df = pq.read_table(ARTIFACTS_DIR / "top100_report.parquet").to_pandas()
    # Deserialise JSON-string columns back to native Python objects
    for col in ("detector_agreement", "july_comparison",
                "novel_relationships", "affected_entities"):
        df[col] = df[col].apply(json.loads)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def load_top100_json() -> list[dict]:
    """Load the Top-100 JSON for full-fidelity drill-down."""
    with open(ARTIFACTS_DIR / "top100_report.json") as f:
        return json.load(f)


# ── Annotations (read / append-only) ──────────────────────────────────────

def load_annotations() -> dict[str, dict]:
    """Return {timestamp_iso -> annotation_dict}."""
    if not ANNOTATIONS_FILE.exists():
        return {}
    with open(ANNOTATIONS_FILE) as f:
        data = json.load(f)
    return {a["timestamp"]: a for a in data}


def save_annotation(timestamp: str, verdict: str, notes: str) -> None:
    """Append or update a single annotation.  This is the ONLY write op."""
    annotations = []
    if ANNOTATIONS_FILE.exists():
        with open(ANNOTATIONS_FILE) as f:
            annotations = json.load(f)

    # Upsert
    found = False
    for a in annotations:
        if a["timestamp"] == timestamp:
            a["verdict"] = verdict
            a["notes"] = notes
            a["updated_at"] = datetime.now(UTC).isoformat()
            found = True
            break
    if not found:
        annotations.append({
            "timestamp": timestamp,
            "verdict": verdict,
            "notes": notes,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        })

    with open(ANNOTATIONS_FILE, "w") as f:
        json.dump(annotations, f, indent=2)
