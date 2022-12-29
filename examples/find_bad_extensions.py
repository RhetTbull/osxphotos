"""Scan Photos library to find photos with bad (incorrect) file extensions.

This can be run with osxphotos via: osxphotos run find_bad_extensions.py

For help, run: osxphotos run find_bad_extensions.py --help
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import sys

import click
from rich import print

from osxphotos import PhotoInfo, PhotosDB
from osxphotos.cli.common import get_data_dir
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.sqlitekvstore import SQLiteKVStore


def check_extension(filepath: str) -> tuple[bool, str, str]:
    """Check if file extension is correct for image file using exiftool

    Args:
        filepath: path to file to check

    Returns: tuple of (bool, str, str) where bool is True if extension is correct, False if not
             and str, str is the current extension, correct extension or current extension if correct
    """
    filepath = pathlib.Path(filepath)
    current_ext = filepath.suffix.lower()

    current_ext = current_ext[1:] if current_ext else ""  # remove leading dot
    exiftool = ExifTool(filepath)
    correct_ext = exiftool.asdict().get("File:FileTypeExtension").lower()
    if current_ext != correct_ext:
        # there are some extensions that have more than one valid extension
        # there are likely more but these are the ones I've seen so far
        is_correct = (
            current_ext in ("jpg", "jpeg") and correct_ext in ("jpg", "jpeg")
        ) or (current_ext in ("tif", "tiff") and correct_ext in ("tif", "tiff"))
    else:
        is_correct = True
    return is_correct, current_ext, correct_ext


def check_photo(
    photo: PhotoInfo, recheck: bool, version: str, kvstore: SQLiteKVStore
) -> None:
    """Check PhotoInfo for correct extension

    Args:
        photo: PhotoInfo instance
        recheck: if True, recheck even if previously checked
        version: "original" or "edited"
        kvstore: SQLiteKVStore instance to store results
    """
    photo_path = photo.path if version == "original" else photo.path_edited
    if photo_path is None:
        print(
            f":warning-emoji:  [yellow]No {version} path for photo: {photo.original_filename} ({photo.uuid})",
            file=sys.stderr,
        )
        return
    if recheck or f"{photo.uuid}:{version}" not in kvstore:
        is_correct, current_ext, correct_ext = check_extension(photo_path)
        if not is_correct:
            print(
                f"{photo.original_filename} ({version}) has incorrect extension: [red]{current_ext}[/] should be [green]{correct_ext}[/]",
                file=sys.stderr,
            )
            # output results as CSV to stdout
            csv.writer(sys.stdout).writerow(
                [
                    photo.uuid,
                    photo.original_filename,
                    version,
                    current_ext,
                    correct_ext,
                    photo_path,
                ]
            )
        kvstore[f"{photo.uuid}:{version}"] = (is_correct, current_ext, correct_ext)


@click.command()
@click.option(
    "--library",
    default=None,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    help="Path to Photos library to use. Default is to use default Photos library.",
)
@click.option(
    "--recheck",
    is_flag=True,
    help="Recheck all files even if previously checked and cached.",
)
@click.option(
    "--edited",
    is_flag=True,
    help="Check edited versions of photos in addition to originals.",
)
def main(library: str, recheck: bool, edited: bool):
    """Scan Photos library to find photos with bad (incorrect) file extensions.

    This can be run with osxphotos via: `osxphotos run find_bad_extensions.py`

    Both STDOUT and STDERR are used to output results.

    STDOUT is used to output a CSV file with the following columns:

    uuid, original_filename, version, current_extension, correct_extension, path

    Thus, to save the results to a file, run:

    osxphotos run find_bad_extensions.py > results.csv
    """

    # exiftool required to run
    try:
        get_exiftool_path()
    except FileNotFoundError as e:
        print(
            ":cross_mark-emoji:  [red]Could not find exiftool. Please download and install"
            " from https://exiftool.org/",
            file=sys.stderr,
        )
        raise click.Abort() from e

    # path to the cache database to store results of extension check
    cache_db_path = os.path.join(get_data_dir(), "bad_extensions.db")
    kvstore = SQLiteKVStore(
        cache_db_path, wal=True, serialize=json.dumps, deserialize=json.loads
    )
    print(f"Using cache database: [blue]{cache_db_path}", file=sys.stderr)

    # load the Photos database and check each photo
    photosdb = PhotosDB(dbfile=library)
    for photo in photosdb.photos():
        check_photo(photo, recheck, "original", kvstore)
        if edited and photo.hasadjustments:
            check_photo(photo, recheck, "edited", kvstore)


if __name__ == "__main__":
    main()
