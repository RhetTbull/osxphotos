"""Push EXIF data to original files in the Photos library"""

from __future__ import annotations

import os

import click
from rich.progress import Progress

from osxphotos import PhotoInfo
from osxphotos.exifwriter import ExifOptions, ExifWriter
from osxphotos.platform import assert_macos
from osxphotos.sidecars import exiftool_json_sidecar
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.utils import pluralize

from .cli_commands import echo, echo_error, query_command, selection_command, verbose
from .kvstore import kvstore
from .verbose import get_verbose_console

assert_macos()


@query_command(name="push-exif")
@click.option(
    "--push-edited",
    is_flag=True,
    help="Push EXIF data to edited photos in addition to originals",
)
def push_exif(photos: list[PhotoInfo], push_edited: bool, **kwargs):
    """Write photo metadata to original files in the Photos library

    This command will use exiftool (which must be installed separately)
    to write metadata to the original files in the Photos library.

    The metadata in Photos database including keywords, persons/faces, titles, etc.
    will be written to the original files.  This is useful if you want to ensure that
    the original file retains the metadata in the Photos database.

    You may use options to control which metadata is written to the original files.
    Metadata may also optionally be written to edited photos/videos using `--push-edited`.

    WARNING: This command will modify the original files in the Photos library.
    It is recommended that you make a backup of your Photos library before running
    this command. It is also not recommended that you run this command on a library
    that is managed by iCloud Photos. Changes to files in an iCloud library may not
    be synced back to iCloud. This is most useful for libraries that are not managed
    by iCloud Photos or for libraries using referenced files.

    The metadata is stored in a SQLite database in your home directory and will be used
    to automatically update or skip files as needed on subsequent runs of this command.
    """

    if not photos:
        echo_error("No photos selected for processing")
        raise click.Abort()

    echo(f"[num]{len(photos)}[/] photos selected for processing")
    echo(
        f":warning-emoji: [warning]This command will modify files in the Photos library: [filepath]{photos[0]._db.library_path}[/]"
    )
    click.confirm("Do you want to continue?", abort=True)

    update_db = kvstore("push_exif")
    echo(f"Using database: [filepath]{update_db.path}[/]")
    options = ExifOptions()
    with Progress(console=get_verbose_console()) as progress:
        num_photos = len(photos)
        task = progress.add_task(
            f"Processing [num]{num_photos}[/] {pluralize(num_photos, 'photo', 'photos')}",
            total=num_photos,
        )

        for photo in photos:
            photo_str = (
                f"[filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
            )
            progress.print(f"Processing {photo_str}")
            process_photo(photo, options, push_edited, update_db)
            progress.advance(task)


def process_photo(
    photo: PhotoInfo,
    options: ExifOptions,
    push_edited: bool,
    update_db: SQLiteKVStore,
) -> tuple[list[str], list[str]]:
    """
    Process a photo, writing metadata to files as needed

    Args:
        photo (PhotoInfo): The photo to process
        options (ExifOptions): The options to use when writing metadata
        push_edited (bool): Whether to write metadata to edited photos
        update_db (SQLiteKVStore): The database to use for storing metadata

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists: the list of files
        that were successfully written to, and the list of files that encountered errors
        during the writing process.
    """
    files_to_write = []
    written = []
    photo_str = f"[filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
    exif_sidecar = exiftool_json_sidecar(photo, options)

    # collect files to write
    if photo.path:
        files_to_write.append(photo.path)
    else:
        verbose(f"Skipping original for {photo_str} (missing path)")
    if photo.live_photo:
        if photo.path_live_photo:
            files_to_write.append(photo.path_live_photo)
        else:
            verbose(f"Skipping live photo for {photo_str} (missing path_live_photo)")
    if push_edited:
        if photo.path_edited:
            files_to_write.append(photo.path_edited)
        else:
            verbose(f"Skipping edited for {photo_str} (missing path_edited)")
        if photo.live_photo and photo.path_edited_live_photo:
            files_to_write.append(photo.path_edited_live_photo)
        else:
            verbose(
                f"Skipping edited live photo for {photo_str} (missing path_edited_live_photo)"
            )
    if photo.has_raw:
        if photo.path_raw:
            files_to_write.append(photo.path_raw)
        else:
            verbose(f"Skipping RAW for {photo_str} (missing path_raw)")

    error = []
    for filepath in files_to_write:
        photo_key = f"{photo.uuid}:{filepath}"
        if photo_key in update_db:
            # already processed this file
            if update_db[photo_key] == exif_sidecar:
                verbose(f"Skipping [filepath]{filepath}[/] (no update needed)")
                continue
            else:
                verbose(f"Updating [filepath]{filepath}[/] (metadata changed)")
        else:
            verbose(
                f"Writing metadata to [filepath]{filepath}[/] (not previously written)"
            )
        if write_exif(photo, filepath, options):
            update_db[photo_key] = exif_sidecar
            written.append(filepath)
        else:
            error.append(filepath)

    return written, error


def write_exif(photo: PhotoInfo, filepath: str, options: ExifOptions):
    """Write metadata to file with exiftool"""
    import time

    time.sleep(0.5)
    exif_writer = ExifWriter(photo)
    warnings, error = exif_writer.write_exif_data(filepath, options)
    if warnings:
        echo_error(f":warning-emoji: {warnings}")
    if error:
        echo_error(f":cross_mark-emoji: {error}")
        return False
    return True
