"""Print path to each original photo in the library and whether it is referenced or not and if it is missing

Run with: osxphotos run photo_paths.py
"""

from __future__ import annotations

import osxphotos
from osxphotos.cli import query_command, verbose


@query_command
def photo_paths(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Print path to each original photo in the library and whether it is referenced or not and if it is missing.

    This may be useful for finding missing referenced photos.
    """
    print("uuid, original_filename, isreference, ismissing, path")
    for photo in photos:
        print(
            f"{photo.uuid}, {photo.original_filename}, "
            f"{'yes' if photo.isreference else 'no'}, "
            f"{'no' if photo.path else 'yes'}, "  # don't look at ismissing for referenced which may be false but at whether path exists
            f"{photo._path_5()}"  # this returns the candidate path for the photo wether or not it exists
        )


if __name__ == "__main__":
    photo_paths()
