#!/usr/bin/env python3
"""
run_pipeline.py
================
Single entry point that runs the ENTIRE July -> August anomaly detection
pipeline end-to-end, in the exact order defined in the project spec
(Phase 0 -> Phase 12, corresponding to Prompt 74 "end-to-end production run").

This script does NOT contain any pipeline logic itself. It is a thin,
fail-fast orchestrator that calls your existing project's CLI commands
in sequence, one process per stage, and stops immediately if any stage
fails, exactly the way Prompt 74 requires ("Stop if leakage, schema
mismatch or artifact inconsistency is detected").

There is no demo mode, no sample-data mode, and no flag to skip real
Kibana/Elasticsearch extraction. It runs against real July and real
August data every time.

--------------------------------------------------------------------
BEFORE YOU RUN THIS ON THE OFFICE PC
--------------------------------------------------------------------
1. Edit the STAGES list below if your CLI commands / module name differ
   from `python -m anomaly_system ...`. Nothing else in this file needs
   to change if you only rename commands.
2. Set the required environment variables (do NOT hardcode them here):
     ELASTIC_HOST
     ELASTIC_USERNAME
     ELASTIC_PASSWORD
   Optionally:
     ELASTIC_CA_CERT, ELASTIC_VERIFY_TLS, ELASTIC_TIMEOUT
3. Set JULY_START / JULY_END / AUGUST_START / AUGUST_END below, or pass
   them as environment variables / CLI args -- see `--help`.
4. Run:  python run_pipeline.py
   Logs are written to ./pipeline_runs/<run_id>/ and to stdout.

--------------------------------------------------------------------
RESUMABILITY
--------------------------------------------------------------------
Each stage is expected to be independently idempotent/resumable per the
spec (checkpoints + manifests). This orchestrator additionally supports
`--start-from <stage_name>` so that if the office PC run dies at, say,
"train_models", you can restart from there instead of re-running
ingestion from scratch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ======================================================================
# CONFIG -- edit this block if your project's CLI differs
# ======================================================================

# The module your CLI is invoked with: `python -m <PACKAGE> <command> ...`
PACKAGE = "tads.cli.main"
INDEX = "logs-*"

# Required environment variables. The orchestrator refuses to start if any
# are missing -- it will NOT silently fall back to demo/sample data.
REQUIRED_ENV_VARS = ["ELASTIC_HOST", "ELASTIC_USERNAME", "ELASTIC_PASSWORD"]

# Date ranges. Prefer setting these via environment variables so the
# script itself never has to be edited for a new run; hardcoded fallbacks
# below are placeholders -- CHANGE THEM before running, or export the
# env vars.
JULY_START = os.environ.get("JULY_START", "2025-07-01T00:00:00Z")
JULY_END = os.environ.get("JULY_END", "2025-08-01T00:00:00Z")
AUGUST_START = os.environ.get("AUGUST_START", "2025-08-01T00:00:00Z")
AUGUST_END = os.environ.get("AUGUST_END", "2025-09-01T00:00:00Z")


@dataclass
class Stage:
    name: str                       # unique short id, used for --start-from
    description: str                # human-readable label for logs
    command: list[str]              # argv, without the leading [sys.executable, -m, PACKAGE]
    required: bool = True           # if False, a failure is logged but does not stop the run


# The full pipeline mapped to our CLI:
STAGES: list[Stage] = [
    Stage("test_connection", "Validate read-only Kibana/Elasticsearch connection",
          ["ingest", "test-connection"]),

    Stage("ingest_july", "Extract July -> raw Parquet + manifest",
          ["ingest", "run", "--dataset", "july", "--index", INDEX, "--start", JULY_START, "--end", JULY_END, "--run-id", "july_full"]),

    Stage("data_quality_july", "July data quality / profiling report",
          ["profile", "run", "--dataset", "july", "--run-id", "july_full"]),

    Stage("windows_july_index", "Assign July events to semantic index",
          ["window", "index", "--dataset", "july"]),

    Stage("windows_july_build", "Assign July events to 5-second windows",
          ["window", "build", "--dataset", "july"]),

    Stage("train_models", "Train Isolation Forest, Autoencoder, Sequence model, PCA, etc. on July",
          ["pipeline", "train"]),

    Stage("ingest_august", "Extract August -> raw Parquet + manifest (independent of July)",
          ["ingest", "run", "--dataset", "august", "--index", INDEX, "--start", AUGUST_START, "--end", AUGUST_END, "--run-id", "august_full"]),

    Stage("data_quality_august", "August data quality / profiling report",
          ["profile", "run", "--dataset", "august", "--run-id", "august_full"]),

    Stage("windows_august_index", "Assign August events to semantic index",
          ["window", "index", "--dataset", "august"]),

    Stage("windows_august_build", "Assign August events to 5-second windows",
          ["window", "build", "--dataset", "august"]),

    Stage("infer_august", "Frozen-artifact blind inference over August",
          ["pipeline", "infer"]),

    Stage("generate_reports", "Generate final results package + Top-100 report",
          ["pipeline", "report"]),

    Stage("dashboard", "Launch Streamlit dashboard",
          ["pipeline", "dashboard"], required=False),
]


# ======================================================================
# Orchestrator internals -- should not normally need editing
# ======================================================================

def check_environment() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"[FATAL] Missing required environment variable(s): {', '.join(missing)}")
        print("        This pipeline only runs against real Kibana/Elasticsearch data.")
        print("        Set these before running, e.g.:")
        for v in missing:
            print(f"          export {v}=...")
        sys.exit(1)


def make_run_dir() -> Path:
    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path("pipeline_runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_stage(stage: Stage, run_dir: Path) -> tuple[bool, float]:
    log_path = run_dir / f"{stage.name}.log"
    
    # Prepend project root to PYTHONPATH so `tads` module can be resolved
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parent)
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
    
    cmd = [sys.executable, "-m", PACKAGE] + stage.command

    print(f"\n{'=' * 70}")
    print(f"[STAGE] {stage.name} -- {stage.description}")
    print(f"[CMD]   {' '.join(cmd)}")
    print(f"[LOG]   {log_path}")
    print(f"{'=' * 70}")

    start = dt.datetime.now(dt.UTC)
    with open(log_path, "w") as log_file:
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
        )
    duration = (dt.datetime.now(dt.UTC) - start).total_seconds()

    ok = result.returncode == 0
    status = "OK" if ok else f"FAILED (exit {result.returncode})"
    print(f"[RESULT] {stage.name}: {status} in {duration:.1f}s")

    if not ok:
        print(f"[RESULT] Last 40 lines of {log_path}:")
        try:
            with open(log_path) as f:
                lines = f.readlines()
            for line in lines[-40:]:
                print("    " + line.rstrip())
        except OSError:
            pass

    return ok, duration


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full anomaly-detection pipeline end-to-end.")
    parser.add_argument(
        "--start-from",
        default=None,
        help="Stage name to resume from (skips all earlier stages). "
             f"Valid names: {', '.join(s.name for s in STAGES)}",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Run only this single stage (for debugging one step).",
    )
    args = parser.parse_args()

    check_environment()

    stages_to_run = STAGES
    if args.only:
        stages_to_run = [s for s in STAGES if s.name == args.only]
        if not stages_to_run:
            print(f"[FATAL] Unknown stage name: {args.only}")
            sys.exit(1)
    elif args.start_from:
        names = [s.name for s in STAGES]
        if args.start_from not in names:
            print(f"[FATAL] Unknown stage name: {args.start_from}")
            sys.exit(1)
        stages_to_run = STAGES[names.index(args.start_from):]

    run_dir = make_run_dir()
    print(f"[INFO] Run directory: {run_dir.resolve()}")
    print(f"[INFO] Package under test: {PACKAGE}")
    print(f"[INFO] July range:   {JULY_START} -> {JULY_END}")
    print(f"[INFO] August range: {AUGUST_START} -> {AUGUST_END}")
    print(f"[INFO] Stages queued: {len(stages_to_run)}")

    summary: list[dict] = []
    overall_start = dt.datetime.now(dt.UTC)

    for stage in stages_to_run:
        ok, duration = run_stage(stage, run_dir)
        summary.append({
            "stage": stage.name,
            "description": stage.description,
            "ok": ok,
            "duration_sec": duration,
            "required": stage.required,
        })

        if not ok:
            if stage.required:
                print(f"\n[FATAL] Required stage '{stage.name}' failed. Stopping pipeline.")
                print(f"        Fix the issue, then resume with:")
                print(f"          python {Path(__file__).name} --start-from {stage.name}")
                _write_summary(run_dir, summary, overall_start, aborted=True)
                sys.exit(1)
            else:
                print(f"[WARN] Optional stage '{stage.name}' failed. Continuing.")

    _write_summary(run_dir, summary, overall_start, aborted=False)
    print(f"\n[DONE] Pipeline completed. Summary: {run_dir / 'summary.json'}")


def _write_summary(run_dir: Path, summary: list[dict], overall_start: dt.datetime, aborted: bool) -> None:
    total_duration = (dt.datetime.now(dt.UTC) - overall_start).total_seconds()
    payload = {
        "aborted": aborted,
        "total_duration_sec": total_duration,
        "stages": summary,
    }
    with open(run_dir / "summary.json", "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
