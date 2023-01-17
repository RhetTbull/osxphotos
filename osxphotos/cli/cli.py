"""Command line interface for osxphotos """

import atexit
import cProfile
import io
import pstats

import click

from osxphotos._constants import PROFILE_SORT_KEYS
from osxphotos._version import __version__

from .about import about
from .add_locations import add_locations
from .albums import albums
from .common import DB_OPTION, JSON_OPTION, OSXPHOTOS_HIDDEN
from .debug_dump import debug_dump
from .docs import docs
from .dump import dump
from .exiftool_cli import exiftool
from .export import export
from .exportdb import exportdb
from .grep import grep
from .help import help
from .import_cli import import_cli
from .info import info
from .install_uninstall_run import install, run, uninstall
from .keywords import keywords
from .labels import labels
from .list import list_libraries
from .orphans import orphans
from .persons import persons
from .photo_inspect import photo_inspect
from .places import places
from .query import query
from .repl import repl
from .snap_diff import diff, snap
from .sync import sync
from .theme import theme
from .timewarp import timewarp
from .tutorial import tutorial
from .uuid import uuid
from .version import version
from .common import DEBUG_OPTIONS


# Click CLI object & context settings
class CLI_Obj:
    def __init__(self, db=None, json=False, debug=False, group=None):
        self.db = db
        self.json = json
        self.group = group


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
@click.version_option(__version__, "--version", "-v")
@DB_OPTION
@JSON_OPTION
@DEBUG_OPTIONS
@click.option(
    "--profile", is_flag=True, hidden=OSXPHOTOS_HIDDEN, help="Enable profiling"
)
@click.option(
    "--profile-sort",
    default=None,
    hidden=OSXPHOTOS_HIDDEN,
    multiple=True,
    metavar="SORT_KEY",
    type=click.Choice(
        PROFILE_SORT_KEYS,
        case_sensitive=True,
    ),
    help="Sort profiler output by SORT_KEY as specified at https://docs.python.org/3/library/profile.html#pstats.Stats.sort_stats. "
    f"Can be specified multiple times. Valid options are: {PROFILE_SORT_KEYS}. "
    "Default = 'cumulative'.",
)
@click.pass_context
def cli_main(ctx, db, json_, profile, profile_sort, **kwargs):
    """osxphotos: the multi-tool for your Photos library"""
    # Note: kwargs is used to catch any debug options passed in
    # the debug options are handled in cli/__init__.py
    # before this function is called
    ctx.obj = CLI_Obj(db=db, json=json_, group=cli_main)
    if profile:
        click.echo("Profiling...")
        profile_sort = profile_sort or ["cumulative"]
        click.echo(f"Profile sort_stats order: {profile_sort}")
        pr = cProfile.Profile()
        pr.enable()

        def at_exit():
            pr.disable()
            click.echo("Profiling completed")
            s = io.StringIO()
            pstats.Stats(pr, stream=s).strip_dirs().sort_stats(
                *profile_sort
            ).print_stats()
            click.echo(s.getvalue())

        atexit.register(at_exit)


# install CLI commands
for command in [
    about,
    add_locations,
    albums,
    debug_dump,
    diff,
    docs,
    dump,
    exiftool,
    export,
    exportdb,
    grep,
    help,
    import_cli,
    info,
    install,
    keywords,
    labels,
    list_libraries,
    orphans,
    persons,
    photo_inspect,
    places,
    query,
    repl,
    run,
    snap,
    sync,
    theme,
    timewarp,
    tutorial,
    uninstall,
    uuid,
    version,
]:
    cli_main.add_command(command)
