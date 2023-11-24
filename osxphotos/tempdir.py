"""Temporary directory for osxphotos session"""

from __future__ import annotations

import pathlib
import tempfile

_TEMPDIR = tempfile.TemporaryDirectory(prefix="osxphotos_")
TEMPDIR = pathlib.Path(_TEMPDIR.name)


def tempdir(subdir: str | None = None):
    """Return path to temporary directory that exists for the duration of the osxphotos session

    Args:
        subdir: optional subdirectory to create in temporary directory

    Returns: pathlib.Path to temporary directory
    """
    if subdir:
        tmp = TEMPDIR / subdir
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp
    else:
        return TEMPDIR


def cleanup():
    """Cleanup temporary directory"""
    _TEMPDIR.cleanup()
