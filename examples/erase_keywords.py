"""Erase all keywords from selected photos

Run with `osxphotos run erase_keywords.py` to erase keywords from selected photos.
"""

from __future__ import annotations

import photoscript

import osxphotos
from osxphotos.cli import selection_command, verbose


@selection_command
def erase_keywords(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Erase all keywords from selected photos."""

    verbose(f"Found {len(photos)} selected photo(s)")
    for photo in photos:
        verbose(f"Processing {photo.original_filename} ({photo.uuid})")
        p = photoscript.Photo(photo.uuid)
        if not p:
            verbose(f"Could not find photo with uuid {photo.uuid}")
            continue
        if p.keywords:
            verbose(f"Erasing keywords {', '.join(photo.keywords)} from {p.filename}")
            p.keywords = []
        else:
            verbose(f"No keywords to erase from {p.filename}")


if __name__ == "__main__":
    erase_keywords()
