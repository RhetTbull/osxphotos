"""Export selected Live photos and re-import just the image portion"""

import pathlib
import sys
import time
from tempfile import TemporaryDirectory
from typing import List

import click
from photoscript import Album, Photo, PhotosLibrary
from rich import print

from osxphotos import PhotoInfo, PhotosDB

DEFAULT_DELETE_ALBUM = "Live Photos to Delete"
DEFAULT_NEW_ALBUM = "Imported Live Photos"


def rename_photos(photo_paths: List[str]) -> List[str]:
    """Given a list of photo paths, rename the photos so names don't clash as duplicated on re-import"""
    # use perf_counter_ns as a simple unique ID to ensure each photo has a different name
    new_paths = []
    for path in photo_paths:
        path = pathlib.Path(path)
        stem = f"{path.stem}_{time.perf_counter_ns()}"
        new_path = path.rename(path.parent / f"{stem}{path.suffix}")
        new_paths.append(str(new_path))
    return new_paths


def set_metadata_from_photo(source_photo: PhotoInfo, dest_photos: List[Photo]):
    """Set metadata (keywords, albums, title, description, favorite) for dest_photos from source_photo"""
    title = source_photo.title
    description = source_photo.description
    keywords = source_photo.keywords
    favorite = source_photo.favorite

    # apply metadata to each photo
    for dest_photo in dest_photos:
        dest_photo.title = title
        dest_photo.description = description
        dest_photo.keywords = keywords
        dest_photo.favorite = favorite

    # add photos to albums
    album_ids = [a.uuid for a in source_photo.album_info]
    for album_id in album_ids:
        album = Album(album_id)
        album.add(dest_photos)


def process_photo(
    photo: Photo,
    photosdb: PhotosDB,
    keep_originals: bool,
    download_missing: bool,
    new_album: Album,
    delete_album: Album,
):
    """Process each Live Photo to export/re-import it"""
    with TemporaryDirectory() as tempdir:
        p = photosdb.get_photo(photo.uuid)
        if not p.live_photo:
            print(
                f"[yellow]Skipping non-Live photo {p.original_filename} ({p.uuid})[/]"
            )
            return

        # versions to download (True for edited, False for original)
        versions = []

        # use photos_export to download from iCloud
        photos_export = False

        # try to download missing photos only if photo is missing and --download-missing
        if keep_originals or not p.hasadjustments:
            # export original photo
            if not p.path and not download_missing:
                print(
                    f"[yellow]Skipping missing original version of photo {p.original_filename} ({p.uuid}) (you may want to try --download-missing)[/]"
                )
                return
            photos_export = download_missing and not p.path
            versions.append(False)

        if p.hasadjustments:
            if not p.path_edited and not download_missing:
                print(
                    f"[yellow]Skipping missing edited version of photo {p.original_filename} ({p.uuid}) (you may want to try --download-missing)[/]"
                )
                return
            photos_export = photos_export or (download_missing and not p.path_edited)
            versions.append(True)

        exported = []
        for version in versions:
            # export the actual photo (without the Live video)
            print(
                f"Exporting {'edited' if version else 'original'} photo {p.original_filename} ({p.uuid})"
            )
            if exports := p.export(
                tempdir,
                live_photo=False,
                edited=version,
                use_photos_export=photos_export,
            ):
                exported.extend(exports)
            else:
                print(
                    f"[red]Error exporting photo {p.original_filename} ({p.uuid})[/]",
                    file=sys.stderr,
                )

        if not exported:
            return

        exported = rename_photos(exported)
        print(
            f"Re-importing {', '.join([pathlib.Path(p).name for p in exported])} to album '{new_album.name}'"
        )
        new_photos = new_album.import_photos(exported)

        print("Applying metadata to newly imported photos")
        set_metadata_from_photo(p, new_photos)

        print(f"Moving {p.original_filename} to album '{delete_album.name}'")
        delete_album.add([Photo(p.uuid)])


@click.command()
@click.option(
    "--download-missing", is_flag=True, help="Download missing files from iCloud."
)
@click.option(
    "--keep-originals",
    is_flag=True,
    help="If photo is edited, also keep the original, unedited photo. "
    "Without --keep-originals, only the edited version of a Live photo that has been edited will be kept.",
)
@click.option(
    "--delete-album",
    "delete_album_name",
    default=DEFAULT_DELETE_ALBUM,
    help="Album to put Live photos in when they're ready to be deleted; "
    f"default = '{DEFAULT_DELETE_ALBUM}'",
)
@click.option(
    "--new-album",
    "new_album_name",
    default=DEFAULT_NEW_ALBUM,
    help="Album to put Live photos in when they've been re-imported after stripping the video component; "
    f"default = '{DEFAULT_NEW_ALBUM}'",
)
def strip_live_photos(
    download_missing, keep_originals, delete_album_name, new_album_name
):
    """Export selected Live photos and re-import just the image portion.

    This script can be used to free space in your Photos library by allowing you
    to effectively delete just the Live video portion of a Live photo.

    The photo part of the Live photo will be exported to a temporary directory then
    reimported into Photos. Albums, keywords, title/caption, favorite, and description
    will be preserved. Unfortunately person/face data cannot be preserved.

    After export Live photos will be moved to an album (which can be set using
    --delete-album) so they can be deleted. You can use Command + Delete to put the
    photos in the trash after selecting them in the album.
    """
    photoslib = PhotosLibrary()
    selected = photoslib.selection
    if not selected:
        print("No photos selected...nothing to do", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(selected)} photo(s)")
    print("Loading Photos database")
    photosdb = PhotosDB()

    new_album = photoslib.album(
        new_album_name, top_level=True
    ) or photoslib.create_album(new_album_name)
    delete_album = photoslib.album(
        delete_album_name, top_level=True
    ) or photoslib.create_album(delete_album_name)

    for photo in selected:
        process_photo(
            photo, photosdb, keep_originals, download_missing, new_album, delete_album
        )

    new_album.spotlight()


if __name__ == "__main__":
    strip_live_photos()
