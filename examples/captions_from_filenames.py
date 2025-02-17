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
    echo(f"Updating [num]{len(photos)}[/] photo{'s' if len(photos) > 1 else ''}")
    for photo in photos:
        if match_ignore(photo, ignore):
            echo(
                f"Skipping [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/]] due to ignore pattern"
            )
            continue
        stem = pathlib.Path(photo.original_filename).stem
        echo(
            f"Setting caption for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/]) to '[filepath]{stem}[/]'"
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


def match_ignore(photo: osxphotos.PhotoInfo, ignore: tuple[str, ...]) -> bool:
    """Check if photo matches any ignore patterns"""
    return any(fnmatch.fnmatch(photo.original_filename, pattern) for pattern in ignore)


if __name__ == "__main__":
    update_captions()
