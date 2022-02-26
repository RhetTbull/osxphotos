"""cli package for osxphotos"""

import rich

from .cli import (
    about,
    albums,
    cli,
    debug_dump,
    diff,
    dump,
    export,
    get_photos_db,
    grep,
    help,
    info,
    install,
    keywords,
    labels,
    list_libraries,
    load_uuid_from_file,
    persons,
    places,
    query,
    repl,
    snap,
    tutorial,
    uninstall,
    uuid,
)
from .common import set_debug

rich.traceback.install()

__all__ = [
    "about",
    "albums",
    "cli",
    "debug_dump",
    "diff",
    "dump",
    "export",
    "get_photos_db",
    "grep",
    "help",
    "info",
    "install",
    "keywords",
    "labels",
    "list_libraries",
    "load_uuid_from_file",
    "persons",
    "places",
    "query",
    "repl",
    "set_debug",
    "set_timestamp",
    "snap",
    "tutorial",
    "uninstall",
    "uuid",
]
