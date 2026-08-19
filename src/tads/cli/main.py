import click

from tads.cli.discover import discover_group
from tads.cli.ingest import ingest_group


@click.group()
def cli() -> None:
    """TADS CLI - Temporal Anomaly Detection System"""
    pass

cli.add_command(ingest_group, name="ingest")
cli.add_command(discover_group, name="discover")

def main() -> None:
    cli()

if __name__ == "__main__":
    main()
