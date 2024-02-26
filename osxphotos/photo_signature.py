"""Compute unique signature for photos"""

from __future__ import annotations

import datetime
import os
from typing import Any

from .fingerprint import fingerprint
from .photoinfo import PhotoInfo
from .photoinfo_file import PhotoInfoFromDict, PhotoInfoFromFile


def photo_signature(
    photo: PhotoInfo | PhotoInfoFromFile | dict | str | os.PathLike,
    exiftool: str | None = None,
) -> str:
    """Compute photo signature for a PhotoInfo or file"""
    if isinstance(photo, dict):
        photo = PhotoInfoFromDict(photo)
    elif not isinstance(photo, PhotoInfo):
        photo = PhotoInfoFromFile(photo, exiftool=exiftool)

    if photo.shared:
        return _shared_photo_signature(photo)

    if photo.fingerprint:
        return f"{photo.original_filename.lower()}:{photo.fingerprint}"

    if photo.path:
        return f"{photo.original_filename.lower()}:{fingerprint(photo.path)}"

    return f"{photo.original_filename.lower()}:{photo.original_filesize}"


def _shared_photo_signature(
    photo: PhotoInfo | PhotoInfoFromFile | PhotoInfoFromDict,
) -> str:
    """return a key for matching a shared photo between libraries"""
    date = photo.date
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return (
        f"{photo.cloud_owner_hashed_id}:"
        f"{photo.original_height}:"
        f"{photo.original_width}:"
        f"{photo.isphoto}:"
        f"{photo.ismovie}:"
        f"{date}"
    )
