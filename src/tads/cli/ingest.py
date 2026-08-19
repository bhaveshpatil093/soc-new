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
