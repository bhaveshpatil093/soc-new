import asyncio
import sys
from typing import Any

import click
from elastic_transport import ConnectionError as ESConnectionError
from elastic_transport import ConnectionTimeout, TlsError
from elasticsearch.exceptions import AuthenticationException, AuthorizationException, NotFoundError
from pydantic import ValidationError

from tads.ingestion.reader import ReadOnlyElasticSource
from tads.schema.settings import Settings, get_settings


@click.group(name="ingest")
def ingest_group() -> None:
    """Commands related to data ingestion."""
    pass

@ingest_group.command(name="test-connection")
@click.option("--index", default="*", help="Index pattern to test (default: *)")
def test_connection(index: str) -> None:
    """
    Test the Elasticsearch connection and diagnostic status.
    """
    click.echo("--- Diagnostic: Elasticsearch Connection ---")

    try:
        settings = get_settings()
    except ValidationError as e:
        click.secho(f"Configuration Error:\n{e}", fg="red")
        sys.exit(10)
    except Exception as e:
        # Important: Don't echo arbitrary exceptions that might contain raw settings values
        # just in case pydantic raises a standard ValueError without scrubbing.
        # (Though our get_settings() function scrubs it for us).
        click.secho(f"Configuration Error: {e}", fg="red")
        sys.exit(10)

    asyncio.run(_run_test_connection(settings, index))

async def _run_test_connection(settings: Settings, index_pattern: str) -> None:
    # Use explicitly low retries for diagnostics so user isn't hanging
    source = ReadOnlyElasticSource(settings=settings, max_retries=1, min_backoff_sec=0.1, max_backoff_sec=1.0)

    click.echo(f"Host: {settings.elastic_host}")
    click.echo("Connecting...")

    try:
        await source.connect()
        # validate_connection() pings the info endpoint
        valid = await source.validate_connection()
        if not valid:
            click.secho("Validation returned false without an exception.", fg="yellow")

        click.secho("Connection Status: OK", fg="green")
        click.secho("Authentication Status: OK", fg="green")
        click.secho("Authorization Status: OK", fg="green")

        # 2. Available data sources
        click.echo(f"\nDiscovering sources matching '{index_pattern}'...")
        sources = await source.discover_sources(pattern=index_pattern)
        if not sources:
            click.secho(f"[404] Not Found: Target '{index_pattern}' matched no indices or data streams.", fg="red", bold=True)
            sys.exit(13)

        click.echo(f"Available data sources ({len(sources)} found):")
        for s in sources[:5]:
            click.echo(f"  - {s}")
        if len(sources) > 5:
            click.echo(f"  - ... and {len(sources) - 5} more")

        # 3. Discover fields
        click.echo("\nDiscovering fields in first matched source...")
        first_source = sources[0]
        fields = await source.discover_fields(first_source)

        # Flatten properties briefly to find timestamps
        def get_date_fields(mapping: dict[str, Any], prefix: str = "") -> list[str]:
            date_fields: list[str] = []
            props = mapping.get("properties", {})
            for k, v in props.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if v.get("type") == "date":
                    date_fields.append(full_key)
                elif "properties" in v:
                    date_fields.extend(get_date_fields(v, full_key))
            return date_fields

        ts_fields = get_date_fields(fields)
        if ts_fields:
            click.secho(f"Timestamp fields found: {', '.join(ts_fields)}", fg="green")
        else:
            click.secho("Warning: No 'date' fields discovered in mapping.", fg="yellow")

        # 4. Count and sample
        click.echo("\nChecking event availability...")
        count = await source.count_events(first_source)
        click.echo(f"Total events in {first_source}: {count}")

        if count > 0:
            click.secho("Sample event availability: YES (Data is present)", fg="green")
        else:
            click.secho("Sample event availability: NO (Index is empty)", fg="yellow")

    except AuthenticationException:
        click.secho("[401] Authentication Failed: Check your ELASTIC_USERNAME and ELASTIC_PASSWORD.", fg="red", bold=True)
        sys.exit(11)
    except AuthorizationException:
        click.secho("[403] Authorization Failed: Your account lacks required privileges.", fg="red", bold=True)
        sys.exit(12)
    except NotFoundError:
        click.secho(f"[404] Not Found: Target '{index_pattern}' could not be found. Check your configuration.", fg="red", bold=True)
        sys.exit(13)
    except ConnectionTimeout:
        click.secho("Timeout: Connection or read timeout. Check network routing and latency.", fg="red", bold=True)
        sys.exit(14)
    except TlsError:
        click.secho("TLS Failure: Certificate validation failed. Check ELASTIC_CA_CERT or ELASTIC_VERIFY_TLS.", fg="red", bold=True)
        sys.exit(15)
    except ESConnectionError as e:
        err_str = str(e).lower()
        if "dnserror" in err_str or "nodename nor servname provided" in err_str or "name or service not known" in err_str:
            click.secho("DNS Failure: Host could not be resolved. Check your DNS settings or ELASTIC_HOST URL.", fg="red", bold=True)
            sys.exit(16)
        else:
            click.secho("Connection Refused: Host reachable but port/service is not accepting connections.", fg="red", bold=True)
            sys.exit(17)
    except Exception:
        # Fallback for unexpected errors. Make sure not to leak credentials in the string repr.
        click.secho("An unexpected error occurred.", fg="red")
        sys.exit(1)
    finally:
        await source.close()

    click.echo("\n--- Diagnostic Complete ---")

