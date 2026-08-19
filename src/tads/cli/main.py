import click

from tads.cli.ingest import ingest_group


@click.group()
def cli() -> None:
    """TADS CLI - Temporal Anomaly Detection System"""
    pass

cli.add_command(ingest_group, name="ingest")

def main() -> None:
    cli()

if __name__ == "__main__":
    main()
