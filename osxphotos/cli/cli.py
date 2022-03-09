"""Command line interface for osxphotos """

import click

import osxphotos
from osxphotos._version import __version__

from .about import about
from .albums import albums
from .common import DB_OPTION, JSON_OPTION, OSXPHOTOS_HIDDEN
from .debug_dump import debug_dump
from .dump import dump
from .export import export
from .exportdb import exportdb
from .grep import grep
from .help import help
from .info import info
from .install_uninstall_run import install, run, uninstall
from .keywords import keywords
from .labels import labels
from .list import _list_libraries, list_libraries
from .persons import persons
from .places import places
from .query import query
from .repl import repl
from .snap_diff import diff, snap
from .tutorial import tutorial
from .uuid import uuid


# Click CLI object & context settings
class CLI_Obj:
    def __init__(self, db=None, json=False, debug=False, group=None):
        self.db = db
        self.json = json
        self.group = group


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
@DB_OPTION
@JSON_OPTION
@click.option(
    "--debug",
    required=False,
    is_flag=True,
    help="Enable debug output",
    hidden=OSXPHOTOS_HIDDEN,
)
@click.version_option(__version__, "--version", "-v")
@click.pass_context
def cli_main(ctx, db, json_, debug):
    ctx.obj = CLI_Obj(db=db, json=json_, group=cli_main)


# install CLI commands
for command in [
    about,
    albums,
    debug_dump,
    diff,
    dump,
    export,
    exportdb,
    grep,
    help,
    info,
    install,
    keywords,
    labels,
    list_libraries,
    persons,
    places,
    query,
    repl,
    run,
    snap,
    tutorial,
    uninstall,
    uuid,
]:
    cli_main.add_command(command)
