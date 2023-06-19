"""Utilities for working with unicode strings."""

from __future__ import annotations

import pathlib
import unicodedata
from typing import Literal, TypeVar, Union

from osxphotos.platform import is_macos

# Unicode format to use for comparing strings
DEFAULT_UNICODE_FORM = "NFC"

# global unicode format
_GLOBAL_UNICODE_FORM = DEFAULT_UNICODE_FORM

# global unicode format to use for filesystem paths
_GLOBAL_UNICODE_FS_FORM = "NFD" if is_macos else "NFC"

PathType = TypeVar("PathType", bound=Union[str, pathlib.Path])

UnicodeDataType = TypeVar(
    "UnicodeDataType", bound=Union[str, list[str], tuple[str, ...], None]
)

__all__ = [
    "get_unicode_form",
    "set_unicode_form",
    "get_unicode_fs_form",
    "set_unicode_fs_form",
    "normalize_fs_path",
    "normalize_unicode",
    "DEFAULT_UNICODE_FORM",
]


def get_unicode_form() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode format"""
    global _GLOBAL_UNICODE_FORM
    return _GLOBAL_UNICODE_FORM


def set_unicode_form(format: Literal["NFC", "NFKC", "NFD", "NFKD"]) -> None:
    """Set the global unicode format"""

    if format not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {format}")

    global _GLOBAL_UNICODE_FORM
    _GLOBAL_UNICODE_FORM = format


def get_unicode_fs_form() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode filesystem format"""
    global _GLOBAL_UNICODE_FS_FORM
    return _GLOBAL_UNICODE_FS_FORM


def set_unicode_fs_form(format: str) -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Set the global unicode filesystem format"""

    if format not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {format}")

    global _GLOBAL_UNICODE_FS_FORM
    _GLOBAL_UNICODE_FS_FORM = format


def normalize_fs_path(path: PathType) -> PathType:
    """Normalize filesystem paths with unicode in them"""
    form = get_unicode_fs_form()
    if isinstance(path, pathlib.Path):
        return pathlib.Path(unicodedata.normalize(form, str(path)))
    else:
        return unicodedata.normalize(form, path)


def normalize_unicode(value: UnicodeDataType) -> UnicodeDataType:
    """normalize unicode data"""
    form = get_unicode_form()
    if value is None:
        return None
    if isinstance(value, tuple):
        return tuple(unicodedata.normalize(form, v) for v in value)
    elif isinstance(value, list):
        return [unicodedata.normalize(form, v) for v in value]
    elif isinstance(value, str):
        return unicodedata.normalize(form, value)
    else:
        return value
