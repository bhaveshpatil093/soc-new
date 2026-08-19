import asyncio
import sys
import typing

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

@discover_group.command(name="mapping")
@click.argument("index")
def discover_mapping(index: str) -> None:
    """
    Inspect the schema of INDEX and map it against the canonical internal fields.
    """
    click.echo(f"--- Schema Inspection: {index} ---")
    try:
        settings = get_settings()
    except Exception as e:
        click.secho(f"Configuration Error: {e}", fg="red")
        sys.exit(10)

    asyncio.run(_run_mapping(settings, index))

async def _run_mapping(settings: Settings, index: str) -> None:
    from tads.schema.mapping import SchemaInspector
    source = ReadOnlyElasticSource(settings=settings)

    click.echo("Connecting and fetching mapping...")
    try:
        await source.connect()
        fields_mapping = await source.discover_fields(index)

        # Flatten the mapping to just field names for the inspector
        # The reader.py already has a recursive get_date_fields, let's write a generic flat field extractor
        def _extract_all_fields(mapping_dict: dict[str, typing.Any], prefix: str = "") -> list[str]:
            fields = []
            props = mapping_dict.get("properties", {})
            for k, v in props.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if "properties" in v:
                    fields.extend(_extract_all_fields(v, full_key))
                else:
                    fields.append(full_key)
            return fields

        flat_fields = _extract_all_fields(fields_mapping)
        if not flat_fields:
            click.secho(f"No fields found in index '{index}'.", fg="yellow")
            sys.exit(0)

        inspector = SchemaInspector()
        report = inspector.inspect_and_map(flat_fields)

        click.echo("\n[ Mapped Fields ]")
        for source_f, canonical_f in report.mapped_fields.items():
            click.echo(f"  {source_f} -> {canonical_f}")

        click.echo(f"\n[ Missing Canonical Fields ] ({len(report.missing_canonical_fields)})")
        for m in report.missing_canonical_fields:
            click.secho(f"  {m}", fg="yellow")

        click.echo(f"\n[ Unmapped Source Fields (Raw/Extra) ] ({len(report.unmapped_fields)})")
        # Just show a sample if too many
        display_unmapped = report.unmapped_fields[:15]
        for u in display_unmapped:
            click.echo(f"  {u}")
        if len(report.unmapped_fields) > 15:
            click.echo(f"  ... and {len(report.unmapped_fields) - 15} more.")

        click.echo("\n[ Summary ]")
        click.echo(f"  Coverage: {report.coverage_percentage:.1f}% of canonical schema resolved.")
        click.echo(
            f"  Source fields preserved: {len(report.mapped_fields)} mapped + "
            f"{len(report.unmapped_fields)} unmapped = {len(flat_fields)} total."
        )

    except Exception as e:
        click.secho(f"Error during mapping inspection: {e}", fg="red")
        sys.exit(1)
    finally:
        await source.close()
