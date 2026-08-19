import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from tads.schema.canonical import SCHEMA_V1

logger = logging.getLogger(__name__)

class DatasetProfiler:
    """
    Scalable out-of-core dataset profiler using DuckDB.
    Calculates exact and approximate (HyperLogLog) metrics.
    """

    def __init__(self, dataset: str, run_id: str, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset
        self.run_id = run_id

        if base_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root
        else:
            self.base_dir = Path(base_dir)

        self.data_dir = self.base_dir / "data" / dataset / "raw"
        self.artifacts_dir = self.base_dir / "artifacts" / dataset / "profiles"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def profile(self) -> dict[str, Any]:
        """
        Executes profiling queries across the dataset.
        """
        pattern = str(self.data_dir / "*" / "*.parquet")

        import glob
        if not glob.glob(pattern):
            logger.warning(f"No parquet files found for {self.dataset} at {pattern}")
            return {}

        conn = duckdb.connect(database=':memory:')

        try:
            # Generate missingness projection queries dynamically from schema
            missing_cols = []
            for field in SCHEMA_V1.fields:
                col = field.name
                if col == "@timestamp":
                    col = '"@timestamp"'
                # COUNT(col) counts NON-NULLs
                alias = f"count_{field.name.replace('@', '')}"
                missing_cols.append(f"COUNT({col}) as {alias}")
            missing_projection = ",\n                ".join(missing_cols)

            # Query 1: Aggregates & Missingness & Cardinality (HLL)
            # Duplicate rate exact via COUNT(DISTINCT _id)
            query1 = f"""
            SELECT
                COUNT(*) as total_events,
                MIN("@timestamp") as min_ts,
                MAX("@timestamp") as max_ts,
                APPROX_COUNT_DISTINCT(user_name) as unique_users,
                APPROX_COUNT_DISTINCT(source_ip) + APPROX_COUNT_DISTINCT(destination_ip) as unique_ips,
                APPROX_COUNT_DISTINCT(host_name) as unique_hosts,
                APPROX_COUNT_DISTINCT(process_name) as unique_processes,
                COUNT(DISTINCT _id) as exact_unique_ids,
                {missing_projection}
            FROM '{pattern}'
            """

            result1 = conn.execute(query1).fetchone()

            if not result1:
                return {}

            total_events = result1[0]
            if total_events == 0:
                return {"total_events": 0}

            min_ts = result1[1].isoformat() if result1[1] else None
            max_ts = result1[2].isoformat() if result1[2] else None
            unique_users = result1[3]
            unique_ips = result1[4]
            unique_hosts = result1[5]
            unique_processes = result1[6]
            exact_unique_ids = result1[7]

            duplicate_rate = (1.0 - (exact_unique_ids / total_events)) * 100.0 if total_events > 0 else 0.0

            # Missingness processing
            missing_stats = {}
            col_offset = 8
            for idx, field in enumerate(SCHEMA_V1.fields):
                count_non_null = result1[col_offset + idx]
                pct_missing = ((total_events - count_non_null) / total_events) * 100.0
                missing_stats[field.name] = {
                    "missing_count": total_events - count_non_null,
                    "missing_percentage": pct_missing,
                    "flagged_review": pct_missing > 20.0
                }

            # Query 2: Event Category
            cat_rows = conn.execute(f"SELECT event_category, COUNT(*) FROM '{pattern}' GROUP BY event_category").fetchall()
            event_categories = {str(r[0]): r[1] for r in cat_rows}

            # Query 3: Event Outcome
            out_rows = conn.execute(f"SELECT event_outcome, COUNT(*) FROM '{pattern}' GROUP BY event_outcome").fetchall()
            event_outcomes = {str(r[0]): r[1] for r in out_rows}

            # Query 4: Daily Volume
            daily_rows = conn.execute(f"""
                SELECT date_trunc('day', "@timestamp") as bucket, COUNT(*)
                FROM '{pattern}'
                GROUP BY 1 ORDER BY 1
            """).fetchall()
            daily_volume = {r[0].isoformat(): r[1] for r in daily_rows if r[0]}

            # Query 5: Hourly Volume & Gap Detection
            hourly_rows = conn.execute(f"""
                SELECT date_trunc('hour', "@timestamp") as bucket, COUNT(*)
                FROM '{pattern}'
                GROUP BY 1 ORDER BY 1
            """).fetchall()
            hourly_volume = {r[0].isoformat(): r[1] for r in hourly_rows if r[0]}

            # Compile Profile
            profile_data = {
                "generated_at": datetime.now().isoformat(),
                "dataset": self.dataset,
                "run_id": self.run_id,
                "total_events": total_events,
                "timestamp_coverage": {
                    "min": min_ts,
                    "max": max_ts,
                    "daily_buckets": len(daily_volume),
                    "hourly_buckets": len(hourly_volume)
                },
                "unique_counts": {
                    "users_approx": unique_users,
                    "ips_approx": unique_ips,
                    "hosts_approx": unique_hosts,
                    "processes_approx": unique_processes
                },
                "duplicate_rate_percent": duplicate_rate,
                "missingness": missing_stats,
                "distributions": {
                    "event_category": event_categories,
                    "event_outcome": event_outcomes
                },
                "volume": {
                    "daily": daily_volume,
                    "hourly": hourly_volume
                }
            }

            # Save to JSON
            out_path = self.artifacts_dir / f"{self.run_id}_profile.json"
            with out_path.open('w') as f:
                json.dump(profile_data, f, indent=2)

            return profile_data

        finally:
            conn.close()

    def print_summary(self, profile: dict[str, Any]) -> None:
        """
        Prints a human-readable summary to the console, specifically highlighting
        flagged missingness fields >20%.
        """
        import click
        if not profile:
            click.echo("No profile generated.")
            return

        click.secho(f"\n=== Dataset Profile: {profile['dataset'].upper()} (Run: {profile['run_id']}) ===", bold=True, fg="cyan")
        click.echo(f"Total Events:    {profile['total_events']}")
        click.echo(f"Time Coverage:   {profile['timestamp_coverage']['min']} -> {profile['timestamp_coverage']['max']}")
        click.echo(f"Duplicate Rate:  {profile['duplicate_rate_percent']:.2f}% (Exact)")

        click.echo("\n--- Approximate Cardinalities (HyperLogLog) ---")
        click.echo(f"Unique Users:     {profile['unique_counts']['users_approx']}")
        click.echo(f"Unique IPs:       {profile['unique_counts']['ips_approx']}")
        click.echo(f"Unique Hosts:     {profile['unique_counts']['hosts_approx']}")
        click.echo(f"Unique Processes: {profile['unique_counts']['processes_approx']}")

        click.echo("\n--- Missing Fields Review ---")
        for field, stats in profile['missingness'].items():
            pct = stats['missing_percentage']
            if stats['flagged_review']:
                click.secho(f"  [FLAG] {field:<20}: {pct:6.2f}% missing (>20% threshold)", fg="red", bold=True)
            else:
                click.echo(f"  [OK]   {field:<20}: {pct:6.2f}% missing")

        click.echo(f"\nFull structured profile saved to: artifacts/{profile['dataset']}/profiles/{profile['run_id']}_profile.json")
