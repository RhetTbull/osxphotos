""" Example showing how to use a custom function for osxphotos {function} template
    Returns expected path for a missing photos
    Use:  osxphotos query --missing --field original_path "{function:photopath.py::original}"
    or for edited photos:  osxphotos query --missing --field edited_path "{function:photopath.py::edited}"
"""

from __future__ import annotations

import os
from typing import List, Optional, Union

from osxphotos import ExportOptions, PhotoInfo
from osxphotos._constants import _MOVIE_TYPE, _PHOTO_TYPE, _PHOTOS_5_SHARED_PHOTO_PATH


def original(
    photo: PhotoInfo, options: ExportOptions, args: Optional[str] = None, **kwargs
) -> Union[list[str], str]:
    """returns expected path for original photo or None if path cannot be determined

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.ExportOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    if photo._info["shared"]:
        # shared photo
        return os.path.join(
            photo._db._library_path,
            _PHOTOS_5_SHARED_PHOTO_PATH,
            photo._info["directory"],
            photo._info["filename"],
        )
    elif photo._info["directory"].startswith("/"):
        # referenced photo
        return os.path.join(photo._info["directory"], photo._info["filename"])
    else:
        # regular photo
        return os.path.join(
            photo._db._masters_path,
            photo._info["directory"],
            photo._info["filename"],
        )


def edited(
    photo: PhotoInfo, options: ExportOptions, args: Optional[str] = None, **kwargs
) -> Union[list[str], str]:
    """returns expected path for edited photo or None if path cannot be determined

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.ExportOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    if not photo._info["hasAdjustments"]:
        return []

    library = photo._db._library_path
    directory = photo._uuid[0]  # first char of uuid
    filename = None
    if photo._info["type"] == _PHOTO_TYPE:
        # it's a photo
        if photo._db._photos_ver != 5 and photo.uti == "public.heic":
            filename = f"{photo._uuid}_1_201_a.heic"
        else:
            filename = f"{photo._uuid}_1_201_a.jpeg"
    elif photo._info["type"] == _MOVIE_TYPE:
        # it's a movie
        filename = f"{photo._uuid}_2_0_a.mov"
    else:
        return []

    return os.path.join(library, "resources", "renders", directory, filename)
