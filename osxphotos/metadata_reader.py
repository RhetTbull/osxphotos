"""Read metadata from photos and videos using exiftool or sidecar files"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Callable, Optional, Tuple

from osxphotos.photoinfo_protocol import PhotoInfoProtocol

from .datetime_utils import (
    datetime_has_tz,
    datetime_naive_to_utc,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
    utc_offset_seconds,
)
from .exiftool import ExifToolCaching
from .exifutils import get_exif_date_time_offset

EXIFTOOL_DEG_MIN_SEC_PATTERN = r"(\d+)\s*deg\s*(\d+)\'\s*(\d+\.\d+)\""


@dataclass
class MetaData:
    """Metadata for a photo or video

    Attributes:
        title: title of photo
        description: description of photo
        keywords: list of keywords for photo
        location: tuple of lat, long or None, None if not set
        favorite: bool, True if photo marked favorite
        rating: int, rating of photo 0-5
        persons: list of persons in photo
        date: datetime for photo as naive datetime.datetime in local timezone or None if not set
        timezone: timezone or None of original date (before conversion to local naive datetime)
        tz_offset_sec: int or None if not set, offset from UTC in seconds
        height: int or None if not set, height of photo in pixels
        width: int or None if not set, width of photo in pixels
    """

    title: str = ""
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    location: tuple[Optional[float], Optional[float]] = (None, None)
    favorite: bool = False
    rating: int = 0
    persons: list[str] = field(default_factory=list)
    date: datetime.datetime | None = None
    timezone: datetime.tzinfo | None = None
    tz_offset_sec: float | None = None
    height: int | None = None
    width: int | None = None

    def __ior__(self, other):
        if isinstance(other, MetaData):
            for field in fields(self):
                other_value = getattr(other, field.name)
                self_value = getattr(self, field.name)
                if other_value:
                    setattr(self, field.name, other_value)
        else:
            raise TypeError("Unsupported operand type")
        return self


class SidecarFileType(Enum):
    """Enum for sidecar file type"""

    XMP = 1
    exiftool = 2
    osxphotos = 3
    GoogleTakeout = 4
    Unknown = 5


def get_sidecar_filetype(filepath: str | pathlib.Path) -> SidecarFileType:
    """Determine type of sidecar file"""
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )
    if filepath.suffix.lower() == ".xmp":
        return SidecarFileType.XMP
    elif filepath.suffix.lower() == ".json":
        # could be exiftool or osxphotos or Google Takeout
        with open(filepath, "r") as fp:
            try:
                metadata = json.load(fp)
            except json.JSONDecodeError:
                return SidecarFileType.Unknown
            if isinstance(metadata, list):
                # could be exiftool or osxphotos
                metadata = metadata[0]
                if metadata.get("ExifToolVersion"):
                    return SidecarFileType.exiftool
                elif metadata.get("ExifTool:ExifToolVersion"):
                    return SidecarFileType.osxphotos
            elif isinstance(metadata, dict):
                # could be Google Takeout
                # Google Takeout JSON appears to always have keys:
                # 'title', 'description', 'imageViews', 'creationTime',
                # 'photoTakenTime', 'geoData', 'geoDataExif', 'url'
                # Google Takeout is the only format to sometimes set 'googlePhotosOrigin'
                if ("googlePhotosOrigin" in metadata) or all(
                    k in metadata
                    for k in (
                        "title",
                        "description",
                        "imageViews",
                        "creationTime",
                        "photoTakenTime",
                        "geoData",
                        "geoDataExif",
                        "url",
                    )
                ):
                    return SidecarFileType.GoogleTakeout
    return SidecarFileType.Unknown


def get_sidecar_for_file(filepath: str | pathlib.Path) -> pathlib.Path | None:
    """Get sidecar file for filepath if it exists or None

    Note:
        Tests for both JSON and XMP sidecar. If both exists, JSON is returned.
        Tests both with and without original suffix. If both exists, file with original suffix is returned.
        E.g. search order is: img_1234.jpg.json, img_1234.json, img_1234.jpg.xmp, img_1234.xmp
        For Google Takeout, the sidecar may be named img_1234.jpg.json or img_1234.json;
        if the image is edited, it will be named img_1234-edited.jpg but the sidecar will still be
        named img_1234.jpg.json or img_1234.json so drop the -edited suffix when searching for the sidecar.
        If there is a duplicate file name, Google Takeout will append a number to the file name
        in form img_1234(1).jpg but the sidecar may be named img_1234.jpg(1).json
    """
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )
    for ext in [".json", ".xmp"]:
        sidecar = pathlib.Path(f"{filepath}{ext}")
        if sidecar.is_file():
            return sidecar
        sidecar = filepath.with_suffix(ext)
        if sidecar.is_file():
            return sidecar

    # if here, no sidecar found, check for Google Takeout formats
    # Google Takeout may append -edited to the file name but not the sidecar
    # If there is a duplicate file name, Google Takeout will append a number to the file name
    # in form img_1234(1).jpg but the sidecar may be named img_1234.jpg(1).json

    stem = filepath.stem
    # strip off -edited suffix (Google Takeout) or _edited (OSXPhotos edited images with default suffix)
    if stem.endswith("-edited") or stem.endswith("_edited"):
        # strip off -edited/_edited suffix
        stem = stem[:-7]
        new_filepath = filepath.with_stem(stem)
        return get_sidecar_for_file(new_filepath)

    # strip off (1) suffix for Google takeout naming scheme
    if match := re.match(r"(.*)(\(\d+\))$", stem):
        stem = match.groups()[0]
        new_filepath = pathlib.Path(
            str(filepath.with_stem(stem)) + match.groups()[1] + ".json"
        )
        if new_filepath.is_file():
            return new_filepath

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


def metadata_from_exiftool(
    filepath: str | pathlib.Path, exiftool_path: str | None
) -> MetaData:
    """Get metadata from file with exiftool

    Returns the following metadata from EXIF/XMP/IPTC fields as a MetaData named tuple
        title: str, XMP:Title, IPTC:ObjectName, QuickTime:DisplayName
        description: str, XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription, QuickTime:Description
        keywords: str, XMP:Subject, XMP:TagsList, IPTC:Keywords (QuickTime:Keywords not supported)
        location: Tuple[lat, lon],  EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef,  EXIF:GPSLongitude, QuickTime:GPSCoordinates, UserData:GPSCoordinates
        rating: int, XMP:Rating
        height: int, ImageHeight
        width: int, ImageWidth
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
    rating: int, XMP:Rating

    Raises:
        ValueError if error reading sidecar file
    """
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )

    sidecar_type = get_sidecar_filetype(filepath)

    if sidecar_type == SidecarFileType.XMP:
        # use exiftool to read XMP sidecar
        exiftool = ExifToolCaching(filepath, exiftool_path)
        metadata = exiftool.asdict()
        return metadata_from_metadata_dict(metadata)

    if sidecar_type in (SidecarFileType.exiftool, SidecarFileType.osxphotos):
        with open(filepath, "r") as fp:
            try:
                metadata = json.load(fp)[0]
            except (json.JSONDecodeError, IndexError) as e:
                raise ValueError(f"Error reading sidecar file {filepath}: {e}")
        return metadata_from_metadata_dict(metadata)

    if sidecar_type == SidecarFileType.GoogleTakeout:
        return metadata_from_google_takeout(filepath)

    raise ValueError(f"Unknown sidecar type for file {filepath}")


def metadata_from_google_takeout(filepath: str | pathlib.Path) -> MetaData:
    """Read metadata from Google Takeout JSON file"""
    with open(filepath, "r") as fp:
        try:
            metadata = json.load(fp)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error reading sidecar file {filepath}: {e}")

    title = metadata.get("title")
    description = metadata.get("description")
    favorite = metadata.get("favorited", False)
    geo_data = metadata.get("geoData", {})
    location = geo_data.get("latitude"), geo_data.get("longitude")
    if location == (0.0, 0.0):
        # Google Takeout uses 0.0, 0.0 to indicate no location
        location = None, None
    persons = [p["name"] for p in metadata.get("people", [])]
    timestamp = metadata.get("photoTakenTime", {}).get("timestamp")
    if timestamp:
        try:
            # Takeout JSON stores date as timestamp in UTC
            # regardless of timezone of photo
            # convert to naive datetime in local timezone
            # as that's what Photos uses
            date = datetime.datetime.fromtimestamp(int(timestamp))
            # From datetime.datetime.fromtimestamp docs:
            # Return the local date and time corresponding to the POSIX timestamp, such as is returned by time.time().
            # If optional argument tz is None or not specified, the timestamp is converted to the platform’s local date and time,
            # and the returned datetime object is naive.
        except ValueError:
            date = None
    else:
        date = None

    return MetaData(
        title=title or "",
        description=description or "",
        keywords=[],
        location=location,
        favorite=favorite,
        persons=persons,
        date=date,
        # Google Takeout doesn't store timezone but times are in UTC so cannot determine true timezone
        timezone=False,
        tz_offset_sec=0,
    )


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

    rating = metadata.get("XMP:Rating") or metadata.get("Rating")

    height = (
        metadata.get("File:ImageHeight")
        or metadata.get("EXIF:ImageHeight")
        or metadata.get("ImageHeight")
        or metadata.get("QuickTime:ImageHeight")
    )
    width = (
        metadata.get("File:ImageWidth")
        or metadata.get("EXIF:ImageWidth")
        or metadata.get("ImageWidth")
        or metadata.get("QuickTime:ImageWidth")
    )

    # adjust width, height if needed for the EXIF orientation
    # Note: this may not work properly for QuickTime files
    orientation = (
        metadata.get("EXIF:Orientation")
        or metadata.get("Orientation")
        or metadata.get("QuickTime:VideoOrientation")
    )
    width, height = width_height_for_orientation(width, height, orientation)

    persons = metadata.get("XMP:PersonInImage", []) or metadata.get("PersonInImage", [])
    if persons and not isinstance(persons, (tuple, list)):
        persons = [persons]

    date_info = get_exif_date_time_offset(metadata)
    date: datetime.datetime | None = date_info.datetime
    tz_offset, timezone = None, None
    if date and datetime_has_tz(date):
        # convert to naive datetime in local timezone as that is what Photos uses
        tz_offset = utc_offset_seconds(date)
        timezone = date.tzinfo
        date = datetime_remove_tz(datetime_utc_to_local(datetime_tz_to_utc(date)))

    title = title or ""
    description = description or ""
    keywords = keywords or []
    if not isinstance(keywords, (tuple, list)):
        keywords = [keywords]

    location = location_from_metadata_dict(metadata)

    return MetaData(
        title=title,
        description=description,
        keywords=keywords,
        location=location,
        rating=rating or 0,
        favorite=False,
        persons=persons,
        date=date,
        timezone=timezone,
        tz_offset_sec=tz_offset,
        height=height,
        width=width,
    )


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
            #  "GPSLatitude": "33 deg 42' 54.22\"",
            #  "GPSLongitude": "118 deg 19' 10.81\"",

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
            try:
                latitude = float(metadata.get("XMP:GPSLatitude"))
            except TypeError:
                latitude = None

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
            try:
                longitude = float(metadata.get("XMP:GPSLongitude"))
            except TypeError:
                longitude = None
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


def width_height_for_orientation(
    width: int | None, height: int | None, orientation: int | None
) -> tuple[int | None, int | None]:
    """Return width, height for given orientation"""
    if orientation is None:
        return width, height

    swap_orientations = {5, 6, 7, 8}
    if orientation in swap_orientations:
        return height, width
    else:
        return width, height


def metadata_from_photoinfo(photoinfo: PhotoInfoProtocol) -> MetaData:
    """Create a MetaData object from a PhotoInfo instance"""
    tz_offset = utc_offset_seconds(photoinfo.date)
    timezone = photoinfo.date.tzinfo
    date = datetime_remove_tz(datetime_utc_to_local(datetime_tz_to_utc(photoinfo.date)))
    location = tuple(photoinfo.location) if photoinfo.location else (None, None)
    return MetaData(
        title=photoinfo.title,
        description=photoinfo.description,
        keywords=photoinfo.keywords,
        location=location,
        rating=photoinfo.rating or 0,
        favorite=photoinfo.favorite,
        persons=photoinfo.persons,
        date=date,
        timezone=timezone,
        tz_offset_sec=tz_offset,
        height=photoinfo.height,
        width=photoinfo.width,
    )
