"""Utilities for working with image files"""

from __future__ import annotations

import os
import pathlib
import plistlib
import re
from contextlib import suppress
from functools import cache
from typing import Any
from weakref import ref
import subprocess
import logging

from osxphotos.platform import assert_macos

assert_macos()

import cgmetadata
import makelive
import osxmetadata

logger = logging.getLogger("osxphotos")

# regular expressions to match original + edited pairs
# if a pair of photos matching these regular expressions is imported, Photos creates an edited photo on import
ORIGINAL_RE = r"^(.*\/?)([A-Za-z]{3})_(\d{4}).*$"
EDITED_RE = r"^.*\/?[A-Za-z]{3}_E\d{4}.*$"


def content_tree(filepath: str | os.PathLike) -> list[str]:
    """Return the content tree for a file"""
    try:
        md = osxmetadata.OSXMetaData(str(filepath))
        return md.get("kMDItemContentTypeTree") or []
    except Exception as e:
        # sometimes osxmetadata fails on certain external volumes, so try using mdls
        return content_tree_mdls(filepath)


def content_tree_mdls(filepath: str | os.PathLike) -> list[str]:
    try:
        result = subprocess.run(
            ["mdls", "-raw", "-name", "kMDItemContentTypeTree", filepath],
            capture_output=True,
            text=True,
            check=True,
        )
        # Clean up the output by removing the enclosing parentheses and splitting into a list
        output = result.stdout.strip()
        output = output.strip("()%")
        content_types = [item.strip().strip('"') for item in output.split(",")]
        return content_types
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error executing mdls command to get content tree: {e}")
        return []


@cache
def is_image_file(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is an image file"""
    return "public.image" in content_tree(filepath)


@cache
def is_video_file(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is a video file"""
    return "public.movie" in content_tree(filepath)


@cache
def is_raw_image(filepath: str | os.PathLike) -> bool:
    """Return True if filepath is a RAW image"""
    return "public.camera-raw-image" in content_tree(filepath)


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
    if not is_image_file(filepath1) or not is_video_file(filepath2):
        # expects live pairs to be image, video
        return False
    return makelive.is_live_photo_pair(filepath1, filepath2)


def is_possible_live_pair(
    filepath1: str | os.PathLike, filepath2: str | os.PathLike
) -> bool:
    """Return True if photos could be a live photo pair (even if files lack the Content ID metadata"""
    if is_image_file(filepath1) and is_video_file(filepath2):
        return True
    return False


def burst_uuid_from_path(path: pathlib.Path) -> str | None:
    """Get burst UUID of a file"""
    if not is_image_file(path):
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
        if plist.get("adjustmentFormatIdentifier") == "com.apple.photo":
            return True
    return False


def is_edited_version_of_file(file1: pathlib.Path, file2: pathlib.Path) -> bool:
    """Return True if file2 appears to be an edited version of file1"""
    if match := re.match(ORIGINAL_RE, str(file1)):
        if re.match(f"{match.group(1)}{match.group(2)}_E{match.group(3)}", str(file2)):
            return True
    return False
