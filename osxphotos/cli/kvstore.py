"""Simple interface to SQLiteKVStore for storing state between runs of the CLI tool."""


from __future__ import annotations

import atexit
import contextlib
import datetime

from osxphotos.sqlitekvstore import SQLiteKVStore

from .common import get_data_dir

__all__ = ["kvstore"]

# Store open connections
__kvstores = []


@atexit.register
def close_kvstore():
    """Close any open SQLiteKVStore databases"""
    global __kvstores
    for kv in __kvstores:
        with contextlib.suppress(Exception):
            kv.close()


def kvstore(name: str) -> SQLiteKVStore:
    """Return a key/value store for storing state between commands.

    The key/value store is a SQLite database stored in the user's XDG data directory,
    usually `~/.local/share/`.  The key/value store can be used like a dict to store
    arbitrary key/value pairs which persist between runs of the CLI tool.

    Args:
        name: a unique name for the key/value store

    Returns:
        SQLiteKVStore object
    """
    global __kvstores
    data_dir = get_data_dir()
    if not name.endswith(".db"):
        name += ".db"
    kv = SQLiteKVStore(str(data_dir / name), wal=True)
    if not kv.about:
        kv.about = f"Key/value store for {name}, created by osxphotos CLI on {datetime.datetime.now()}"
    __kvstores.append(kv)
    return kv
