import asyncio
import sys

import click
from pydantic import ValidationError

from tads.ingestion.reader import ReadOnlyElasticSource
from tads.schema.settings import Settings, get_settings


@click.group(name="discover")
def discover_group() -> None:
    """Commands related to data source discovery."""
    pass

@discover_group.command(name="sources")
@click.argument("pattern")
def discover_sources(pattern: str) -> None:
    """
    Discover indices and data streams matching the given PATTERN.
    """
    click.echo(f"--- Discovery: {pattern} ---")
    try:
        settings = get_settings()
    except ValidationError as e:
        click.secho(f"Configuration Error:\n{e}", fg="red")
        sys.exit(10)
    except Exception as e:
        click.secho(f"Configuration Error: {e}", fg="red")
        sys.exit(10)

    asyncio.run(_run_discovery(settings, pattern))

async def _run_discovery(settings: Settings, pattern: str) -> None:
    source = ReadOnlyElasticSource(settings=settings)

    click.echo("Connecting...")
    try:
        await source.connect()
        indices = await source.discover_sources(pattern)
        if not indices:
            click.secho(f"No sources found matching '{pattern}'.", fg="yellow")
            sys.exit(0)

        click.secho(f"Found {len(indices)} matching sources. Fetching metadata...", fg="green")

        for index in indices:
            click.echo(f"\nAnalyzing: {index}")
            metadata = await source.discover_source_metadata(index)

            click.echo(f"  Name:       {metadata.name}")
            click.echo(f"  Type:       {metadata.source_type}")
            click.echo(f"  Fields:     {metadata.fields_count}")

            if metadata.timestamp_candidates:
                click.echo(f"  Timestamps: {', '.join(metadata.timestamp_candidates)}")
            else:
                click.secho("  Timestamps: no timestamp candidate found", fg="yellow")

            if metadata.primary_timestamp_field:
                click.echo(f"  Primary TS: {metadata.primary_timestamp_field}")
                click.echo(f"  Earliest:   {metadata.earliest_timestamp or 'Unknown'}")
                click.echo(f"  Latest:     {metadata.latest_timestamp or 'Unknown'}")

            if metadata.approximate_document_count is not None:
                click.echo(f"  Docs count: ~{metadata.approximate_document_count}")
            else:
                click.echo("  Docs count: Unknown")

    except Exception as e:
        click.secho(f"Error during discovery: {e}", fg="red")
        sys.exit(1)
    finally:
        await source.close()

    click.echo("\n--- Discovery Complete ---")
