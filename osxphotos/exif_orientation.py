"""Check and fix EXIF orientation in images."""

from __future__ import annotations

import logging
import os
import pathlib
import typing

from .exiftool import ExifTool, exiftool_can_write

if typing.TYPE_CHECKING:
    from .exportoptions import ExportOptions
    from .photoinfo import PhotoInfo

logger = logging.getLogger("osxphotos")

__all__ = ["check_exif_orientation", "fix_exif_orientation"]


def check_exif_orientation(
    orientation: int,
    src: str | os.PathLike,
    exiftool_path: str | None = None,
    exiftool_flags: list[str] | None = None,
) -> tuple[bool, int | None]:
    """Fix orientation of photo using exiftool to match the orientation in the photo info

    Args:
        orientation: orientation to check
        src: path to source file
        exiftool_path: path to exiftool
        exiftool_flags: list of flags to pass to exiftool

    Returns:
        tuple of True if orientation matches, False if orientation does not match and the orientation of the file
    """
    exiftool = ExifTool(src, exiftool=exiftool_path, flags=exiftool_flags)
    file_orientation = exiftool.asdict().get("EXIF:Orientation")
    if file_orientation == orientation:
        logger.debug(
            f"Orientation {file_orientation} matches orientation {orientation} for file {src}"
        )
        return True, file_orientation

    logger.debug(
        f"Orientation {file_orientation} does not match orientation {orientation} for file {src}"
    )
    return False, file_orientation


def fix_exif_orientation(
    photo: PhotoInfo, src: str | os.PathLike, options: ExportOptions
) -> tuple[bool, str]:
    """Fix orientation of photo using exiftool to match the orientation in the photo info

    Args:
        photo: PhotoInfo object
        src: path to source file
        options: ExportOptions object

    Returns:
        tuple of True if orientation was fixed, False if no fix was needed and string with message about the fix

    Note: This function modifies the source file
    """
    if not photo.orientation:
        # orientation is either an EXIF orientation (1-8) or 0 if no orientation is set
        status = f"Orientation is 0 for photo {photo.uuid}, no fix needed"
        logger.debug(status)
        return False, status

    if not isinstance(src, pathlib.Path):
        src = pathlib.Path(src)

    if not exiftool_can_write(src.suffix):
        status = f"exiftool cannot write to file {src}, skipping orientation fix"
        logger.debug(status)
        return False, status

    match, file_orientation = check_exif_orientation(
        photo.orientation,
        src,
        exiftool_path=photo._exiftool_path,
        exiftool_flags=options.exiftool_flags,
    )
    if match:
        status = f"Orientation matches for photo {photo.uuid}, no fix needed"
        logger.debug(status)
        return False, status

    if photo.orientation == 1 and file_orientation is None:
        status = f"File orientation not set for photo {photo.uuid} but photo orientation is 1 (normal), no fix needed"
        logger.debug(status)
        return False, status

    status = f"File orientation {file_orientation} does not match photo.orientation {photo.orientation} for photo {photo.uuid}, fixing orientation"
    logger.debug(status)
    if not options.dry_run:
        exiftool = ExifTool(
            src, exiftool=photo._exiftool_path, flags=options.exiftool_flags
        )
        exiftool.setvalue("EXIF:Orientation", photo.orientation)
    return True, status
