"""Recover photos from a Photos library where the database has been corrupted or is missing

Run this with: osxphotos run recover_photos.py <library_path> <output_path> [--dry-run]
"""

import datetime
import os
import pathlib
import sys
from functools import cache

import click
import xattr

import osxphotos
from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.cli.click_rich_echo import rich_echo_error as echo_error
from osxphotos.cli.import_cli import rename_edited_group
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.exifutils import get_exif_date_time_offset
from osxphotos.fileutil import FileUtilMacOS, FileUtilNoOp
from osxphotos.image_file_utils import is_image_file, is_raw_image, is_video_file
from osxphotos.utils import increment_filename


@click.command()
@click.option("--dry-run", is_flag=True, help="Dry run: don't actually copy files")
@click.argument("library_path", type=click.Path(exists=True))
@click.argument("destination", type=click.Path(dir_okay=True, file_okay=False))
def main(library_path: str, destination: str, dry_run: bool):
    """Recover photos from a Photos library where the database has been corrupted or is missing

    This script will scan the 'originals' directory of the Photos library to recover original photos
    and copy the original files to the destination directory.

    It will look for edited versions of the photos and copy those if they exist and and will also
    create .AAE files for edited photos that can be used by Photos or 'osxphotos import' to preserve
    non-destructive edits when re-importing the photos to the library.

    It will also attempt to recover the original filename for the photo if it is available in
    the extended attributes of the file and will also attempt to recover the original date/time
    of the photos. If the original filename is not available, it will use the current filename.
    If the original date/time is not available, it will use the current date/time of the file.

    In order to run this, you must first install exiftool (https://exiftool.org) and also install
    osxphotos (https://github.com/RhetTbull/osxphotos). The script can then be run with:
        osxphotos run recover_photos.py <library_path> <output_path> [--dry-run]

    The script will generate a lot of output. You may want to redirect the output to a file for easier
    review. For example:
        osxphotos run recover_photos.py <library_path> <output_path> [--dry-run] > recover.txt

    or

        osxphotos run recover_photos.py <library_path> <output_path> [--dry-run] | tee recover.txt

        which will show the output on the terminal and also write it to recover.txt

    Recovered files will be exported to the destination directory using YYYY/MM/DD directory structure.

    Use 'osxphotos run recover_photos.py --help' to view the help.
    """
    try:
        get_exiftool_path()
    except FileNotFoundError as e:
        echo(f"Error: {e}")
        sys.exit(1)

    library_path = pathlib.Path(library_path)
    destination = pathlib.Path(destination)
    originals = read_originals(library_path)

    echo(
        f"Attempting recovery of [num]{len(originals)}[/] photos from [filepath]{library_path}[/] to [filepath]{destination}[/]"
    )
    original_count = 0
    edited_count = 0
    aae_count = 0
    for original in originals:
        try:
            counts = export_file(library_path, destination, original, dry_run)
            original_count += counts[0]
            edited_count += counts[1]
            aae_count += counts[2]
        except Exception as e:
            echo_error(f"[error]Error processing [filename]{original}[/]: {e}")

    echo(
        f"Done. Recovered [num]{original_count}[/] original photos, "
        f"[num]{edited_count}[/] edited photos, and [num]{aae_count}[/] AAE files."
    )


def read_originals(library_path: pathlib.Path) -> list[pathlib.Path]:
    """Read the originals directory from a Photos library"""
    originals_path = library_path / "originals"
    if not originals_path.exists():
        raise ValueError(f"Originals path not found: {originals_path}")
    # return list of files in the originals directory excluding directories
    # and files that start with a dot
    return [
        p
        for p in originals_path.glob("**/*")
        if p.is_file() and not p.name.startswith(".")
    ]


def get_original_filename(path: pathlib.Path) -> str:
    """Get original filename from path"""
    # The original filename for photos in the Photos library is stored in the
    # com.apple.assetsd.originalFilename extended attribute
    # This function reads the extended attribute and returns the original filename
    # or the current filename if the extended attribute is not found
    try:
        original_filename = xattr.getxattr(
            str(path), "com.apple.assetsd.originalFilename"
        ).decode()
    except Exception as e:
        original_filename = path.name

    return fix_raw_pair_name(path, original_filename)


def fix_raw_pair_name(path: pathlib.Path, original_filename: str) -> str:
    """Fix the filename if it is a RAW+JPEG pair"""
    original_filename_pathlib = pathlib.Path(original_filename)
    if original_filename_pathlib.stem.endswith("_4") and is_raw_image(path):
        # Raw images of a raw+jpeg pair are stored with _4 suffix in the filename
        # for example, A92D9C26-3A50-4197-9388-CB5F7DB9FA91.jpeg and A92D9C26-3A50-4197-9388-CB5F7DB9FA91_4.cr2
        # If the correct original_name wasn't found and thus the original name still contains _4, rename the output file to drop the _4
        # This is a workaround for the case where the original filename is not found in the extended attributes
        # and should affect very few files but may affect files imported from a camera
        original_filename = (
            original_filename_pathlib.stem[:-2] + original_filename_pathlib.suffix
        )
    return original_filename


def get_date_time(path: pathlib.Path) -> datetime.datetime:
    """Return the original date and time for a photo"""
    exif = ExifTool(path).asdict()
    dt_info = get_exif_date_time_offset(exif, True)
    if dt_info.datetime:
        return dt_info.datetime
    else:
        # fall back to file modification time
        return datetime.datetime.fromtimestamp(path.stat().st_mtime)


