from pathlib import Path

import click

from optimade_maker.convert import convert_archive
from optimade_maker.logger import LOGGER
from optimade_maker.serve import OptimakeServer


@click.group()
def cli():
    """
    Tools for making OPTIMADE APIs for a raw data archives annotated with an
    `optimade.yaml` file.
    """
    pass


@cli.command()
@click.option(
    "--jsonl_path",
    type=click.Path(),
    help="The path to write the JSONL file to.",
)
@click.option(
    "--limit",
    type=int,
    help="Limit the ingestion to a fixed number of structures (useful for testing).",
)
@click.argument(
    "path",
    type=click.Path(),
)
def convert(jsonl_path, path, limit=None):
    """
    Convert a raw data archive into OPTIMADE JSONL.

    PATH needs to contain the full raw data archive, with the `optimade.yaml` config
    file at the top level. The data is converted into the OPTIMADE JSON Lines format.
    """

    if jsonl_path:
        jsonl_path = Path(jsonl_path)
        if jsonl_path.exists():
            raise FileExistsError(f"File already exists at {jsonl_path}.")
    convert_archive(Path(path), jsonl_path=jsonl_path, limit=limit)


@cli.command()
@click.option(
    "--port",
    type=int,
    default=5000,
    help="The port to serve the API on.",
)
@click.argument(
    "path",
    type=click.Path(),
)
def serve(port, path):
    """
    Serve a raw data archive with an OPTIMADE API.

    PATH needs to contain the full raw data archive, with the `optimade.yaml` config
    file at the top level. If needed, the data is first converted into an OPTIMADE JSONL
    file. However, if the JSONL file already exists, the API is started from it.

    Note that this command starts the API using a simple backend, which is not recommended
    for a production environment.
    """

    jsonl_file = "optimade.jsonl"
    path = Path(path)

    if not (path / jsonl_file).exists():
        LOGGER.info(f"{jsonl_file} doesn't exist. Converting archive.")
        convert_archive(path)
    else:
        LOGGER.info(f"{jsonl_file} already exists!")

    LOGGER.info("Starting the API")
    optimake_server = OptimakeServer(path, port)
    optimake_server.start_api()


if __name__ == "__main__":
    cli()
