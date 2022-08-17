""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from typing import List, Optional

import photoscript
from more_itertools import chunked
from photoscript import Album, Folder, Photo, PhotosLibrary

from .photoinfo import PhotoInfo
from .utils import noop, pluralize

__all__ = ["PhotosAlbum", "PhotosAlbumPhotoScript"]


class PhotosAlbum:
    """Add osxphotos.photoinfo.PhotoInfo objects to album"""

    def __init__(self, name: str, verbose: Optional[callable] = None):
        self.name = name
        self.verbose = verbose or noop
        self.library = photoscript.PhotosLibrary()

        album = self.library.album(name)
        if album is None:
            self.verbose(f"Creating Photos album '{self.name}'")
            album = self.library.create_album(name)
        self.album = album

    def add(self, photo: PhotoInfo):
        photo_ = photoscript.Photo(photo.uuid)
        self.album.add([photo_])
        self.verbose(
            f"Added {photo.original_filename} ({photo.uuid}) to album {self.name}"
        )

    def add_list(self, photo_list: List[PhotoInfo]):
        photos = []
        for p in photo_list:
            try:
                photos.append(photoscript.Photo(p.uuid))
            except Exception as e:
                self.verbose(f"Error creating Photo object for photo {p.uuid}: {e}")
        for photolist in chunked(photos, 10):
            self.album.add(photolist)
        photo_len = len(photo_list)
        self.verbose(
            f"Added {photo_len} {pluralize(photo_len, 'photo', 'photos')} to album {self.name}"
        )

    def photos(self):
        return self.album.photos()


def folder_by_path(folders: List[str], verbose: Optional[callable] = None) -> Folder:
    """Get (and create if necessary) a Photos Folder by path (passed as list of folder names)"""
    library = PhotosLibrary()
    verbose = verbose or noop
    top_folder_name = folders.pop(0)
    top_folder = library.folder(top_folder_name, top_level=True)
    if not top_folder:
        verbose(f"Creating folder '{top_folder_name}'")
        top_folder = library.create_folder(top_folder_name)
    current_folder = top_folder
    for folder_name in folders:
        folder = current_folder.folder(folder_name)
        if not folder:
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
        album = folder.album(album_name)
        if not album:
            verbose(f"Creating album '{album_name}'")
            album = folder.create_album(album_name)
    else:
        # only have album name
        album_name = folders_album[0]
        album = library.album(album_name, top_level=True)
        if not album:
            verbose(f"Creating album '{album_name}'")
            album = library.create_album(album_name)

    return album


class PhotosAlbumPhotoScript:
    """Add photoscript.Photo objects to album"""

    def __init__(
        self, name: str, verbose: Optional[callable] = None, auto_folder: bool = False
    ):
        """Return a PhotosAlbumPhotoScript object, creating the album if necessary

        Args:
            name: Name of album
            verbose: optional callable to print verbose output
            auto_folder: if True, split album name on '/' to create folders if necessary,
                e.g. if name = 'folder1/folder2/album' then folders 'folder1' and 'folder2' will be created
                and album 'album' will be created in 'folder2';
                if False, album 'folder1/folder2/album' will be created
        """
        self.verbose = verbose or noop
        self.library = PhotosLibrary()

        folders_album = name.split("/") if auto_folder else [name]
        self.album = album_by_path(folders_album, verbose=verbose)
        self.name = name

    def add(self, photo: Photo):
        self.album.add([photo])
        self.verbose(f"Added {photo.filename} ({photo.uuid}) to album {self.name}")

    def add_list(self, photo_list: List[Photo]):
        for photolist in chunked(photo_list, 10):
            self.album.add(photolist)
        photo_len = len(photo_list)
        self.verbose(
            f"Added {photo_len} {pluralize(photo_len, 'photo', 'photos')} to album {self.name}"
        )

    def photos(self):
        return self.album.photos()
