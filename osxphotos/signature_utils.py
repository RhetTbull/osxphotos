"""Helpers for matching photo signatures."""

from __future__ import annotations

import pathlib
import re

__all__ = [
    "normalize_collision_filename",
    "normalize_photo_signature_filename",
]

# Photos appends a counter to the filename when importing a file whose name
# collides with an existing photo, e.g. "IMG_1234.HEIC" -> "IMG_1234 2.HEIC".
# Match a single space followed by a counter with no leading zeros so filenames
# that legitimately end in a number ("Scan 001.jpg", "Vacation 2024.jpg") are
# left alone.
_COLLISION_SUFFIX_RE = re.compile(r"^(?P<stem>.+?) [1-9]\d{0,2}$")


def normalize_collision_filename(filename: str | pathlib.Path) -> str:
    """Strip a Photos-style collision counter from a filename if present."""
    path = pathlib.Path(filename)
    stem = path.stem
    if match := _COLLISION_SUFFIX_RE.match(stem):
        stem = match.group("stem")
    return f"{stem}{path.suffix}"


def normalize_photo_signature_filename(
    signature: str, filename: str | pathlib.Path
) -> str:
    """Return a signature with a collision counter stripped from the filename portion.

    Args:
        signature: photo signature as returned by photo_signature()
        filename: original filename of the photo the signature was computed from

    Returns: the signature with the collision counter removed from the filename
        portion or the signature unchanged if it does not begin with filename.

    Note: signatures for shared photos do not contain a filename so they are
        returned unchanged.
    """
    prefix = f"{pathlib.Path(filename).name.lower()}:"
    if not signature.startswith(prefix):
        # signature isn't of the form "filename:fingerprint" (e.g. a shared
        # photo signature) so there's no filename to normalize
        return signature
    return f"{normalize_collision_filename(filename).lower()}:{signature[len(prefix):]}"
