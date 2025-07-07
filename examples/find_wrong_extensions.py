"""Find photos and videos with mismatched UTI and/or extension in the Photos library

Run with: osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/refs/heads/main/examples/find_wrong_extensions.py
"""

import pathlib
from dataclasses import dataclass

import click
from utitools import uti_for_suffix

import osxphotos
from osxphotos.cli import echo, echo_error, query_command, verbose
from osxphotos.exiftool import get_exiftool_path


@dataclass
class ExtensionMismatch:
    photo: osxphotos.PhotoInfo | None = None
    original_uti: str | None = None
    original_suffix: str | None = None
    original_filename_uti: str | None = None
    actual_uti: str | None = None
    actual_suffix: str | None = None


def check_photo_extensions(photos: list[osxphotos.PhotoInfo]):
    """Check photo extensions and UTI for mismatches."""

    results = []
    for p in photos:
        # three different ways to get UTI:
        # PhotoInfo.uti,
        # PhotoInfo.exiftool.asdict().get("File:FileTypeExtension") (what exiftool thinks the file actually us),
        # PhotoInfo.original_filename
        # If any of these don't match, add to mismatch list

        mismatch = 0
        mismatch_data = ExtensionMismatch(photo=p)

        # check uti against original_filename (can be done without path / exiftool)
        original_suffix = pathlib.Path(p.original_filename).suffix.lower()
        try:
            original_filename_uti = uti_for_suffix(original_suffix).lower()
        except Exception as e:
            original_filename_uti = None
        original_uti = p.uti.lower()

        mismatch_data.original_uti = original_uti
        mismatch_data.original_suffix = original_suffix
        mismatch_data.original_filename_uti = original_filename_uti

        if original_filename_uti != original_uti:
            mismatch += 1

        # checks that require the original file be on disk
        if not p.path:
            continue
        try:
            extension = p.exiftool.asdict().get("File:FileTypeExtension", "")
            extension = f".{extension.lower()}"
            uti_for_extension = uti_for_suffix(extension).lower()
            mismatch_data.actual_suffix = extension
            mismatch_data.actual_uti = uti_for_extension
            if uti_for_extension != original_uti:
                mismatch += 1
            elif uti_for_extension != uti_for_suffix(original_suffix):
                mismatch += 1
            elif uti_for_extension != uti_for_suffix(pathlib.Path(p.path).suffix):
                mismatch += 1
        except Exception as e:
            pass

        if mismatch:
            results.append(mismatch_data)

    return results


@query_command
def main(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Find photos with mismatched UTI and/or extension.

    Requires exiftool to be installed and in the system path.

    Prints a CSV report of photos with mismatched UTI and/or extension.
    """

    if not get_exiftool_path():
        echo_error("exiftool not found. Please install exiftool: https://exiftool.org/")
        raise click.Abort()

    if not photos:
        echo("No photos in query result.")
        return

    verbose(f"Checking {len(photos)} photo{'s' if len(photos) != 1 else ''}")
    results = check_photo_extensions(photos)
    if results:
        echo(
            "filename, uuid, shared_photo, original_uti, original_suffix, actual_uti, actual_suffix"
        )
        for result in results:
            echo(
                ", ".join(
                    [
                        result.photo.original_filename,
                        result.photo.uuid,
                        str(result.photo.shared),
                        result.original_uti,
                        result.original_suffix,
                        result.actual_uti,
                        result.actual_suffix,
                    ]
                )
            )


if __name__ == "__main__":
    main()
