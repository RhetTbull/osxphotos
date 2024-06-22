"""Print information about one or more items selected in Photos; run with `osxphotos run photo_inspect.py`"""

from time import sleep

import bitmath
from photoscript import PhotosLibrary
from rich import print

from osxphotos import PhotoInfo, PhotosDB
from osxphotos.utils import dd_to_dms_str


def get_photo_type(photo: PhotoInfo):
    """Return a string describing the type of photo"""
    if photo.ismovie:
        photo_type = "video"
    else:
        raw = "RAW+JPEG " if photo.has_raw else "RAW " if photo.israw else ""
        photo_type = f"{raw}photo"
    if photo.burst:
        photo_type += " burst"
    if photo.live_photo:
        photo_type += " live"
    if photo.selfie:
        photo_type += " selfie"
    if photo.panorama:
        photo_type += " panorama"
    if photo.hdr:
        photo_type += " HDR"
    if photo.screenshot:
        photo_type += " screenshot"
    if photo.screen_recording:
        photo_type += " screen-recording"
    if photo.slow_mo:
        photo_type += " slow-mo"
    if photo.time_lapse:
        photo_type += " time-lapse"
    if photo.portrait:
        photo_type += " portrait"
    return photo_type


def inspect_photo(photo: PhotoInfo):
    """Print info about an osxphotos PhotoInfo object"""

    properties = [
        f"filename: {photo.original_filename}",
        f"type: {get_photo_type(photo)}",
        f"uuid: {photo.uuid}",
        f"date: {photo.date.isoformat()}",
        f"dimensions: {photo.height} x {photo.width}",
        f"file size: {bitmath.Byte(photo.original_filesize).to_MB()}",
        f"title: {photo.title or '-'}",
        f"description: {photo.description or '-'}",
        f"edited: {'✔' if photo.hasadjustments else '-'}",
        f"keywords: {', '.join(photo.keywords) or '-'}",
        f"persons: {', '.join(photo.persons) or '-'}",
        f"location: {', '.join(dd_to_dms_str(*photo.location)) if photo.location[0] else '-'}",
        f"place: {photo.place.name if photo.place else '-'}",
        f"categories: {', '.join(photo.labels) or '-'}",
        f"albums: {', '.join(photo.albums) or '-'}",
        f"favorite: {'♥' if photo.favorite else '-'}",
    ]
    if photo.exif_info:
        properties.extend(
            [
                f"camera: {photo.exif_info.camera_make or '-'} {photo.exif_info.camera_model or '-'}",
                f"lens: {photo.exif_info.lens_model or '-'}",
            ]
        )
    for property in properties:
        print(property)
    print("-" * 20)


if __name__ == "__main__":
    print("Loading Photos Library...")
    photosdb = PhotosDB()
    photoslib = PhotosLibrary()

    # keep track of last seen UUIDs so we don't print duplicates
    last_uuids = []
    print("Select one or more photos in Photos (press Ctrl+C to quit)")
    while True:
        if photos := photoslib.selection:
            uuids = sorted([photo.uuid for photo in photos])
            if uuids != last_uuids:
                for photo in photos:
                    photoinfo = photosdb.get_photo(photo.uuid)
                    inspect_photo(photoinfo)
                last_uuids = uuids
        sleep(0.200)
