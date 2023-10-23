"""Write metadata from Photos to photo and video files that have been exported from Photos. 

 Run with osxphotos using `osxphotos run sync_photos_exif_to_files.py METADATA [OPTIONS] PATH_OR_FILENAMES`

 For help, run `osxphotos run sync_photos_exif_to_files.py --help`
 """

from __future__ import annotations

import pathlib
from typing import Any, Callable

import click
import objc
from Foundation import NSURL
from rich.progress import Progress

from osxphotos import PhotoInfo, PhotosDB, QueryOptions
from osxphotos.cli import echo, echo_error
from osxphotos.cli.param_types import CSVOptions
from osxphotos.cli.push_exif import set_options_from_metadata
from osxphotos.cli.verbose import get_verbose_console, verbose_print
from osxphotos.exifwriter import ExifOptions, ExifWriter
from osxphotos.exportoptions import ExportOptions
from osxphotos.fileutil import FileUtil
from osxphotos.touch_files import touch_files


class CPLResourceIdentity:
    """Dummy class to keep editor happy; will be replaced by objc.loadBundle()"""

    def fingerPrintForFileAtURL_error_(self, url: NSURL, error: Any) -> str:
        pass

    def fingerPrintForFileAtURL_typeIdentifier_error_(
        self, url: NSURL, type_identifier: Any, error: Any
    ) -> str:
        pass


# Load the CloudPhotoLibrary private framework
objc.loadBundle(
    "CPLResourceIdentity",
    bundle_path=objc.pathForFramework(
        "/System/Library/PrivateFrameworks/CloudPhotoLibrary.framework"
    ),
    module_globals=globals(),
)


def fingerprint(file_path: str | pathlib.Path) -> str:
    """Compute fingerprint of a file using the same algorithm as Photos.app; uses a private, undocumented framework."""

    with objc.autorelease_pool():
        # Convert the file URL to an NSURL object
        url = NSURL.fileURLWithPath_(str(file_path))

        # the method name is different on different versions of macOS
        # so try both, starting with the current version
        try:
            # this works on Ventura but not Catalina
            return CPLResourceIdentity.fingerPrintForFileAtURL_error_(url, None)
        except AttributeError:
            # this works on Catalina
            return CPLResourceIdentity.fingerPrintForFileAtURL_typeIdentifier_error_(
                url, None, None
            )


