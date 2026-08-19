import sys

import click

from tads.profiling.profiler import DatasetProfiler


@click.group(name="profile")
def profile_group() -> None:
    """Dataset profiling commands."""
    pass

@profile_group.command(name="run")
@click.option("--dataset", type=click.Choice(["july", "august"]), required=True, help="Target dataset namespace")
@click.option("--run-id", required=True, help="Run ID of the extraction to profile")
def run_profile(dataset: str, run_id: str) -> None:
    """
    Profile the parquets extracted for a given dataset/run-id.
    Calculates coverage, missingness, and cardinality.
    """
    click.echo(f"Starting Dataset Profiler for {dataset.upper()} (Run ID: {run_id})...")
    try:
        profiler = DatasetProfiler(dataset=dataset, run_id=run_id)
        profile_data = profiler.profile()

        if not profile_data:
            sys.exit(1)

        profiler.print_summary(profile_data)

    except Exception as e:
        click.secho(f"Profiling failed: {e}", fg="red")
        sys.exit(1)
