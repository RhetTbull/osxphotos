"""about command for osxphotos CLI"""

import os

import click
import packaging

from osxphotos._constants import OSXPHOTOS_URL
from osxphotos._version import __version__

from .common import get_latest_version


@click.command(name="version")
@click.pass_obj
@click.pass_context
@click.option(
    "--run",
    metavar="COMMAND",
    required=False,
    type=str,
    help="Run COMMAND if there is a new version of osxphotos available.",
)
def version(ctx, cli_obj, run):
    """Check for new version of osxphotos."""
    latest_version, err = get_latest_version()
    if latest_version and packaging.version.parse(
        latest_version
    ) > packaging.version.parse(__version__):
        click.echo(
            f"A new version of osxphotos is available: {latest_version} (you have {__version__})\n"
            "Run `pipx upgrade osxphotos` to upgrade (assuming you installed osxphotos with pipx).\n"
            f"See {OSXPHOTOS_URL} for more information."
        )
        if run:
            click.echo(f"Running command: '{run}'")
            os.system(run)
    elif not latest_version:
        click.echo(f"Unable to check for new version of osxphotos: {err}")
    else:
        click.echo(f"You have the latest version of osxphotos: {__version__}")
