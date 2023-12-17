"""Read metadata from photos and videos using exiftool or sidecar files"""

from __future__ import annotations

import json
import pathlib
from collections import namedtuple
from typing import Optional, Tuple

from .exiftool import ExifToolCaching

MetaData = namedtuple("MetaData", ["title", "description", "keywords", "location"])


def metadata_from_file(filepath: pathlib.Path, exiftool_path: str) -> MetaData:
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
    filepath: pathlib.Path, exiftool_path: str | None
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
            #  "GPSLatitude": "33 deg 42' 54.22\" N",
            #  "GPSLongitude": "118 deg 19' 10.81\" W",

            latitude = float(latitude)
            latitude_ref = metadata.get("EXIF:GPSLatitudeRef") or metadata.get(
                "GPSLatitudeRef"
            )
            latitude_ref = latitude_ref.upper()[:1] if latitude_ref else None
            if latitude_ref == "S":
                latitude = -abs(latitude)
            elif latitude_ref and latitude_ref != "N":
                latitude = None
        if latitude is None:
            latitude = metadata.get("XMP:GPSLatitude")
        if longitude := metadata.get("EXIF:GPSLongitude") or metadata.get(
            "GPSLongitude"
        ):
            longitude = float(longitude)
            longitude_ref = metadata.get("EXIF:GPSLongitudeRef") or metadata.get(
                "GPSLongitudeRef"
            )
            longitude_ref = longitude_ref.upper()[:1] if longitude_ref else None
            if longitude_ref == "W":
                longitude = -abs(longitude)
            elif longitude_ref and longitude_ref != "E":
                longitude = None
        if longitude is None:
            longitude = metadata.get("XMP:GPSLongitude")
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
