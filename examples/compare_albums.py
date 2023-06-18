"""Compare two albums in Photos and find the differences."""

import sys

import click

import osxphotos


@click.command()
@click.argument("album1")
@click.argument("album2")
def compare_albums(album1, album2):
    print("Loading Photos library...")
    photosdb = osxphotos.PhotosDB()
    album1_ = None
    album2_ = None
    for album in photosdb.album_info:
        if album.title == album1:
            album1_ = album
        if album.title == album2:
            album2_ = album
    if album1_ is None:
        print("Album 1 not found:", album1)
        sys.exit(1)
    if album2_ is None:
        print("Album 2 not found:", album2)
        sys.exit(1)

    print(f"Comparing albums: '{album1}' '{album2}'")
    not_in_album2 = [photo for photo in album1_.photos if photo not in album2_.photos]
    not_in_album1 = [photo for photo in album2_.photos if photo not in album1_.photos]

    print(f"Photos in '{album1}' but not in '{album2}':")
    for photo in not_in_album2:
        print(f"  {photo.original_filename}, {photo.date}, {photo.uuid}")
    print(f"Photos in '{album2}' but not in '{album1}':")
    for photo in not_in_album1:
        print(f"  {photo.original_filename}, {photo.date}, {photo.uuid}")


if __name__ == "__main__":
    compare_albums()
