"""cli package for osxphotos"""

from rich.traceback import install as install_traceback

from .about import about
from .albums import albums
from .cli import cli_main
from .common import get_photos_db, load_uuid_from_file, set_debug
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

install_traceback()

__all__ = [
    "about",
    "albums",
    "cli_main",
    "debug_dump",
    "diff",
    "dump",
    "export",
    "exportdb",
    "grep",
    "help",
    "info",
    "install",
    "keywords",
    "labels",
    "list_libraries",
    "list_libraries",
    "load_uuid_from_file",
    "persons",
    "places",
    "query",
    "repl",
    "run",
    "snap",
    "tutorial",
    "uuid",
]
