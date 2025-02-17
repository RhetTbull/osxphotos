"""Update captions from filenames; ignore filenames that match a pattern

run with `osxphotos run captions_from_filenames.py --help`
"""

from __future__ import annotations

import fnmatch
import pathlib

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, query_command, verbose


@query_command
@click.option(
    "--ignore",
    type=str,
    multiple=True,
    help="Pattern to ignore filenames; use glob patterns as would be used for file matching",
)
@click.option("--dry-run", is_flag=True, help="Dry run, do not update captions")
def update_captions(
    photos: list[osxphotos.PhotoInfo], ignore: tuple[str, ...], dry_run: bool, **kwargs
):
    """Update captions from filenames; ignore filenames that match a pattern.

    For example, to ignore filenames that start with "IMG_", use the --ignore option:
    `osxphotos run captions_from_filenames.py --ignore "IMG_*"`

    """
    echo(f"Updating {len(photos)} photo{'s' if len(photos) > 1 else ''}")
    if ignore:
        photos = filter_ignore(photos, ignore)
    for photo in photos:
        stem = pathlib.Path(photo.original_filename).stem
        echo(
            f"Setting caption for {photo.original_filename} ({photo.uuid}) to '{stem}'"
        )
        if not dry_run:
            set_caption(photo, stem)


def set_caption(photo: osxphotos.PhotoInfo, caption: str):
    """Set caption for photo"""
    try:
        p = photoscript.Photo(photo.uuid)
        p.description = caption
    except Exception as e:
        echo(f"Error setting caption for {photo.original_filename} ({photo.uuid}): {e}")


def filter_ignore(
    photos: list[osxphotos.PhotoInfo], ignore: tuple[str, ...]
) -> list[osxphotos.PhotoInfo]:
    """Filter photos based on ignore patterns"""
    return [
        photo
        for photo in photos
        if not any(
            fnmatch.fnmatch(photo.original_filename, pattern) for pattern in ignore
        )
    ]


if __name__ == "__main__":
    update_captions()
