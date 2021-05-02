""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from typing import Optional
import photoscript
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

    def photos(self):
        return self.album.photos()


# def add_photo_to_album(photo, album_pairs, results):
#     # todo: class PhotoAlbum
#     # keeps a name, maintains state
#     """ add photo to album(s) as defined in album_pairs

#     Args:
#         photo: PhotoInfo object
#         album_pairs: list of tuples with [(album name, results_list)]
#         results: ExportResults object

#     Returns:
#         updated ExportResults object
#     """
#     for album, result_list in album_pairs:
#         try:
#                 if album_export is None:
#                     # first time fetching the album, see if it exists already
#                     album_export = photos_library.album(
#                         add_exported_to_album
#                     )
#                     if album_export is None:
#                         # album doesn't exist, so create it
#                         verbose_(
#                             f"Creating Photos album '{add_exported_to_album}'"
#                         )
#                         album_export = photos_library.create_album(
#                             add_exported_to_album
#                         )
#                 exported_photo = photoscript.Photo(p.uuid)
#                 album_export.add([exported_photo])
#                 verbose_(
#                     f"Added {p.original_filename} ({p.uuid}) to album {add_exported_to_album}"
#                 )
#                 exported_album = [
#                     (filename, add_exported_to_album)
#                     for filename in export_results.exported
#                 ]
#                 export_results.exported_album = exported_album
#             if
#         except Exception as e:
#             click.echo(
#                 f"Error adding photo {p.original_filename} ({p.uuid}) to album {add_exported_to_album}"
#             )
