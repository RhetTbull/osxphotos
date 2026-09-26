"""install/uninstall/run commands for osxphotos CLI"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import sys
import zipfile
from runpy import run_module, run_path

import click

from .param_types import PathOrURL

__all__ = ["install", "run", "uninstall", "validate_python_file"]


def validate_python_file(python_file: str) -> str | None:
    """Check that python_file contains Python source code that compiles without error.

    Directories, zip files, and compiled .pyc files, which runpy.run_path can also run,
    are not checked.

    Args:
        python_file: path to the file to check

    Returns: None if python_file is valid, otherwise a message describing the problem
    """
    if os.path.isdir(python_file) or zipfile.is_zipfile(python_file):
        return None

    try:
        with open(python_file, "rb") as fd:
            source = fd.read()
    except OSError as e:
        return f"Could not read {python_file}: {e}"

    if source.startswith(importlib.util.MAGIC_NUMBER):
        return None

    try:
        compile(source, python_file, "exec")
    except (SyntaxError, ValueError) as e:
        message = f"{python_file} does not appear to be a valid Python file: {e}"
        head = source.lstrip()[:512].lower()
        if head.startswith((b"<!doctype html", b"<html")):
            message += (
                "\nThe file appears to be an HTML web page, not a Python script. "
                "If you passed a URL, make sure it points to the raw file "
                "(for example, the 'Raw' button on GitHub)."
            )
        return message
    return None


class RunCommand(click.Command):
    """Custom command that ignores unknown options so options can be passed to the run script"""

    def make_parser(self, ctx):
        """Creates the underlying option parser for this command."""
        parser = click.OptionParser(ctx)
        parser.ignore_unknown_options = True
        for param in self.get_params(ctx):
            param.add_to_parser(parser, ctx)
        return parser

    def get_usage(self, ctx):
        """Returns the help for this command;
        normally it would just return the usage string
        but in order to pass --help on to the run script,
        help for the run command is handled here"""
        return self.get_help(ctx)


@click.command()
@click.option(
    "-U", "--upgrade", is_flag=True, help="Upgrade packages to latest version."
)
@click.option(
    "-r",
    "requirements_file",
    metavar="FILE",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Install from requirements file FILE.",
)
@click.argument("packages", nargs=-1, required=False)
def install(packages, upgrade, requirements_file):
    """Install Python packages into the same environment as osxphotos"""
    args = ["pip", "--disable-pip-version-check", "--verbose", "install"]
    if upgrade:
        args += ["--upgrade"]
    if requirements_file:
        args += ["-r", requirements_file]
    if not requirements_file and not packages:
        raise click.UsageError(
            "Must specify either -r or one or more packages to install"
        )
    args += list(packages)
    sys.argv = args
    run_module("pip", run_name="__main__")


@click.command()
@click.argument("packages", nargs=-1, required=True)
@click.option("-y", "--yes", is_flag=True, help="Don't ask for confirmation.")
def uninstall(packages, yes):
    """Uninstall Python packages from the osxphotos environment"""
    sys.argv = ["pip", "uninstall"] + list(packages) + (["-y"] if yes else [])
    run_module("pip", run_name="__main__")


@click.command(name="run", cls=RunCommand)
@click.option("--help", "-h", is_flag=True, help="Show this message and exit.")
@click.argument("python_file", nargs=1, type=PathOrURL(exists=True))
@click.argument("args", metavar="ARGS", nargs=-1)
def run(python_file, help, args):
    """Run a python file using same environment as osxphotos.
    Any args are made available to the python file.

    The python file may be a path on disk, 'osxphotos run /path/to/file.py'
    or a URL to a python file, for example,

    'osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py'

    If the URL is for a GitHub page showing the file (e.g.
    https://github.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py)
    or a GitHub gist, the raw file will be downloaded instead.
    The file is checked to ensure it is valid Python before it is run.
    """

    if error := validate_python_file(python_file):
        raise click.BadParameter(error, param_hint="PYTHON_FILE")

    # Need to drop all the args from sys.argv up to and including the run command
    # For example, command could be one of the following:
    # osxphotos run example.py --help
    # osxphotos --debug run example.py --verbose --db /path/to/photos.db
    # etc.

    with contextlib.suppress(ValueError):
        index = sys.argv.index("run")
        sys.argv = sys.argv[index + 1 :]
    run_path(python_file, run_name="__main__")
