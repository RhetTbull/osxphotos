""" ExifInfo class to expose EXIF info from the library """

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from osxphotos.photos_datetime import photos_datetime

__all__ = ["ExifInfo", "exifinfo_factory"]


@dataclass(frozen=True)
class ExifInfo:
    """Original EXIF info associated with a photo from the Photos library"""

    flash_fired: bool | None = None
    iso: int | None = None
    metering_mode: int | None = None
    sample_rate: int | None = None
    track_format: int | None = None
    white_balance: int | None = None
    aperture: float | None = None
    bit_rate: float | None = None
    duration: float | None = None
    exposure_bias: float | None = None
    focal_length: float | None = None
    fps: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    shutter_speed: float | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    codec: str | None = None
    lens_model: str | None = None
    date: datetime.datetime | None = None
    tzoffset: int | None = None
    tzname: str | None = None


def exifinfo_factory(data: dict[str, Any] | None) -> ExifInfo:
    """Create an ExifInfo object from a dictionary of EXIF data"""
    if data is None:
        return ExifInfo()

    exif_info = ExifInfo(
        iso=data["ZISO"],
        flash_fired=True if data["ZFLASHFIRED"] == 1 else False,
        metering_mode=data["ZMETERINGMODE"],
        sample_rate=data["ZSAMPLERATE"],
        track_format=data["ZTRACKFORMAT"],
        white_balance=data["ZWHITEBALANCE"],
        aperture=data["ZAPERTURE"],
        bit_rate=data["ZBITRATE"],
        duration=data["ZDURATION"],
        exposure_bias=data["ZEXPOSUREBIAS"],
        focal_length=data["ZFOCALLENGTH"],
        fps=data["ZFPS"],
        latitude=data["ZLATITUDE"],
        longitude=data["ZLONGITUDE"],
        shutter_speed=data["ZSHUTTERSPEED"],
        camera_make=data["ZCAMERAMAKE"],
        camera_model=data["ZCAMERAMODEL"],
        codec=data["ZCODEC"],
        lens_model=data["ZLENSMODEL"],
        # ZDATECREATED, ZTIMEZONEOFFSET, ZTIMEZONENAME added in Ventura / Photos 8 so may not be present
        tzoffset=data.get("ZTIMEZONEOFFSET"),
        tzname=data.get("ZTIMEZONENAME"),
        date=photos_datetime(
            data.get("ZDATECREATED"),
            data.get("ZTIMEZONEOFFSET"),
            data.get("ZTIMEZONENAME"),
            default=False,
        ),
    )
    return exif_info
