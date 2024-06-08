"""Compute unique signature for photos"""

from __future__ import annotations

import datetime
import os

from .photoinfo import PhotoInfo
from .photoinfo_dict import PhotoInfoFromDict, photoinfo_from_dict
from .photoinfo_file import PhotoInfoFromFile
from .platform import is_macos

if is_macos:
    from .fingerprint import fingerprint


def photo_signature(
    photo: PhotoInfo | PhotoInfoFromFile | dict | str | os.PathLike,
    exiftool: str | None = None,
) -> str:
    """Compute photo signature for a PhotoInfo, a PhotoInfo dict, or file path"""
    if isinstance(photo, dict):
        photo = photoinfo_from_dict(photo)
    elif not isinstance(photo, PhotoInfo):
        photo = PhotoInfoFromFile(photo, exiftool=exiftool)

    if photo.shared:
        return _shared_photo_signature(photo)

    if photo.fingerprint:
        return f"{photo.original_filename.lower()}:{photo.fingerprint}"

    if photo.path and is_macos:
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
