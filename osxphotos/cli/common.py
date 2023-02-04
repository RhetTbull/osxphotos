"""Globals and constants use by the CLI commands"""

from __future__ import annotations

import os
import pathlib
from datetime import datetime

import click
from packaging import version
from xdg import xdg_config_home, xdg_data_home

import osxphotos
from osxphotos._constants import APP_NAME
from osxphotos._version import __version__
from osxphotos.utils import get_latest_version

# used to show/hide hidden commands
OSXPHOTOS_HIDDEN = not bool(os.getenv("OSXPHOTOS_SHOW_HIDDEN", default=False))

# used by snap and diff commands
OSXPHOTOS_SNAPSHOT_DIR = "/private/tmp/osxphotos_snapshots"

# where to write the crash report if osxphotos crashes
OSXPHOTOS_CRASH_LOG = f"{os.getcwd()}/osxphotos_crash.log"

CLI_COLOR_ERROR = "red"
CLI_COLOR_WARNING = "yellow"

__all__ = [
    "CLI_COLOR_ERROR",
    "CLI_COLOR_WARNING",
    "get_photos_db",
    "noop",
    "time_stamp",
]


def noop(*args, **kwargs):
    """no-op function"""
    pass


def time_stamp() -> str:
    """return timestamp"""
    return f"[time]{str(datetime.now())}[/time] -- "


def get_photos_db(*db_options):
    """Return path to photos db, select first non-None db_options
    If no db_options are non-None, try to find library to use in
    the following order:
    - last library opened
    - system library
    - ~/Pictures/Photos Library.photoslibrary
    - failing above, returns None
    """
    if db_options:
        for db in db_options:
            if db is not None:
                return db

    # if get here, no valid database paths passed, so try to figure out which to use
    db = osxphotos.utils.get_last_library_path()
    if db is not None:
        click.echo(f"Using last opened Photos library: {db}", err=True)
        return db

    db = osxphotos.utils.get_system_library_path()
    if db is not None:
        click.echo(f"Using system Photos library: {db}", err=True)
        return db

    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    if os.path.isdir(db):
        click.echo(f"Using Photos library: {db}", err=True)
        return db
    else:
        return None


def get_config_dir() -> pathlib.Path:
    """Get the directory where config files are stored; create it if necessary."""
    config_dir = xdg_config_home() / APP_NAME
    if not config_dir.is_dir():
        config_dir.mkdir(parents=True)
    return config_dir


def get_data_dir() -> pathlib.Path:
    """Get the director where local user data files are stored; create it if necessary"""
    data_dir = xdg_data_home() / APP_NAME
    if not data_dir.is_dir():
        data_dir.mkdir(parents=True)
    return data_dir


def check_version():
    """Check for updates"""
    latest_version, _ = get_latest_version()
    if latest_version and version.parse(latest_version) > version.parse(__version__):
        click.echo(
            f"New version {latest_version} available; you are running {__version__}\n"
            "Run `pipx upgrade osxphotos` to upgrade.\n"
            "Use --no-version-check or set environment variable OSXPHOTOS_NO_VERSION_CHECK=1 "
            "to suppress this message and prevent osxphotos from checking for latest version.",
            err=True,
        )
