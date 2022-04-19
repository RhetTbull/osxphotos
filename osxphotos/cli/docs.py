"""docs command for osxphotos CLI """

import pathlib
import shutil
from typing import Optional

import click

from osxphotos._version import __version__

from .common import get_config_dir


@click.command()
@click.pass_obj
@click.pass_context
def docs(ctx, cli_obj):
    """Open osxphotos documentation in your browser."""

    docs_dir = get_config_dir() / "docs"
    if not docs_dir.exists():
        docs_dir.mkdir(parents=True)

    docs_version = get_docs_version(docs_dir)
    if not docs_version or docs_version != __version__:
        click.echo(f"Copying docs for osxphotos version {__version__}")
        shutil.rmtree(str(docs_dir), ignore_errors=True)
        copy_docs(docs_dir)
        set_docs_version(docs_dir, __version__)

    index = docs_dir / "index.html"
    click.echo(f"Opening {index}")
    click.launch(str(index))


def get_docs_version(docs_dir: pathlib.Path) -> Optional[str]:
    """Get the version of the docs directory"""

    if not docs_dir.exists():
        return None

    version_file = docs_dir / ".version"
    if not version_file.exists():
        return None

    with version_file.open() as f:
        return f.read().strip()


def copy_docs(docs_dir: pathlib.Path):
    """Copy the latest docs to the docs directory"""
    # there must be a better way to do this
    # docs are in osxphotos/docs and this file is in osxphotos/cli
    src_dir = pathlib.Path(__file__).parent.parent / "docs"
    shutil.copytree(str(src_dir), str(docs_dir))


def set_docs_version(docs_dir: pathlib.Path, version: str):
    """Set the version of the docs directory"""
    version_file = docs_dir / ".version"
    if version_file.exists():
        version_file.unlink()
    with version_file.open("w") as f:
        f.write(version)
