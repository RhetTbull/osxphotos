"""Utilities for working with image files"""

from __future__ import annotations

import logging
import os
import pathlib
import plistlib
import re
import subprocess
from contextlib import suppress
from functools import cache
from typing import Any

from utitools import conforms_to_uti, uti_for_path

from osxphotos.platform import is_macos

if is_macos:
    try:
        # won't be installed on macOS < 11
        import cgmetadata
    except ImportError:
        cgmetadata = None

    try:
        # won't be installed on macOS < 11
        import makelive
    except ImportError:
        makelive = None

    import objc
    from Foundation import NSURL, NSURLTypeIdentifierKey

logger = logging.getLogger("osxphotos")

# regular expressions to match original + edited pairs
# if a pair of photos matching these regular expressions is imported, Photos creates an edited photo on import
ORIGINAL_RE = r"^(.*\/?)([A-Za-z]{3})_(\d{4})(.*)\.([a-zA-Z0-9]+)$"
EDITED_RE = r"^.*\/?[A-Za-z]{3}_E\d{4}.*$"


def file_conforms_to_uti(path: str | os.PathLike, uti: str) -> bool:
    """Return True if file at path conforms to UTI"""
    return conforms_to_uti(uti_for_path(path) or "", uti)


@cache
def is_image_file(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is an image file"""
    return file_conforms_to_uti(filepath, "public.image")


@cache
def is_video_file(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is a video file"""
    return file_conforms_to_uti(filepath, "public.movie")


@cache
def is_raw_image(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is a RAW image"""
    return file_conforms_to_uti(filepath, "public.camera-raw-image")


@cache
def is_jpeg_or_heic(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is a JPEG or HEIC/HEIF image.

    A live photo's still image is always a JPEG or HEIC/HEIF file; these are
    the only image types that can be paired with a QuickTime video to form a
    live photo.
    """
    return (
        file_conforms_to_uti(filepath, "public.jpeg")
        or file_conforms_to_uti(filepath, "public.heic")
        or file_conforms_to_uti(filepath, "public.heif")
    )


def is_raw_pair(filepath1: str | os.PathLike, filepath2: str | os.PathLike) -> bool:
    """Return True if one of the files is a RAW image and the other is a non-RAW image"""
    return (
        is_raw_image(filepath1)
        and (is_image_file(filepath2) and not is_raw_image(filepath2))
        or is_raw_image(filepath2)
        and (is_image_file(filepath1) and not is_raw_image(filepath1))
    )


def is_live_pair(filepath1: str | os.PathLike, filepath2: str | os.PathLike) -> bool:
    """Return True if photos are a live photo pair"""
    if not makelive:
        return False

    # A live photo pair is a still image (JPEG/HEIC) plus a QuickTime video.
    # Other image types (e.g. PNG) can't form a live photo, so return False
    # rather than letting makelive raise (see #2128).
    if not is_jpeg_or_heic(filepath1) or not is_video_file(filepath2):
        # expects live pairs to be image, video
        return False

    try:
        return makelive.is_live_photo_pair(filepath1, filepath2)
    except ValueError:
        # makelive raises ValueError if the files aren't a valid live photo
        # pair; treat that as "not a live pair" rather than crashing.
        return False


def is_possible_live_pair(
    filepath1: str | os.PathLike, filepath2: str | os.PathLike
) -> bool:
    """Return True if photos could be a live photo pair (even if files lack the Content ID metadata"""
    return bool(
        (is_image_file(filepath1) and is_video_file(filepath2))
        or (is_video_file(filepath1) and is_image_file(filepath2))
    )


def burst_uuid_from_path(path: pathlib.Path) -> str | None:
    """Get burst UUID of a file"""
    if not is_image_file(path):
        return None

    if not cgmetadata:
        return None

    md = cgmetadata.ImageMetadata(path)
    with suppress(KeyError):
        return md.properties["MakerApple"]["11"]
    return None


def load_aae_file(filepath: str | os.PathLike) -> dict[str, Any] | None:
    """Return plist dict if aae file is valid, else return None"""
    if not pathlib.Path(filepath).is_file():
        return None

    with open(filepath, "rb") as f:
        try:
            plist = plistlib.load(f)
        except plistlib.InvalidFileException:
            return None
    return plist


def is_apple_photos_aae_file(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is an AAE file containing Apple Photos adjustments; returns False is file contains adjustments for an external editor"""
    if plist := load_aae_file(filepath):
        if plist.get("adjustmentFormatIdentifier") in [
            "com.apple.photo",
            "com.apple.video",
        ]:
            return True
    return False


def is_edited_version_of_file(file1: pathlib.Path, file2: pathlib.Path) -> bool:
    """Return True if file2 appears to be an edited version of file1"""
    if match := re.match(ORIGINAL_RE, str(file1)):
        if re.match(
            f"{re.escape(match.group(1))}{match.group(2)}_E{match.group(3)}{re.escape(match.group(4))}",
            str(file2),
        ):
            return True
    return False
