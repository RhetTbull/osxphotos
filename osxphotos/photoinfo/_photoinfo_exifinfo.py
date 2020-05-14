""" PhotoInfo methods to expose EXIF info from the library """

import logging
from dataclasses import dataclass

from .._constants import _PHOTOS_4_VERSION


@dataclass(frozen=True)
class ExifInfo:
    """ EXIF info associated with a photo from the Photos library """

    flash_fired: bool
    iso: int
    metering_mode: int
    sample_rate: int
    track_format: int
    white_balance: int
    aperture: float
    bit_rate: float
    duration: float
    exposure_bias: float
    focal_length: float
    fps: float
    latitude: float
    longitude: float
    shutter_speed: float
    camera_make: str
    camera_model: str
    codec: str
    lens_model: str


@property
def exif_info(self):
    """ Returns an ExifInfo object with the EXIF data for photo
        Note: the returned EXIF data is the data Photos stores in the database on import;
        ExifInfo does not provide access to the EXIF info in the actual image file
        Some or all of the fields may be None
        Only valid for Photos 5; on earlier database returns None
        """

    if self._db._db_version <= _PHOTOS_4_VERSION:
        logging.debug(f"exif_info not implemented for this database version")
        return None

    try:
        exif = self._db._db_exifinfo_uuid[self.uuid]
        exif_info = ExifInfo(
            iso=exif["ZISO"],
            flash_fired=True if exif["ZFLASHFIRED"] == 1 else False,
            metering_mode=exif["ZMETERINGMODE"],
            sample_rate=exif["ZSAMPLERATE"],
            track_format=exif["ZTRACKFORMAT"],
            white_balance=exif["ZWHITEBALANCE"],
            aperture=exif["ZAPERTURE"],
            bit_rate=exif["ZBITRATE"],
            duration=exif["ZDURATION"],
            exposure_bias=exif["ZEXPOSUREBIAS"],
            focal_length=exif["ZFOCALLENGTH"],
            fps=exif["ZFPS"],
            latitude=exif["ZLATITUDE"],
            longitude=exif["ZLONGITUDE"],
            shutter_speed=exif["ZSHUTTERSPEED"],
            camera_make=exif["ZCAMERAMAKE"],
            camera_model=exif["ZCAMERAMODEL"],
            codec=exif["ZCODEC"],
            lens_model=exif["ZLENSMODEL"],
        )
    except KeyError:
        logging.debug(f"Could not find exif record for uuid {self.uuid}")
        exif_info = ExifInfo(
            iso=None,
            flash_fired=None,
            metering_mode=None,
            sample_rate=None,
            track_format=None,
            white_balance=None,
            aperture=None,
            bit_rate=None,
            duration=None,
            exposure_bias=None,
            focal_length=None,
            fps=None,
            latitude=None,
            longitude=None,
            shutter_speed=None,
            camera_make=None,
            camera_model=None,
            codec=None,
            lens_model=None,
        )

    return exif_info