@ingest_group.command(name="run")
@click.option("--dataset", type=click.Choice(["july", "august"]), required=True, help="Target dataset namespace")
@click.option("--index", required=True, help="Elasticsearch index or data stream pattern")
@click.option("--start", required=True, help="ISO8601 start time (inclusive)")
@click.option("--end", required=True, help="ISO8601 end time (exclusive)")
@click.option("--batch-size", default=5000, help="Number of documents per page")
@click.option("--run-id", default="default", help="Identifier for checkpointing")
def run_ingest(dataset: str, index: str, start: str, end: str, batch_size: int, run_id: str) -> None:
    """
    Run scalable event extraction with resumability and checkpoints.
    """
    click.echo(f"--- Starting Extraction: {index} into {dataset} ---")
    try:
        settings = get_settings()
    except Exception as e:
        click.secho(f"Configuration Error: {e}", fg="red")
        sys.exit(10)

    try:
        asyncio.run(_run_extraction(settings, dataset, index, start, end, batch_size, run_id))
    except KeyboardInterrupt:
        click.secho("\nProcess interrupted by user (SIGINT).", fg="yellow")
        sys.exit(130)

async def _run_extraction(settings: Settings, dataset: Any, index: str, start: str, end: str, batch_size: int, run_id: str) -> None:
    import datetime
    import time

    from tads.ingestion.checkpoint import CheckpointManager, ExtractionCheckpoint
    from tads.ingestion.manifest import ManifestBuilder
    from tads.storage.writer import ParquetStorage

    # Check for existing completed manifest first (Idempotency)
    manifest_builder = ManifestBuilder(dataset=dataset)
    try:
        existing_manifest = manifest_builder.load(run_id)
        if existing_manifest.status == "COMPLETED":
            click.secho(f"\nManifest '{run_id}' is already COMPLETED. Skipping extraction.", fg="green")
            click.secho("\n--- Ingestion Summary ---", fg="cyan", bold=True)
            click.echo(f"Run ID:        {existing_manifest.run_id}")
            click.echo(f"Source:        {existing_manifest.source}")
            click.echo(f"Duration:      {existing_manifest.duration_seconds:.2f}s")

            throughput = 0.0
            if existing_manifest.duration_seconds > 0:
                throughput = existing_manifest.event_count / existing_manifest.duration_seconds
            click.echo(f"Throughput:    {throughput:.2f} events/sec")

            click.echo(f"Extracted:     {existing_manifest.event_count} events")
            if existing_manifest.dropped_events:
                click.echo("Dropped Events:")
                for reason, count in existing_manifest.dropped_events.items():
                    click.echo(f"  - {reason}: {count}")
            click.echo(f"Partitions:    {existing_manifest.partition_count}")
            click.echo(f"Schema Hash:   {existing_manifest.schema_hash}")
            return
    except FileNotFoundError:
        pass

    source = ReadOnlyElasticSource(settings=settings)
    manager = CheckpointManager(dataset=dataset)
    writer = ParquetStorage(dataset=dataset)

    # We define the partition string from the start date (e.g. "2024-07")
    partition = start[:7] if len(start) >= 7 else "default"

    files_written: list[Any] = []
    actual_min_ts = None
    actual_max_ts = None
    total_dropped: dict[str, int] = {}

    # Check for existing checkpoint
    checkpoint = manager.load(run_id)
    if checkpoint:
        click.secho(f"Resuming from checkpoint '{run_id}'. Documents processed: {checkpoint.event_count}", fg="green")
        if checkpoint.source != index or checkpoint.time_range.get("start") != start or checkpoint.time_range.get("end") != end:
            click.secho("Warning: Current run parameters differ from checkpoint parameters!", fg="yellow")
        search_after = checkpoint.search_after
        docs_processed = checkpoint.event_count
    else:
        click.echo("No checkpoint found. Starting fresh extraction.")
        search_after = None
        docs_processed = 0
        checkpoint = ExtractionCheckpoint(
            source=index,
            time_range={"start": start, "end": end},
            search_after=search_after,
            partition=partition,
            event_count=0,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            software_version="0.1.0"
        )
        manager.save(run_id, checkpoint)

        # Initialize manifest only on fresh run
        from tads.schema.canonical import SCHEMA_V1
        manifest_builder.initialize_run(run_id, index, start, end, batch_size, schema_version=SCHEMA_V1.version)

    try:
        click.echo("\n1. Validating connection...")
        await source.connect()
        click.secho("Connection successful.", fg="green")

        click.echo("2. Discovering source...")
        is_valid = await source.validate_connection()
        if not is_valid:
            click.secho("Source validation failed. Check permissions or network.", fg="red")
            sys.exit(1)
        # Verify index mapping
        mapping = await source.discover_fields(index)
        if not mapping:
            click.secho(f"Warning: Could not discover mappings for index {index}.", fg="yellow")

        click.echo(f"Source '{index}' ready.")

        stream = source.stream_events(
            index=index,
            start_time=start,
            end_time=end,
            batch_size=batch_size,
            search_after=search_after
        )

        click.echo("3. Extracting... Press Ctrl+C to stop gracefully.")
        start_time_real = time.time()

        batch_counter = 0
        async for batch, next_sa in stream:
            batch_len = len(batch)
            if batch_len == 0:
                continue

            # Tracking min/max timestamps BEFORE writer mutates the hits
            for hit in batch:
                src = hit.get("_source", {})
                ts = src.get("@timestamp")
                if ts:
                    if not actual_min_ts or ts < actual_min_ts:
                        actual_min_ts = ts
                    if not actual_max_ts or ts > actual_max_ts:
                        actual_max_ts = ts

            batch_counter += 1

            # Form a deterministic batch ID (e.g. index + counter)
            batch_id = f"offset_{docs_processed}"

            file_path, dropped = writer.write_batch(batch, partition, run_id, batch_id)

            # Aggregate dropped events
            for reason, count in dropped.items():
                total_dropped[reason] = total_dropped.get(reason, 0) + count

            # Update successfully coerced docs
            survived_count = batch_len - sum(dropped.values())
            docs_processed += survived_count

            if file_path and file_path not in files_written:
                files_written.append(file_path)

            # Save checkpoint AFTER successful processing of batch
            checkpoint.search_after = next_sa
            checkpoint.event_count = docs_processed
            checkpoint.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            manager.save(run_id, checkpoint)

            sys.stdout.write(
                f"\rProcessed {docs_processed} documents "
                f"(Dropped: {sum(total_dropped.values())})... "
                f"(Saved batch {batch_counter})"
            )
            sys.stdout.flush()

        duration = time.time() - start_time_real
        print()
        click.secho(f"Extraction complete! Total documents processed: {docs_processed}", fg="green")
        manager.clear(run_id)

        # Finalize the partition so readers will accept it
        writer.finalize_partition(partition, run_id, total_docs=docs_processed)

        # Mark manifest completed
        manifest_builder.mark_completed(
            run_id=run_id,
            files_written=files_written,
            actual_min_timestamp=actual_min_ts,
            actual_max_timestamp=actual_max_ts,
            event_count=docs_processed,
            partitions={partition},
            duration_seconds=duration,
            dropped_events=total_dropped
        )

        # Print End Summary
        click.secho("\n--- Ingestion Summary ---", fg="cyan", bold=True)
        click.echo(f"Run ID:        {run_id}")
        click.echo(f"Duration:      {duration:.2f}s")
        throughput = 0.0
        if duration > 0:
            throughput = docs_processed / duration
        click.echo(f"Throughput:    {throughput:.2f} events/sec")
        click.echo(f"Extracted:     {docs_processed} events")

        if total_dropped:
            click.echo("Dropped Events:")
            for reason, count in total_dropped.items():
                click.echo(f"  - {reason}: {count}")

        click.echo(f"Partitions:    {len({partition})}")

    except asyncio.CancelledError:
        click.secho("\nExtraction cancelled. Checkpoint safely preserved.", fg="yellow")
        raise
    except Exception as e:
        manifest_builder.mark_failed(run_id, event_count=docs_processed)
        click.secho(f"\nError during extraction: {e}", fg="red")
        sys.exit(1)
    finally:
        if 'source' in locals():
            await source.close()