@cache
def get_uuid(path: pathlib.Path) -> str:
    """Return the UUID for a photo"""
    # The UUID is stored in the com.apple.assetsd.UUID extended attribute
    # and in most cases (with exception of referenced files) will be the stem of the filename
    # first try to read the extended attribute
    # if that fails, return the stem of the filename
    try:
        uuid = xattr.getxattr(str(path), "com.apple.assetsd.UUID").decode()
        print(f"{uuid=}")
    except Exception as e:
        uuid = path.stem
    return uuid


def get_edited_path(
    library_path: pathlib.Path, path: pathlib.Path
) -> pathlib.Path | None:
    """Return the path to the edited version of the file"""
    # edited files are stored in the resources / renders directory
    # the path is constructed from the library path, the uuid of the photo
    uuid = get_uuid(path)
    if is_image_file(path):
        # edited version could be a HEIC or JPEG file
        # check both
        for ext in ["heic", "jpeg", "jpg"]:
            if edited := edited_path_for_ext(library_path, uuid, ext):
                return edited
        return None
    elif is_video_file(path):
        # edited version could be a MOV file
        return edited_path_for_ext(library_path, uuid, "mov")
    return None


def edited_path_for_ext(
    library_path: pathlib.Path, uuid: str, ext: str
) -> pathlib.Path | None:
    """Return edited path for extension"""
    directory = uuid[0]
    if ext in ["heic", "jpeg", "jpg"]:
        edited_path = (
            library_path / "resources" / "renders" / directory / f"{uuid}_1_201_a.{ext}"
        )
        if edited_path.exists():
            return edited_path
    elif ext == "mov":
        edited_path = (
            library_path / "resources" / "renders" / directory / f"{uuid}_2_0_a.mov"
        )
        if edited_path.exists():
            return edited_path
    return None


def get_aae_path(library_path: pathlib.Path, path: pathlib.Path) -> pathlib.Path | None:
    """Return the path to the AAE file for a photo"""
    # the AAE file, if it exists, is a .plist file with the same name as the photo in the resources / renders / directory
    directory = get_uuid(path)[0]
    aae_path = library_path / "resources" / "renders" / directory / f"{path.stem}.plist"
    if aae_path.exists():
        return aae_path
    return None


def get_output_path(
    output_path: pathlib.Path, date_time: datetime.datetime, original_filename: str
) -> pathlib.Path:
    """Get output path for photo in YYYY/MM/DD/original_filename format"""

    output_path = (
        output_path
        / date_time.strftime("%Y")
        / date_time.strftime("%m")
        / date_time.strftime("%d")
        / original_filename
    )
    if output_path.exists():
        output_path = pathlib.Path(increment_filename(output_path))
    return output_path


def export_file(
    library_path: pathlib.Path,
    destination: pathlib.Path,
    path: pathlib.Path,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Export a file to the destination, returns count of original, edited, and aae files exported"""
    exported_files = []
    fileutil = FileUtilNoOp if dry_run else FileUtilMacOS()
    original_filename = get_original_filename(path)
    date_time = get_date_time(path)
    edited_path = get_edited_path(library_path, path)
    aae_path = get_aae_path(library_path, path)
    output_path = get_output_path(destination, date_time, original_filename)
    original_count = 0
    edited_count = 0
    aae_count = 0
    if not dry_run:
        os.makedirs(output_path.parent, exist_ok=True)

    if output_path.exists():
        echo_error(f"[error]Error copying file {path}: {output_path} already exists")
    else:
        echo(f"Copying [filepath]{path}[/] to [filepath]{output_path}[/]")
        fileutil.copy(path, output_path)
        exported_files.append(output_path)
        original_count += 1

    if edited_path:
        edited_filename = output_path.stem + "_edited" + edited_path.suffix
        edited_output_path = output_path.parent / edited_filename
        if edited_output_path.exists():
            echo_error(
                f"[error]Error copying edited file {edited_path}: {edited_output_path} already exists"
            )
        else:
            echo(
                f"Copying edited file [filepath]{edited_path}[/] to [filepath]{edited_output_path}[/]"
            )
            fileutil.copy(edited_path, edited_output_path)
            exported_files.append(edited_output_path)
            edited_count += 1
    else:
        edited_output_path = None

    if aae_path:
        aae_filename = output_path.stem + ".aae"
        aae_output_path = output_path.parent / aae_filename
        if aae_output_path.exists():
            echo_error(
                f"[error]Error copying AAE file [filepath]{aae_path}[/]: [filepath]{aae_output_path}[/] already exists"
            )
        else:
            echo(
                f"Copying AAE file [filepath]{aae_path}[/] to [filepath]{aae_output_path}[/]"
            )
            fileutil.copy(aae_path, aae_output_path)
            exported_files.append(aae_output_path)
            aae_count += 1
    else:
        aae_output_path = None

    for path in exported_files:
        echo(
            f"Setting file modification and access time to [time]{date_time}[/] for [filepath]{path}[/]"
        )
        if not dry_run:
            try:
                touch_file(path, date_time)
            except Exception as e:
                echo_error(f"[error]Error touching date/time on {path}: {e}")

    if edited_output_path or aae_output_path:
        echo(f"Renaming edited group")
        if not dry_run:
            edited_group = [output_path]
            if edited_output_path:
                edited_group.append(edited_output_path)
            if aae_output_path:
                edited_group.append(aae_output_path)
            try:
                renamed_files = rename_edited_group(
                    edited_group,
                    "_edited",
                    None,
                    None,
                    False,
                    None,
                )
                echo(
                    f"Renamed files: {', '.join('[filename]'+f.name+'[/]' for f in renamed_files)}"
                )
            except Exception as e:
                echo_error(f"[error]Error renaming edited group: {e}")

    return original_count, edited_count, aae_count


def touch_file(path: pathlib.Path, dt: datetime.datetime):
    """Set file modification and access time to dt"""
    dt = dt.timestamp()
    os.utime(path, (dt, dt))


if __name__ == "__main__":
    main()
