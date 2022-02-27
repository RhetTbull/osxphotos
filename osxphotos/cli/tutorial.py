"""tutorial command for osxphotos CLI"""

import io
import pathlib

import click
from rich.console import Console
from rich.markdown import Markdown

from .help import strip_html_comments, strip_md_links


@click.command(name="tutorial")
@click.argument(
    "WIDTH",
    nargs=-1,
    type=click.INT,
)
@click.pass_obj
@click.pass_context
def tutorial(ctx, cli_obj, width):
    """Display osxphotos tutorial."""
    width = width[0] if width else 100
    click.echo_via_pager(tutorial_help(width=width))


def tutorial_help(width=78):
    """Return formatted string for tutorial"""
    sio = io.StringIO()
    console = Console(file=sio, force_terminal=True, width=width)
    help_md = get_tutorial_text()
    help_md = strip_html_comments(help_md)
    help_md = strip_md_links(help_md)
    console.print(Markdown(help_md))
    help_str = sio.getvalue()
    sio.close()
    return help_str


def get_tutorial_text():
    """Load tutorial text from file"""
    # TODO: would be better to use importlib.abc.ResourceReader but I can't find a single example of how to do this
    help_file = pathlib.Path(__file__).parent / "../tutorial.md"
    with open(help_file, "r") as fd:
        md = fd.read()
    return md