@click.command()
@click.argument(
    "metadata",
    required=True,
    type=CSVOptions(
        [
            "all",
            "keywords",
            "location",
            "faces",
            "persons",
            "datetime",
            "title",
            "description",
        ]
    ),
)
@click.option(
    "--key",
    "-k",
    "key_func",
    metavar="KEY",
    help="Key to use for matching exported files to originals in Photos library. "
    "The default is to match on fingerprint (a hash of the file contents) "
    "If you have edited the exported files, you may need to use another key such as "
    "filename. Valid keys are fingerprint, filename, size. "
    "Keys may be combined in any order with a comma, e.g. 'filename,size'. "
    "If multiple files match the same photo, the first one found will be used or multiple "
    "photos match the file, the first one found will be used.",
    type=CSVOptions(["fingerprint", "filename", "size"]),
    default="fingerprint",
)
@click.option(
    "--touch",
    "-t",
    is_flag=True,
    help="Touch file after writing metadata to sync Finder dates to EXIF dates",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recursively search any directories in PATH_OR_FILES for files",
)
@click.option(
    "--dry-run", is_flag=True, help="Dry run only; do not write metadata files"
)
@click.option(
    "--same-name",
    is_flag=True,
    help="Assume unmatched files in the same directory as a matched file with the same basename "
    "belong to the same photo (for example, Live Photos or RAW+JPEG pairs)",
)
@click.option(
    "--library", "-l", help="Specify Photos library path", type=click.Path(exists=True)
)
@click.argument("path_or_files", nargs=-1, type=click.Path(exists=True))
def main(
    metadata: str,
    key_func: tuple[str, ...],
    touch: bool,
    recursive: bool,
    dry_run: bool,
    same_name: bool,
    library: str,
    path_or_files: tuple[str, ...],
):
    """Export metadata from Photos to files that have been exported from Photos.

    Run with osxphotos using:
     `osxphotos run sync_photos_exif_to_files.py METADATA [OPTIONS] PATH_OR_FILENAMES`

    Why use this script? You exported files from Photos.app using the "Export Unmodified Originals" option
    and now want to sync the metadata from Photos (keywords, dates, etc.) to the exported files.

    This script will attempt to match the exported files to the originals in Photos.app and write the metadata
    using exiftool (https://exiftool.org/). You must download and install exiftool for this script to work, either
    directly from the exiftool website or via homebrew (https://brew.sh/, brew install exiftool).

    METADATA is a comma separated string of one or more values that indicates which metadata to export.
    METADATA must be one or more of the following, separated by commas:

    all keywords location faces persons datetime title description

    - all: all metadata

    - keywords: keywords/tags (e.g. IPTC:Keywords, etc.)

    - location: location information (e.g. EXIF:GPSLatitude, EXIF:GPSLongitude, etc.)

    - faces: face region information (e.g. XMP:RegionName, etc.)

    - persons: person in image information (e.g. XMP:PersonInImage, etc.)

    - datetime: date/time information (e.g. EXIF:DateTimeOriginal, etc.)

    - title: title information (e.g. XMP:Title, etc.)

    - description: description information (e.g. XMP:Description, etc.)

    For example, to export keywords and location information:

        osxphotos run sync_photos_exif_to_files.py keywords,location [OPTIONS] PATH_OR_FILENAMES

    For help, run `osxphotos run sync_photos_exif_to_files.py --help`
    """

    # configure verbose printing so console output is formatted correctly
    verbose_print(highlight=False)

    if not path_or_files:
        echo_error("No files to process")
        return

    # load photos library
    echo("Loading Photos library")
    photosdb = PhotosDB(dbfile=library)
    photos = photosdb.query(QueryOptions(shared=False))
    if not photos:
        echo("No photos to export")
        return
    echo(f"Loaded [num]{len(photos)}[/] photo(s) from Photos library")

    # collect files to process
    echo("Collecting files to process")
    files = collect_files(path_or_files, recursive)
    echo(f"Found [num]{len(files)}[/] file(s) to process.")

    # sync metadata
    sync_metadata(
        photos=photos,
        metadata=metadata,
        key_func=key_func,
        files=files,
        dry_run=dry_run,
        touch=touch,
        same_name=same_name,
    )


def sync_metadata(
    photos: list[PhotoInfo],
    metadata: tuple[str, ...],
    key_func: tuple[str, ...],
    files: list[pathlib.Path],
    dry_run: bool,
    touch: bool,
    same_name: bool,
):
    """Sync metadata from Photos to files

    Args:
        photos: list of PhotoInfo objects
        metadata: tuple of metadata to sync
        key_func: tuple of keys to use for matching files to Photos library
        files: list of files to sync
        dry_run: if True, do not write metadata
        touch: if True, touch file after writing metadata to sync Finder dates to EXIF dates (but not if dry_run)
    """

    # compute key map for matching files to Photos library
    echo("Creating key map for matching files to Photos library")
    file_keys = compute_file_keys(key_func, files)
    photo_keys = compute_photo_keys(key_func, photos)

    # sync metadata
    options = ExifOptions()
    options = set_options_from_metadata(options, metadata)

    # dict to track matched; key is parent directory of file
    # value is a dict with key of filename and value of matching photo
    matched = {}

    # dict to track unmatched files
    # key is parent directory of file, value is list of files
    unmatched = {}

    with Progress(console=get_verbose_console()) as progress:
        task = progress.add_task("Matching metadata", total=len(files))
        for file_key, files in file_keys.items():
            if file_key in photo_keys:
                if len(photo_keys[file_key]) > 1:
                    progress.print(
                        f"Found [num]{len(files)}[/] matching photos for file key [uuid]{file_key}[/]; using first one found"
                    )
                photo = photo_keys[file_key][0]
                # write the metadata
                for file_ in files:
                    sync_metadata_for_file(
                        photo=photo,
                        filepath=file_,
                        options=options,
                        dry_run=dry_run,
                        touch=touch,
                        echo=progress.print,
                    )
                    matched.setdefault(file_.parent, {})[file_.name] = photo
            else:
                for file_ in files:
                    progress.print(
                        f":warning-emoji: [warning]No photo found matching file(s) [filepath]{files[0]}[/] in Photos library"
                    )
                    unmatched.setdefault(file_.parent, []).append(file_)
            for _ in range(len(files)):
                progress.advance(task)

    # sync metadata for unmatched files
    if unmatched:
        unmatched_files = sum(len(v) for v in unmatched.values())
        echo(f"Did not find matching photo for [num]{unmatched_files}[/] file(s)")
        if same_name:
            with Progress(console=get_verbose_console()) as progress:
                task = progress.add_task(
                    "Looking for files with same basename as matched files",
                    total=len(unmatched),
                )
                for parent, files in unmatched.items():
                    if parent in matched:
                        for f in files:
                            f = pathlib.Path(f)
                            basename = f.stem
                            for matched_file in matched[parent]:
                                matched_file_stem = pathlib.Path(matched_file).stem
                                if matched_file_stem == basename:
                                    progress.print(
                                        f"Matched [filepath]{f}[/] to [filepath]{matched_file}[/]"
                                    )
                                    photo = matched[parent][matched_file]
                                    filepath = parent / f
                                    sync_metadata_for_file(
                                        photo=photo,
                                        filepath=filepath,
                                        options=options,
                                        dry_run=dry_run,
                                        touch=touch,
                                        echo=progress.print,
                                    )
                    progress.advance(task)


