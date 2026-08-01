"""Helpers for matching photo signatures."""

from __future__ import annotations

import pathlib
import re

_COLLISION_SUFFIX_RE = re.compile(r"^(?P<stem>.*?)(?:\s+\d+)$", re.IGNORECASE)


def normalize_collision_filename(filename: str | pathlib.Path) -> str:
    """Strip a Photos-style collision suffix from a filename if present."""
    path = pathlib.Path(filename)
    stem = path.stem
    if match := _COLLISION_SUFFIX_RE.match(stem):
        stem = match.group("stem")
    return f"{stem}{path.suffix}"


def normalize_photo_signature_filename(signature: str, filename: str | pathlib.Path) -> str:
    """Return a signature with a collision suffix stripped from the filename portion."""
    if ":" not in signature:
        return signature
    _, rest = signature.split(":", 1)
    return f"{normalize_collision_filename(filename).lower()}:{rest}"
