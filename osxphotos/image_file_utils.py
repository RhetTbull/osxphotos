"""Utilities for working with image files"""

from __future__ import annotations

import os
import pathlib
from contextlib import suppress
from functools import cache

from osxphotos.platform import assert_macos

assert_macos()

import cgmetadata
import makelive
import osxmetadata


def content_tree(filepath: str | os.PathLike) -> list[str]:
    """Return the content tree for a file"""
    md = osxmetadata.OSXMetaData(str(filepath))
    return md.get("kMDItemContentTypeTree") or []


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
