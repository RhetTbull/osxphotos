"""install/uninstall/run commands for osxphotos CLI"""

import sys
from runpy import run_module, run_path

import click


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


@click.command(name="run")
@click.argument("python_file", nargs=1, type=click.Path(exists=True))
def run(python_file):
    """Run a python file using same environment as osxphotos"""
    run_path(python_file, run_name="__main__")
