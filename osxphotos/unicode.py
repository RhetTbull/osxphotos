"""Utilities for working with unicode strings."""

from __future__ import annotations

import pathlib
import unicodedata
from typing import Literal, TypeVar

from osxphotos.platform import is_macos

# Unicode format to use for comparing strings
DEFAULT_UNICODE_FORM = "NFC"

# global unicode format
_GLOBAL_UNICODE_FORM = DEFAULT_UNICODE_FORM

# global unicode format to use for filesystem paths
_GLOBAL_UNICODE_FS_FORM = "NFD" if is_macos else "NFC"

PathType = TypeVar("PathType", bound=str | pathlib.Path)

UnicodeDataType = TypeVar(
    "UnicodeDataType", bound=str | list[str] | tuple[str, ...] | None
)

__all__ = [
    "DEFAULT_UNICODE_FORM",
    "get_unicode_form",
    "get_unicode_fs_form",
    "normalize_fs_path",
    "normalize_unicode",
    "set_unicode_form",
    "set_unicode_fs_form",
]


def get_unicode_form() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode format"""
    return _GLOBAL_UNICODE_FORM


def set_unicode_form(fmt: Literal["NFC", "NFKC", "NFD", "NFKD"]) -> None:
    """Set the global unicode format"""

    if fmt not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {fmt}")

    global _GLOBAL_UNICODE_FORM
    _GLOBAL_UNICODE_FORM = fmt


def get_unicode_fs_form() -> Literal["NFC", "NFKC", "NFD", "NFKD"]:
    """Return the global unicode filesystem format"""
    return _GLOBAL_UNICODE_FS_FORM


def set_unicode_fs_form(fmt: Literal["NFC", "NFKC", "NFD", "NFKD"]):
    """Set the global unicode filesystem format"""

    if fmt not in ["NFC", "NFKC", "NFD", "NFKD"]:
        raise ValueError(f"Invalid unicode format: {fmt}")

    global _GLOBAL_UNICODE_FS_FORM
    _GLOBAL_UNICODE_FS_FORM = fmt


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
        return tuple(
            unicodedata.normalize(form, str(v if v is not None else "")) for v in value
        )
    elif isinstance(value, list):
        return [
            unicodedata.normalize(form, str(v if v is not None else "")) for v in value
        ]
    elif isinstance(value, str):
        return unicodedata.normalize(form, value)
    else:
        return value
