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

from osxphotos.platform import assert_macos

assert_macos()

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
from utitools import conforms_to_uti, uti_for_path

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

    if not is_image_file(filepath1) or not is_video_file(filepath2):
        # expects live pairs to be image, video
        return False

    return makelive.is_live_photo_pair(filepath1, filepath2)


def is_possible_live_pair(
    filepath1: str | os.PathLike, filepath2: str | os.PathLike
) -> bool:
    """Return True if photos could be a live photo pair (even if files lack the Content ID metadata"""
    if (is_image_file(filepath1) and is_video_file(filepath2)) or (
        is_video_file(filepath1) and is_image_file(filepath2)
    ):
        return True
    return False


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
            f"{match.group(1)}{match.group(2)}_E{match.group(3)}{match.group(4)}",
            str(file2),
        ):
            return True
    return False
