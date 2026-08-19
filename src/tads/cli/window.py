import sys

import click

from tads.windowing.dataset import WindowDatasetBuilder
from tads.windowing.indexer import WindowIndexer


@click.group(name="window")
def window_group() -> None:
    """Temporal windowing commands."""


@window_group.command(name="index")
@click.option("--dataset", type=click.Choice(["july", "august"]), required=True, help="Target dataset namespace")
def run_index(dataset: str) -> None:
    """
    Generates a deterministic 5-second semantic window index for the dataset.
    Creates event_index.parquet and window_summary.parquet out-of-core.
    """
    click.echo(f"Starting Semantic Window Indexer for {dataset.upper()}...")
    try:
        indexer = WindowIndexer(dataset=dataset)
        results = indexer.generate_index()

        if not results:
            sys.exit(1)

        click.secho(f"\nSUCCESS: Generated deterministic semantic window indexes for {dataset.upper()}", fg="green", bold=True)
        click.echo(f"  Event Index:    {results['event_index']}")
        click.echo(f"  Window Summary: {results['window_summary']}")

    except Exception as e:
        click.secho(f"Window indexing failed: {e}", fg="red")
        sys.exit(1)


@window_group.command(name="build")
@click.option("--dataset", type=click.Choice(["july", "august"]), required=True, help="Target dataset namespace")
def run_build(dataset: str) -> None:
    """
    Builds the 5-second temporal window dataset from canonical Parquet events.
    Output: data/<dataset>/windows/window_dataset.parquet
    """
    click.echo(f"Building window dataset for {dataset.upper()}...")
    try:
        builder = WindowDatasetBuilder(dataset=dataset)
        result = builder.build()

        if result.get("status") == "no_data":
            click.secho("No data found.", fg="yellow")
            sys.exit(1)

        click.secho(f"\nSUCCESS: Window dataset built for {dataset.upper()}", fg="green", bold=True)
        click.echo(f"  Non-empty windows:  {result['non_empty_windows']}")
        click.echo(f"  Empty windows added: {result['empty_windows_added']}")
        click.echo(f"  Total windows:       {result['total_windows']}")
        click.echo(f"  Total events:        {result['total_events']}")
        click.echo(f"  Output:              {result['output_path']}")

    except Exception as e:
        click.secho(f"Window dataset build failed: {e}", fg="red")
        sys.exit(1)

