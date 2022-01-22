""" ExifInfo class to expose EXIF info from the library """

from dataclasses import dataclass

__all__ = ["ExifInfo"]


@dataclass(frozen=True)
class ExifInfo:
    """EXIF info associated with a photo from the Photos library"""

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
