#!/usr/bin/env python3

from pathlib import Path
import click
import importlib.metadata
from leaf_desease_predictor.app import LeafDeseasePredictor

__version__ = importlib.metadata.version("leaf_desease_predictor")

@click.group(invoke_without_command=True, no_args_is_help=True)
@click.pass_context
@click.version_option(__version__, prog_name="leaf-desease-predictor")
def cli(*args):
    pass

@click.command(help="run the main application")
@click.argument('configuration_file', type=click.Path(exists=True))
def run(configuration_file: Path) -> None:
    bridge = LeafDeseasePredictor(configuration_file)
    bridge.run()
cli.add_command(run)


if __name__ == "__main__":
    cli()
