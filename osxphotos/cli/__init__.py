"""cli package for osxphotos"""
import sys

from rich import print
from rich.traceback import install as install_traceback

from osxphotos.debug import (
    debug_breakpoint,
    debug_watch,
    get_debug_flags,
    get_debug_options,
    set_debug,
    wrap_function,
)

# apply any debug functions
# need to do this before importing anything else so that the debug functions
# wrap the right function references
# if a module does something like "from exiftool import ExifTool" and the user tries
# to wrap 'osxphotos.exiftool.ExifTool.asdict', the original ExifTool.asdict will be
# wrapped but the caller will have a reference to the function before it was wrapped
# reference: https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/13-ordering-issues-when-monkey-patching-in-python.md
args = get_debug_options(["--watch", "--breakpoint"], sys.argv)
for func_name in args.get("--watch", []):
    try:
        wrap_function(func_name, debug_watch)
        print(f"Watching {func_name}")
    except AttributeError:
        print(f"{func_name} does not exist")
        sys.exit(1)

for func_name in args.get("--breakpoint", []):
    try:
        wrap_function(func_name, debug_breakpoint)
        print(f"Breakpoint added for {func_name}")
    except AttributeError:
        print(f"{func_name} does not exist")
        sys.exit(1)

args = get_debug_flags(["--debug"], sys.argv)
if args.get("--debug", False):
    set_debug(True)
    print("Debugging enabled")

from .about import about
from .albums import albums
from .cli import cli_main
from .common import get_photos_db, load_uuid_from_file
from .debug_dump import debug_dump
from .dump import dump
from .exiftool_cli import exiftool
from .export import export
from .exportdb import exportdb
from .grep import grep
from .help import help
from .info import info
from .install_uninstall_run import install, run, uninstall
from .keywords import keywords
from .labels import labels
from .list import _list_libraries, list_libraries
from .orphans import orphans
from .persons import persons
from .photo_inspect import photo_inspect
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
    "exiftool_cli",
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
    "orphans",
    "persons",
    "photo_inspect",
    "places",
    "query",
    "repl",
    "run",
    "set_debug",
    "snap",
    "tutorial",
    "uuid",
]