def sync_metadata_for_file(
    photo: PhotoInfo,
    filepath: pathlib.Path,
    options: ExifOptions,
    dry_run: bool,
    touch: bool,
    echo: Callable[[Any], None],
):
    echo(
        f"Syncing metadata from photo [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/]) to file [filepath]{filepath}"
    )
    if not dry_run:
        exif_writer = ExifWriter(photo)
        exif_writer.write_exif_data(filepath, options)
    if touch:
        echo(
            f"Touching file [filepath]{filepath}[/] to sync Finder dates to EXIF dates"
        )
        if not dry_run:
            # borrow the touch_files code from PhotoExporter as it does what we need
            touch_files(photo, [filepath], ExportOptions(fileutil=FileUtil))


def collect_files(path_or_files: tuple[str], recursive: bool) -> list[pathlib.Path]:
    """Collect files to process"""
    files = []
    if recursive:
        files = []
        for path_or_file in path_or_files:
            path = pathlib.Path(path_or_file)
            if path.is_dir():
                files.extend(path.glob("**/*"))
            else:
                files.append(path)
    else:
        files = [pathlib.Path(path_or_file) for path_or_file in path_or_files]
    # filter out directories
    files = [f for f in files if f.is_file()]
    return files


def compute_file_keys(
    keys: tuple[str], files: list[pathlib.Path]
) -> dict[str, list[pathlib.Path]]:
    """Compute keys for matching files to Photos library"""
    key_map = {
        "fingerprint": lambda x: fingerprint(x),
        "filename": lambda x: x.name,
        "size": lambda x: x.stat().st_size,
    }
    key_funcs = [key_map[k] for k in keys]
    file_keys = {}
    for file in files:
        file_key = tuple([f(file) for f in key_funcs])
        if file_key in file_keys:
            file_keys[file_key].append(file)
        else:
            file_keys[file_key] = [file]
    return file_keys


def compute_photo_keys(
    keys: tuple[str], photos: list[PhotoInfo]
) -> dict[str, list[PhotoInfo]]:
    """Compute keys for matching photos to files"""
    key_map = {
        "fingerprint": lambda x: x.fingerprint,
        "filename": lambda x: x.original_filename,
        "size": lambda x: x.original_filesize,
    }
    key_funcs = [key_map[k] for k in keys]
    photo_keys = {}
    for photo in photos:
        photo_key = tuple([f(photo) for f in key_funcs])
        if photo_key in photo_keys:
            photo_keys[photo_key].append(photo)
        else:
            photo_keys[photo_key] = [photo]
    return photo_keys


if __name__ == "__main__":
    main()
