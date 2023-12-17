"""Read metadata from photos and videos using exiftool or sidecar files"""

from __future__ import annotations

import json
import pathlib
import re
from collections import namedtuple
from typing import Optional, Tuple

from .exiftool import ExifToolCaching

EXIFTOOL_DEG_MIN_SEC_PATTERN = r"(\d+)\s*deg\s*(\d+)\'\s*(\d+\.\d+)\""

MetaData = namedtuple("MetaData", ["title", "description", "keywords", "location"])


def get_sidecar_for_file(filepath: str | pathlib.Path) -> pathlib.Path | None:
    """Get sidecar file for filepath if it exists or None

    Note:
        Tests for both JSON and XMP sidecar. If both exists, JSON is returned.
        Tests both with and without original suffix. If both exists, file with original suffix is returned.
        E.g. search order is: img_1234.jpg.json, img_1234.json, img_1234.jpg.xmp, img_1234.xmp
    """
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )
    for ext in ["json", "xmp"]:
        sidecar = pathlib.Path(f"{filepath}.{ext}")
        if sidecar.is_file():
            return sidecar
        sidecar = filepath.with_suffix("." + ext)
        if sidecar.is_file():
            return sidecar
    return None


def convert_exiftool_latitude(lat_string, lat_ref):
    """Convert latitude string from exiftool to decimal format"""
    # Regular expression to match and capture the degrees, minutes, and seconds
    match = re.match(EXIFTOOL_DEG_MIN_SEC_PATTERN, lat_string)

    if not match:
        raise ValueError(f"Invalid latitude string: {lat_string}")

    deg, minutes, seconds = map(float, match.groups())
    latitude = deg + minutes / 60 + seconds / 3600
    if lat_ref and lat_ref.upper()[:1] == "S":
        latitude = -latitude

    return latitude


def convert_exiftool_longitude(lon_string, lon_ref):
    """Convert longitude string from exiftool to decimal format"""
    # Regular expression to match and capture the degrees, minutes, and seconds
    match = re.match(EXIFTOOL_DEG_MIN_SEC_PATTERN, lon_string)

    if not match:
        raise ValueError(f"Invalid longitude string: {lon_string}")

    deg, minutes, seconds = map(float, match.groups())
    longitude = deg + minutes / 60 + seconds / 3600
    if lon_ref and lon_ref.upper()[:1] == "W":
        longitude = -longitude

    return longitude


def metadata_from_file(filepath: str | pathlib.Path, exiftool_path: str) -> MetaData:
    """Get metadata from file with exiftool

    Returns the following metadata from EXIF/XMP/IPTC fields as a MetaData named tuple
        title: str, XMP:Title, IPTC:ObjectName, QuickTime:DisplayName
        description: str, XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription, QuickTime:Description
        keywords: str, XMP:Subject, XMP:TagsList, IPTC:Keywords (QuickTime:Keywords not supported)
        location: Tuple[lat, lon],  EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef,  EXIF:GPSLongitude, QuickTime:GPSCoordinates, UserData:GPSCoordinates
    """
    exiftool = ExifToolCaching(filepath, exiftool_path)
    metadata = exiftool.asdict()
    return metadata_from_metadata_dict(metadata)


def metadata_from_sidecar(
    filepath: str | pathlib.Path, exiftool_path: str | None
) -> MetaData:
    """Get metadata from sidecar file; if file is XMP, exiftool must be installed.

    Returns: the following metadata from EXIF/XMP/IPTC fields as a MetaData named tuple
    title: str, XMP:Title, IPTC:ObjectName, QuickTime:DisplayName
    description: str, XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription, QuickTime:Description
    keywords: str, XMP:Subject, XMP:TagsList, IPTC:Keywords (QuickTime:Keywords not supported)
    location: Tuple[lat, lon],  EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef,  EXIF:GPSLongitude, QuickTime:GPSCoordinates, UserData:GPSCoordinates

    Raises:
        ValueError if error reading sidecar file
    """
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )
    if filepath.suffix.lower() == ".xmp":
        # use exiftool to read XMP sidecar
        exiftool = ExifToolCaching(filepath, exiftool_path)
        metadata = exiftool.asdict()
    else:
        with open(filepath, "r") as fp:
            try:
                metadata = json.load(fp)[0]
            except (json.JSONDecodeError, IndexError) as e:
                raise ValueError(f"Error reading sidecar file {filepath}: {e}")

    return metadata_from_metadata_dict(metadata)


