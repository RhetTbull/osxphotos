"""Self-update command for osxphotos"""

import click

from osxphotos._constants import APP_NAME
from osxphotos._version import __version__

from .selfupdate import update


@click.command(name="update")
def update_command():
    """Update the installation to the latest version."""
    update(APP_NAME, __version__, APP_NAME)
