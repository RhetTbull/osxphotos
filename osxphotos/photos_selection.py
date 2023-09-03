"""PhotosSelection class for accessing currently selected photos in the Photos.app (macOS only)"""

from __future__ import annotations

from osxphotos.platform import assert_macos, is_macos

if not is_macos:
    raise ImportError("PhotosSelection only supported on macOS")

import re

import photoscript
from applescript import ScriptError

from osxphotos import PhotoInfo, PhotosDB


class PhotosSelection:
    """Class which provides indexed access to currently selected photos in Photos.app

    Init:
        photosdb: PhotosDB object

    Examples:
        ```python
            selection = PhotosSelection(photosdb)

            # get first selected photo:
            photo = selection[0]

            # get count of selected photos
            count = len(selection)

            # the returned object is a PhotoInfo object
        ```
    """

    def __init__(self, photosdb: PhotosDB):
        """Create a new PhotosSelection object

        Args:
            photosdb: a PhotosDB object
        """
        self._photosdb = photosdb

    def _get_selection(self) -> list[PhotoInfo]:
        """Return list of selected photos"""
        return get_selected(self._photosdb)

    def __getitem__(self, index) -> PhotoInfo:
        """Return PhotoInfo object for selected photo at index"""
        return self._get_selection()[index]

    def __iter__(self) -> iter:
        """Iterate over selected photos"""
        return iter(self._get_selection())

    def __contains__(self, item) -> bool:
        """Return True if item is in selection, else False"""
        return item in self._get_selection()

    def __repr__(self) -> str:
        """Return string representation"""
        return f"PhotosSelection({self._photosdb})"

    def __str__(self) -> str:
        """Return string representation"""
        return f"PhotosSelection({self._photosdb})"

    def __len__(self) -> int:
        """Return number of selected photos"""
        return len(self._get_selection())


def get_selected(photosdb: PhotosDB):
    assert_macos()
    try:
        selected = photoscript.PhotosLibrary().selection
    except ScriptError as e:
        # some photos (e.g. shared items) can't be selected and raise ScriptError:
        # applescript.ScriptError: Photos got an error: Can’t get media item id "34C26DFA-0CEA-4DB7-8FDA-B87789B3209D/L0/001". (-1728) app='Photos' range=16820-16873
        # In this case, we can parse the UUID from the error (though this only works for a single selected item)
        if match := re.match(r".*Can’t get media item id \"(.*)\".*", str(e)):
            uuid = match[1].split("/")[0]
            return photosdb.photos(uuid=[uuid])
    return photosdb.photos(uuid=[p.uuid for p in selected]) if selected else []