def metadata_from_metadata_dict(metadata: dict) -> MetaData:
    """Return MetaData from metadata dict as loaded from ExifTool or sidecar"""

    title = (
        metadata.get("XMP:Title")
        or metadata.get("IPTC:ObjectName")
        or metadata.get("QuickTime:DisplayName")
        or metadata.get("Title")
        or metadata.get("ObjectName")
    )
    description = (
        metadata.get("XMP:Description")
        or metadata.get("IPTC:Caption-Abstract")
        or metadata.get("EXIF:ImageDescription")
        or metadata.get("QuickTime:Description")
        or metadata.get("Description")
        or metadata.get("Caption-Abstract")
        or metadata.get("ImageDescription")
    )
    keywords = (
        metadata.get("XMP:Subject")
        or metadata.get("XMP:TagsList")
        or metadata.get("IPTC:Keywords")
        or metadata.get("Subject")
        or metadata.get("TagsList")
        or metadata.get("Keywords")
    )

    title = title or ""
    description = description or ""
    keywords = keywords or []
    if not isinstance(keywords, (tuple, list)):
        keywords = [keywords]

    location = location_from_metadata_dict(metadata)
    return MetaData(title, description, keywords, location)


def location_from_metadata_dict(
    metadata: dict,
) -> Tuple[Optional[float], Optional[float]]:
    """Get location from metadata dict as loaded from ExifTool or sidecar

    Returns:
        Tuple of lat, long or None, None if not set

    Note:
        Attempts to get location from the following EXIF fields:
            EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
            EXIF:GPSLatitude, EXIF:GPSLongitude
            QuickTime:GPSCoordinates
            UserData:GPSCoordinates
    """
    # photos and videos store location data differently
    # for photos, location in EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef, EXIF:GPSLatitude, EXIF:GPSLongitude
    # the GPSLatitudeRef and GPSLongitudeRef are needed to determine N/S, E/W respectively
    # for example:
    #   EXIF:GPSLatitudeRef N
    #   EXIF:GPSLongitudeRef W
    #   EXIF:GPSLatitude 33.7198027777778
    #   EXIF:GPSLongitude 118.285491666667
    # for video, location in QuickTime:GPSCoordinates or UserData:GPSCoordinates as a
    # pair of positive/negative numbers thus no ref needed
    # for example:
    #   QuickTime:GPSCoordinates 34.0533 -118.2423

    latitude, longitude = None, None
    try:
        if latitude := metadata.get("EXIF:GPSLatitude") or metadata.get("GPSLatitude"):
            # this could be a float (as str) or a str in format:
            #  "GPSLatitude": "33 deg 42' 54.22\" N",
            #  "GPSLongitude": "118 deg 19' 10.81\" W",

            latitude_ref = metadata.get("EXIF:GPSLatitudeRef") or metadata.get(
                "GPSLatitudeRef"
            )
            latitude_ref = latitude_ref.upper()[:1] if latitude_ref else None

            if isinstance(latitude, str) and "deg" in latitude:
                try:
                    latitude = convert_exiftool_latitude(latitude, latitude_ref)
                except ValueError:
                    latitude = None
            else:
                latitude = float(latitude)
                if latitude_ref == "S":
                    latitude = -abs(latitude)
                elif latitude_ref and latitude_ref != "N":
                    latitude = None

        if latitude is None:
            latitude = float(metadata.get("XMP:GPSLatitude"))

        if longitude := metadata.get("EXIF:GPSLongitude") or metadata.get(
            "GPSLongitude"
        ):
            longitude_ref = metadata.get("EXIF:GPSLongitudeRef") or metadata.get(
                "GPSLongitudeRef"
            )
            longitude_ref = longitude_ref.upper()[:1] if longitude_ref else None

            if isinstance(longitude, str) and "deg" in longitude:
                try:
                    longitude = convert_exiftool_longitude(longitude, longitude_ref)
                except ValueError:
                    longitude = None
            else:
                longitude = float(longitude)
                if longitude_ref == "W":
                    longitude = -abs(longitude)
                elif longitude_ref and longitude_ref != "E":
                    longitude = None
        if longitude is None:
            longitude = float(metadata.get("XMP:GPSLongitude"))
        if latitude is None or longitude is None:
            # maybe it's a video
            if (
                lat_lon := metadata.get("QuickTime:GPSCoordinates")
                or metadata.get("UserData:GPSCoordinates")
                or metadata.get("GPSCoordinates")
            ):
                lat_lon = lat_lon.split()
                if len(lat_lon) != 2:
                    latitude = None
                    longitude = None
                else:
                    latitude = float(lat_lon[0])
                    longitude = float(lat_lon[1])
    except ValueError:
        # couldn't convert one of the numbers to float
        return None, None
    return latitude, longitude
