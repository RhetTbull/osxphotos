""" query function to be used with osxphotos query --query-function to find photos with identified face circles that are unnamed.

See: https://www.reddit.com/r/osxphotos/comments/16o3wbs/finding_unnamed_faces_more_than_apple_photos_shows/

Run with `osxphotos query --query-function find_unnamed_faces.py::unnamed_faces --add-to-album "Unnamed Faces" --quiet`
"""

from __future__ import annotations

from osxphotos import PhotoInfo


# call this with --query-function examples/query_function.py::best_selfies
def unnamed_faces(photos: list[PhotoInfo]) -> list[PhotoInfo]:
    """your query function should take a list of PhotoInfo objects and return a list of PhotoInfo objects (or empty list)"""

    # filter out photos with no face info
    photos = [p for p in photos if p.face_info]
    if not photos:
        return []

    # find identified face circles with no name
    face_photos = []
    for photo in photos:
        for face in photo.face_info:
            if face.quality > -1.0 and not face.name:
                face_photos.append(photo)
                break
    return face_photos
