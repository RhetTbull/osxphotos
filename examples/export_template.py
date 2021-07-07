""" Example showing how to use a custom function for osxphotos {function} template 
    to export photos in a folder structure similar to Photos' own structure

    Use:  osxphotos export /path/to/export --directory "{function:/path/to/export_template.py::photos_folders}"

    This will likely export multiple copies of each photo.  If using APFS file system, this should be
    a non-issue as osxphotos will use copy-on-write so each exported photo doesn't take up additional space
    unless you edit the photo.

    Thank-you @mkirkland4874 for the inspiration for this example!

    This will produce output similar to this:

Library
- Photos
-- {created.year}
---- {created.mm}
------ {created.dd}
- Favorites
- Hidden
- Recently Deleted
- People
- Places
- Imports
Media Types
- Videos
- Selfies
- Portrait
- Panoramas
- Time-lapse
- Slow-mo
- Bursts
- Screenshots
My Albums
-- Album 1
-- Album 2
-- Folder 1
---- Album 3
Shared Albums
-- Shared Album 1
-- Shared Album 2
"""

from typing import List, Union

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.datetime_formatter import DateTimeFormatter
from osxphotos.path_utils import sanitize_dirname
from osxphotos.phototemplate import RenderOptions


def place_folder(photo: osxphotos.PhotoInfo) -> str:
    """Return places as folder in format Country/State/City/etc."""
    if not photo.place:
        return ""

    places = []
    if photo.place.names.country:
        places.append(photo.place.names.country[0])

    if photo.place.names.state_province:
        places.append(photo.place.names.state_province[0])

    if photo.place.names.sub_administrative_area:
        places.append(photo.place.names.sub_administrative_area[0])

    if photo.place.names.additional_city_info:
        places.append(photo.place.names.additional_city_info[0])

    if photo.place.names.area_of_interest:
        places.append(photo.place.names.area_of_interest[0])

    if places:
        return "Library/Places/" + "/".join(sanitize_dirname(place) for place in places)
    else:
        return ""


def photos_folders(photo: osxphotos.PhotoInfo, **kwargs) -> Union[List, str]:
    """template function for use with --directory to export photos in a folder structure similar to Photos

    Args:
        photo: osxphotos.PhotoInfo object
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns: list of directories for each photo

    """

    rendered_date, _ = photo.render_template("{created.year}/{created.mm}/{created.dd}")
    date_path = rendered_date[0]

    def add_date_path(path):
        """add date path (year/mm/dd)"""
        return f"{path}/{date_path}"

    # Library

    directories = []
    if not photo.hidden and not photo.intrash and not photo.shared:
        # set directories to [Library/Photos/year/mm/dd]
        # render_template returns a tuple of [rendered value(s)], [unmatched]
        # here, we can ignore the unmatched value, assigned to _, as we know template will match
        directories, _ = photo.render_template(
            "Library/Photos/{created.year}/{created.mm}/{created.dd}"
        )

    if photo.favorite:
        directories.append(add_date_path("Library/Favorites"))
    if photo.hidden:
        directories.append(add_date_path("Library/Hidden"))
    if photo.intrash:
        directories.append(add_date_path("Library/Recently Deleted"))

    directories.extend(
        [
            add_date_path(f"Library/People/{person}")
            for person in photo.persons
            if person != _UNKNOWN_PERSON
        ]
    )

    if photo.place:
        directories.append(add_date_path(place_folder(photo)))

    if photo.import_info:
        dt = DateTimeFormatter(photo.import_info.creation_date)
        directories.append(f"Library/Imports/{dt.year}/{dt.mm}/{dt.dd}")

    # Media Types

    if photo.ismovie:
        directories.append(add_date_path("Media Types/Videos"))
    if photo.selfie:
        directories.append(add_date_path("Media Types/Selfies"))
    if photo.live_photo:
        directories.append(add_date_path("Media Types/Live Photos"))
    if photo.portrait:
        directories.append(add_date_path("Media Types/Portrait"))
    if photo.panorama:
        directories.append(add_date_path("Media Types/Panoramas"))
    if photo.time_lapse:
        directories.append(add_date_path("Media Types/Time-lapse"))
    if photo.slow_mo:
        directories.append(add_date_path("Media Types/Slo-mo"))
    if photo.burst:
        directories.append(add_date_path("Media Types/Bursts"))
    if photo.screenshot:
        directories.append(add_date_path("Media Types/Screenshots"))

    # Albums

    # render the folders and albums in folder/subfolder/album format
    # the __NO_ALBUM__ is used as a sentinel to strip out photos not in an album
    # use RenderOptions.dirname to force the rendered folder_album value to be sanitized as a valid path
    # use RenderOptions.none_str to specify custom value for any photo that doesn't belong to an album so
    # those can be filtered out; if not specified, none_str is "_"
    folder_albums, _ = photo.render_template(
        "{folder_album}", RenderOptions(dirname=True, none_str="__NO_ALBUM__")
    )

    root_directory = "Shared Albums/" if photo.shared else "My Albums/"
    directories.extend(
        [
            root_directory + folder_album
            for folder_album in folder_albums
            if folder_album != "__NO_ALBUM__"
        ]
    )

    return directories
