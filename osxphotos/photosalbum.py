""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from typing import List, Optional

import photoscript
from more_itertools import chunked
from photoscript import Photo, PhotosLibrary

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


class PhotosAlbumPhotoScript:
    """Add photoscript.Photo objects to album"""

    def __init__(self, name: str, verbose: Optional[callable] = None):
        self.name = name
        self.verbose = verbose or noop
        self.library = PhotosLibrary()

        album = self.library.album(name)
        if album is None:
            self.verbose(f"Creating Photos album '{self.name}'")
            album = self.library.create_album(name)
        self.album = album

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
