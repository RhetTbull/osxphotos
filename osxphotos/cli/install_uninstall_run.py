"""install/uninstall/run commands for osxphotos CLI"""


import contextlib
import sys
from runpy import run_module, run_path

import click


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
    args = ["pip", "install"]
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
@click.argument("python_file", nargs=1, type=click.Path(exists=True))
@click.argument("args", metavar="ARGS", nargs=-1)
def run(python_file, help, args):
    """Run a python file using same environment as osxphotos.
    Any args are made available to the python file."""

    # Need to drop all the args from sys.argv up to and including the run command
    # For example, command could be one of the following:
    # osxphotos run example.py --help
    # osxphotos --debug run example.py --verbose --db /path/to/photos.db
    # etc.
    with contextlib.suppress(ValueError):
        index = sys.argv.index("run")
        sys.argv = sys.argv[index + 1 :]
    run_path(python_file, run_name="__main__")
