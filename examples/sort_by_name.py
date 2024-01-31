"""Adjust the timestamp of selects photos in Photos.app to sort the photos by name.

Reference this Reddit post: https://www.reddit.com/r/ApplePhotos/comments/1adqy5m/sort_photos_by_title_or_filename/

This will change the timestamp of the selected photos -- be sure this is what you want to do
as it cannot easily be undone.

Run this with osxphotos (https://github.com/RhetTbull/osxphotos):

1. Install osxphotos via these instructions: https://github.com/RhetTbull/osxphotos?tab=readme-ov-file#installation
2. Save this as sort_by_name.py
3. Run this script with osxphotos:
    osxphotos run sort_by_name.py
"""

from __future__ import annotations

import datetime

import click
import photoscript

from osxphotos.cli.param_types import DateTimeISO8601, TimeOffset
from osxphotos.utils import pluralize


@click.command()
@click.option(
    "--dry-run", is_flag=True, help="Dry run, don't actually change any photos"
)
@click.option(
    "--start",
    type=DateTimeISO8601(),
    help="Start date/time for photos to change; "
    "if not provided, uses earliest date/time from selected photo. "
    "Format: YYYY-MM-DDTHH:MM:SS, for example: 2020-01-01T12:00:00",
)
@click.option(
    "--step",
    type=TimeOffset(),
    default="1s",
    help="Time step to use for each photo beginning with --start;"
    "default is 1 sec.  Format: 1d, 1h, 1m, 1s, etc.",
)
def sort_by_name(dry_run, start, step):
    """Adjust the timestamp of selects photos in Photos.app to sort the photos by name."""
    photos = photoscript.PhotosLibrary().selection
    if not photos:
        click.echo(
            "No photos selected. Select photos in Photos.app and try again.", err=True
        )
        raise click.Abort()
    if len(photos) == 1:
        click.echo(
            "Only one photo selected. Select more than one photo and try again.",
            err=True,
        )
        raise click.Abort()

    if dry_run:
        click.echo("Dry run, no photos will be changed")

    click.echo(f"Processing {len(photos)} {pluralize(len(photos), 'photo', 'photos')}")

    if not start:
        start = min(validate_date(photo) for photo in photos)
    click.echo(f"Start date/time: {start}")

    step = step or 1
    click.echo(f"Time step: {step}")

    if not click.confirm(
        f"This will change the date of {len(photos)} {pluralize(len(photos), 'photo', 'photos')}.\n"
        f"The first photo will have date/time of {start} and each subsequent photo will be adjusted by {step} seconds.\n"
        "Do you want to continue?"
    ):
        raise click.Abort()

    photos = sorted(photos, key=lambda photo: photo.filename)
    for photo in photos:
        click.echo(f"Setting date for {photo.filename} to {start}")
        if not dry_run:
            photo.date = start
        start += step


def validate_date(photo: photoscript.Photo) -> datetime.datetime:
    """Verify a datetime is valid and if not return today's date."""
    try:
        return photo.date
    except Exception as e:
        return datetime.datetime.now()

if __name__ == "__main__":
    sort_by_name()
