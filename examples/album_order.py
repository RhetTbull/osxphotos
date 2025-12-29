"""Template function that returns the album or folder/album name with a sequence ID
(based on where the album is shown in the Photos library sidebar)

E.g.
01 Album1
02 Album2
03 Folder1
    01 SubFolder1
        01 AlbumInSubFolder1
        02 AlbumInSubFolder2
04 Album3

Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_order.py::album}"
or    osxphotos export /path/to/export --filename "{function:/path/to/album_order.py::folder_album}"

You may pass optional arguments to adjust the formatting in format:
    "{function:/path/to/album_order.py::album(spacer,format)}"
    where spacer = characters to put between the sequence ID and the album or folder name and format is an integer format code
    For example, "{function:/path/to/album_order.py::album( - ,03d)}"
    produces a value like "001 - Album Title"
    The default spacer is " - " and the default format is "d" (no leading zero or padding)
"""

import pathlib
from functools import cache
from typing import List, Optional, Union

from osxphotos import AlbumInfo, FolderInfo, PhotoInfo, PhotosDB
from osxphotos.phototemplate import RenderOptions


def _get_spacer_format(args: str | None):
    """Return spacer and format string from args"""
    spacer = " - "
    format = None
    if args:
        if "," in args:
            spacer, format = args.split(",")
        else:
            spacer = args
    format = "{0:" + format + "}" if format else "{0:d}"
    return spacer, format


def sorted_albums(photosdb: PhotosDB) -> list[AlbumInfo]:
    """Return all albums in database in sorted order"""

    @cache
    def _sorted_albums():
        return sorted(photosdb.album_info, key=lambda x: x.library_list_order)

    return _sorted_albums()


def get_top_level_items(photosdb: PhotosDB) -> tuple[list[FolderInfo], list[AlbumInfo]]:
    """Return all top-level folders and albums"""

    @cache
    def _get_top_level_items():
        all_folders = [f for f in photosdb.folder_info if f.parent is None]
        all_albums = [a for a in photosdb.album_info if a.parent is None]
        return all_folders, all_albums

    return _get_top_level_items()


def album(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Template function that returns the album name with a sequence ID
        (based on where the album is shown in the Photos library sidebar)

        E.g.
        01 Album1
        02 Album2
        03 Folder1
            01 SubFolder1
                01 AlbumInSubFolder1
                02 AlbumInSubFolder2
        04 Album3

        Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_ordder.py::album}"
        or    osxphotos export /path/to/export --filename "{function:/path/to/album_ordder.py::folder_album}"

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """
    all_albums = sorted_albums(photo._db)
    album_uuids = [a.uuid for a in photo.album_info]
    photo_albums = [
        (i + 1, album)
        for i, album in enumerate(all_albums)
        if album.uuid in album_uuids
    ]
    spacer, format = _get_spacer_format(args)
    return [f"{format.format(i)}{spacer}{album.title}" for i, album in photo_albums]


def folder_album(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Template function that returns the folder/album name with a sequence ID
        (based on where the album is shown in the Photos library sidebar)

        E.g.
        01 Album1
        02 Album2
        03 Folder1
            01 SubFolder1
                01 AlbumInSubFolder1
                02 AlbumInSubFolder2
        04 Album3

        Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_ordder.py::album}"
        or    osxphotos export /path/to/export --filename "{function:/path/to/album_ordder.py::folder_album}"

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """
    spacer, format = _get_spacer_format(args)

    # Get all albums the photo is in
    photo_albums = [album for album in photo.album_info]

    # Get top-level items once (cached)
    all_folders, all_albums = get_top_level_items(photo._db)

    results = []
    for album in photo_albums:
        # Build the folder path with sequence numbers
        path_parts = []

        # Process each folder in the hierarchy
        for folder in album.folder_list:
            # Get all siblings (both folders and albums with same parent)
            if folder.parent:
                # Folders and albums within a parent folder
                siblings = list(folder.parent.subfolders) + list(
                    folder.parent.album_info
                )
            else:
                # Top-level folders and albums
                siblings = all_folders + all_albums

            # Sort all siblings by library_list_order
            siblings = sorted(siblings, key=lambda x: x.library_list_order)

            # Find sequence number (1-based index)
            sequence = next(
                (i + 1 for i, item in enumerate(siblings) if item.uuid == folder.uuid),
                0,
            )
            path_parts.append(f"{format.format(sequence)}{spacer}{folder.title}")

        # Now handle the album itself - find its sequence among siblings (folders + albums)
        if album.parent:
            # Album is in a folder - get sibling folders and albums in that folder
            siblings = list(album.parent.subfolders) + list(album.parent.album_info)
        else:
            # Top-level album - get all top-level folders and albums
            siblings = all_folders + all_albums

        # Sort all siblings by library_list_order
        siblings = sorted(siblings, key=lambda x: x.library_list_order)

        # Find sequence number for the album
        album_sequence = next(
            (i + 1 for i, item in enumerate(siblings) if item.uuid == album.uuid), 0
        )
        album_part = f"{format.format(album_sequence)}{spacer}{album.title}"

        # Combine folder path and album
        if path_parts:
            full_path = "/".join(path_parts) + "/" + album_part
        else:
            full_path = album_part

        results.append(full_path)

    return results
