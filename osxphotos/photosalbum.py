""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from typing import List, Optional

import photoscript
from more_itertools import chunked

from .photoinfo import PhotoInfo
from .utils import noop


class PhotosAlbum:
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
        photos = [photoscript.Photo(p.uuid) for p in photo_list]
        for photolist in chunked(photos, 10):
            self.album.add(photolist)
        photo_len = len(photos)
        photo_word = "photos" if photo_len > 1 else "photo"
        self.verbose(f"Added {photo_len} {photo_word} to album {self.name}")

    def photos(self):
        return self.album.photos()
