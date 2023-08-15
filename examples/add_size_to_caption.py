"""Add the photo size in form widthxheight to each photo's caption/description in Photos

Run this with `osxphotos run add_size_to_caption`

Run `osxphotos run add_size_to_caption --help` for help.

Intended to be run with osxphotos; see https://github.com/RhetTbull/osxphotos

This may be helpful for allowing Smart Albums in Photos to filter by photo size.
Reference this reddit post: https://www.reddit.com/r/ApplePhotos/comments/15r4fk6/smart_album_filter_for_photovideo_dimensions/
"""

from __future__ import annotations

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, echo_error, query_command, verbose
from osxphotos.utils import pluralize


@query_command
@click.option(
    "--original",
    is_flag=True,
    help="If photo is edited, use original image size instead of edited image size",
)
@click.option(
    "--clear",
    is_flag=True,
    help="Remove existing size information from description",
)
def main(photos: list[osxphotos.PhotoInfo], original: bool, clear: bool, **kwargs):
    """Add the photo size in form widthxheight to each photo's caption in Photos
    If a photo has a caption, the size will be appended to the caption.

    Use --original to use the original image size instead of the edited image size.
    Use --clear to remove existing size information from caption.
    """
    echo(f"Processing {len(photos)} {pluralize(len(photos), 'photo', 'photos')}...")
    if clear:
        clear_size_str_from_photos(photos, original)
    else:
        add_size_str_to_photos(photos, original)
    echo("Done.")


def compute_size_str(photo: osxphotos.PhotoInfo, original: bool) -> str:
    """Return the size string for a given photo"""
    return (
        f"{photo.original_width}x{photo.original_height}"
        if original
        else f"{photo.width}x{photo.height}"
    )


def add_size_str_to_photos(photos: list[osxphotos.PhotoInfo], original: bool):
    """Add size string to photo description/caption"""
    for photo in photos:
        size_str = compute_size_str(photo, original)
        description = photo.description or ""  # description can be None
        if size_str in description:
            verbose(
                f"Skipping {photo.original_filename} ({photo.uuid}) ({size_str} already in caption)"
            )
            continue
        new_desc = f"{photo.description}\n{size_str}" if description else size_str
        verbose(
            f"Updating caption for {photo.original_filename} ({photo.uuid}) to {new_desc}"
        )
        update_description(photo, new_desc)


def clear_size_str_from_photos(photos: list[osxphotos.PhotoInfo], original: bool):
    """Clear size string from photo description/caption"""
    for photo in photos:
        size_str = compute_size_str(photo, original)
        description = photo.description or ""  # description can be None
        if size_str not in description:
            verbose(
                f"Skipping {photo.original_filename} ({photo.uuid}) ({size_str} not in caption)"
            )
            continue
        new_desc = description.replace(size_str, "").strip()
        verbose(
            f"Setting caption for {photo.original_filename} ({photo.uuid}) to {new_desc}"
        )
        update_description(photo, new_desc)


def update_description(photo: osxphotos.PhotoInfo, new_desc: str):
    """Update photo caption"""
    try:
        photoscript.Photo(photo.uuid).description = new_desc
    except Exception as e:
        echo_error(
            f"Error updating caption for {photo.original_filename} ({photo.uuid}): {e}"
        )


if __name__ == "__main__":
    main()
