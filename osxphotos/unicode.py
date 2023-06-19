"""Utilities for working with unicode strings."""

from __future__ import annotations

import pathlib
import unicodedata
from typing import Literal, TypeVar, Union

from osxphotos.platform import is_macos

# Unicode format to use for comparing strings
UNICODE_FORMAT = "NFC"

# Unicode format to use for filesystem paths
UNICODE_FS_FORMAT = "NFD" if is_macos else "NFC"

PathType = TypeVar("PathType", bound=Union[str, pathlib.Path])

UnicodeDataType = TypeVar(
    "UnicodeDataType", bound=Union[str, list[str], tuple[str, ...], None]
)

__all__ = [
    "get_unicode_format",
    "set_unicode_format",
    "get_unicode_fs_format",
    "set_unicode_fs_format",
    "normalize_fs_path",
    "normalize_unicode",
]


def get_unicode_format() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode format"""
    global UNICODE_FORMAT
    return UNICODE_FORMAT


def set_unicode_format(format: Literal["NFC", "NFKC", "NFD", "NFKD"]) -> None:
    """Set the global unicode format"""

    if format not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {format}")

    global UNICODE_FORMAT
    UNICODE_FORMAT = format


def get_unicode_fs_format() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode filesystem format"""
    global UNICODE_FS_FORMAT
    return UNICODE_FS_FORMAT


def set_unicode_fs_format(format: str) -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Set the global unicode filesystem format"""

    if format not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {format}")

    global UNICODE_FS_FORMAT
    UNICODE_FS_FORMAT = format


def normalize_fs_path(path: PathType) -> PathType:
    """Normalize filesystem paths with unicode in them"""
    global UNICODE_FS_FORMAT
    if isinstance(path, pathlib.Path):
        return pathlib.Path(unicodedata.normalize(UNICODE_FS_FORMAT, str(path)))
    else:
        return unicodedata.normalize(UNICODE_FS_FORMAT, path)


def normalize_unicode(value: UnicodeDataType) -> UnicodeDataType:
    """normalize unicode data"""
    if value is None:
        return None
    if isinstance(value, tuple):
        return tuple(unicodedata.normalize(UNICODE_FORMAT, v) for v in value)
    elif isinstance(value, list):
        return [unicodedata.normalize(UNICODE_FORMAT, v) for v in value]
    elif isinstance(value, str):
        return unicodedata.normalize(UNICODE_FORMAT, value)
    else:
        return value
