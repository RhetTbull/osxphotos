"""Incrementally adjust the time of photos by a fixed amount."""

from __future__ import annotations

import datetime

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, echo_error


@click.command()
@click.option(
    "--time-delta",
    "-t",
    type=int,
    help="Time delta in seconds to adjust photos by",
)
@click.option("--dry-run", is_flag=True, help="Dry run (do not modify library)")
@click.argument("album_name")
def increment(time_delta, dry_run, album_name, **kwargs):
    """Increment the time of photos in an album by a given increment

    For example:

        osxphotos run increment_time.py --time-delta 10 MyAlbum

    will increment the time of all photos in the album "MyAlbum" by 10 seconds.

    Photos will be processed using the current sort order for the album.
    """

    if time_delta is None:
        echo_error("No time delta provided")
        raise click.Abort()

    photosdb = osxphotos.PhotosDB()
    album = get_album(photosdb, album_name)
    if album is None:
        echo_error(f"Could not find album {album_name} in Photos library.")
        raise click.Abort()

    photos = album.photos
    if not photos:
        echo("No photos to process")
        return

    echo(f"Adjusting {len(photos)} photo(s) by {time_delta} seconds")
    for photo in photos:
        try:
            photo_ = photoscript.Photo(photo.uuid)
        except Exception as e:
            echo(f"Error accessing photo {photo.uuid}: {e}")
            continue
        new_date = photo_.date + datetime.timedelta(seconds=time_delta)
        echo(
            f"Adjusting {photo.original_filename} ({photo.uuid}) from {photo_.date} to {new_date}"
        )
        if not dry_run:
            photo_.date = new_date


def get_album(
    photosdb: osxphotos.PhotosDB, album_name: str
) -> osxphotos.AlbumInfo | None:
    """Get album by name; if more than one album with the same name, return the first one"""
    for a in photosdb.album_info:
        if a.title == album_name:
            return a
    return None


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    increment()
