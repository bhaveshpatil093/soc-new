import sys

import click

from tads.windowing.indexer import WindowIndexer


@click.group(name="window")
def window_group() -> None:
    """Temporal windowing commands."""
    pass

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
