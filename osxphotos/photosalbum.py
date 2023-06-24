""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from __future__ import annotations

import unicodedata
from typing import List, Optional

from more_itertools import chunked

from .photoinfo import PhotoInfo
from .platform import assert_macos
from .utils import noop, pluralize

assert_macos()

import photoscript
from photoscript import Album, Folder, Photo, PhotosLibrary

__all__ = ["PhotosAlbum", "PhotosAlbumPhotoScript"]


def get_unicode_variants(s: str) -> list[str]:
    """Get all unicode variants of string"""
    variants = []
    for form in ["NFC", "NFD", "NFKC", "NFKD"]:
        normalized = unicodedata.normalize(form, s)
        variants.append(normalized)
    return variants


def folder_by_path(folders: List[str], verbose: Optional[callable] = None) -> Folder:
    """Get (and create if necessary) a Photos Folder by path (passed as list of folder names)"""
    library = PhotosLibrary()
    verbose = verbose or noop
    top_folder_name = folders.pop(0)

    for folder_variant in get_unicode_variants(top_folder_name):
        top_folder = library.folder(folder_variant, top_level=True)
        if top_folder is not None:
            break
    else:
        verbose(f"Creating folder '{top_folder_name}'")
        top_folder = library.create_folder(top_folder_name)

    current_folder = top_folder
    for folder_name in folders:
        for folder_variant in get_unicode_variants(folder_name):
            folder = current_folder.folder(folder_variant)
            if folder is not None:
                break
        else:
            verbose(f"Creating folder '{folder_name}'")
            folder = current_folder.create_folder(folder_name)
        current_folder = folder
    return current_folder


def album_by_path(
    folders_album: List[str], verbose: Optional[callable] = None
) -> Album:
    """Get (and create if necessary) a Photos Album by path (pass as list of folders, album name)"""
    library = PhotosLibrary()
    verbose = verbose or noop
    if len(folders_album) > 1:
        # have folders
        album_name = folders_album.pop()
        folder = folder_by_path(folders_album, verbose)
        for album_variant in get_unicode_variants(album_name):
            # Get album if it exists
            # need to check every unicode variant to avoid creating duplicate albums with same visual representation (#1085)
            album = folder.album(album_variant)
            if album is not None:
                break
        else:
            verbose(f"Creating album '{album_name}'")
            album = folder.create_album(album_name)
    else:
        # only have album name
        album_name = folders_album[0]
        for album_variant in get_unicode_variants(album_name):
            album = library.album(album_variant, top_level=True)
            if album is not None:
                break
        else:
            # album doesn't exist, create it
            verbose(f"Creating album '{album_name}'")
            album = library.create_album(album_name)

    return album


class PhotosAlbum:
    """Add osxphotos.photoinfo.PhotoInfo objects to album"""

    def __init__(
        self,
        name: str,
        verbose: Optional[callable] = None,
        split_folder: Optional[str] = None,
        rich: bool = False,
    ):
        """Return a PhotosAlbum object, creating the album if necessary

        Args:
            name: Name of album
            verbose: optional callable to print verbose output
            split_folder: if set, split album name on value of split_folder to create folders if necessary,
                e.g. if name = 'folder1/folder2/album' and split_folder='/',
                then folders 'folder1' and 'folder2' will be created and album 'album' will be created in 'folder2';
                if not set, album 'folder1/folder2/album' will be created
            rich: if True, use rich themes for verbose output
        """
        self.verbose = verbose or noop
        self.library = photoscript.PhotosLibrary()

        folders_album = name.split(split_folder) if split_folder else [name]
        self.album = album_by_path(folders_album, verbose=verbose)
        self.name = name
        self.rich = rich

    def add(self, photo: PhotoInfo):
        photo_ = photoscript.Photo(photo.uuid)
        self.album.add([photo_])
        self.verbose(
            f"Added {self._format_name(photo.original_filename)} ({self._format_uuid(photo.uuid)}) to album {self._format_album(self.name)}"
        )

    def add_list(self, photo_list: List[PhotoInfo]):
        photos = []
        for p in photo_list:
            try:
                photos.append(photoscript.Photo(p.uuid))
            except Exception as e:
                self.verbose(
                    f"Error creating Photo object for photo {self._format_uuid(p.uuid)}: {e}"
                )
        for photolist in chunked(photos, 10):
            self.album.add(photolist)
        photo_len = len(photo_list)
        self.verbose(
            f"Added {self._format_num(photo_len)} {pluralize(photo_len, 'photo', 'photos')} to album {self._format_album(self.name)}"
        )

    def photos(self):
        return self.album.photos()

    def _format_uuid(self, uuid: str) -> str:
        """ "Format uuid for verbose output"""
        return f"[uuid]{uuid}[/uuid]" if self.rich else uuid

    def _format_album(self, album: str) -> str:
        """ "Format album name for verbose output"""
        return f"[filepath]{album}[/filepath]" if self.rich else album

    def _format_name(self, name: str) -> str:
        """ "Format name for verbose output"""
        return f"[filename]{name}[/filename]" if self.rich else name

    def _format_num(self, num: int) -> str:
        """ "Format number for verbose output"""
        return f"[num]{num}[/num]" if self.rich else str(num)


class PhotosAlbumPhotoScript(PhotosAlbum):
    """Add photoscript.Photo objects to album"""

    def add(self, photo: Photo):
        self.album.add([photo])
        self.verbose(
            f"Added {self._format_name(photo.filename)} ({self._format_uuid(photo.uuid)}) to album {self._format_album(self.name)}"
        )

    def add_list(self, photo_list: List[Photo]):
        for photolist in chunked(photo_list, 10):
            self.album.add(photolist)
        photo_len = len(photo_list)
        self.verbose(
            f"Added {self._format_num(photo_len)} {pluralize(photo_len, 'photo', 'photos')} to album {self._format_album(self.name)}"
        )
