"""install/uninstall/run commands for osxphotos CLI"""

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
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "-U", "--upgrade", is_flag=True, help="Upgrade packages to latest version"
)
def install(packages, upgrade):
    """Install Python packages into the same environment as osxphotos"""
    args = ["pip", "install"]
    if upgrade:
        args += ["--upgrade"]
    args += list(packages)
    sys.argv = args
    run_module("pip", run_name="__main__")


@click.command()
@click.argument("packages", nargs=-1, required=True)
@click.option("-y", "--yes", is_flag=True, help="Don't ask for confirmation")
def uninstall(packages, yes):
    """Uninstall Python packages from the osxphotos environment"""
    sys.argv = ["pip", "uninstall"] + list(packages) + (["-y"] if yes else [])
    run_module("pip", run_name="__main__")


@click.command(name="run", cls=RunCommand)
# help command passed just to keep click from intercepting help
# and allowing --help to be passed to the script being run
@click.option("--help", "-h", is_flag=True, help="Show this message and exit")
@click.argument("python_file", nargs=1, type=click.Path(exists=True))
@click.argument("args", metavar="ARGS", nargs=-1)
def run(python_file, help, args):
    """Run a python file using same environment as osxphotos.
    Any args are made available to the python file."""
    # drop first two arguments, which are the osxphotos script and run command
    sys.argv = sys.argv[2:]
    run_path(python_file, run_name="__main__")
