"""Example that shows how to add PhotoInfo objects to an album in Photos"""

from osxphotos import PhotosDB
from osxphotos.photosalbum import PhotosAlbum

# If album exists it will be used, otherwise it will be created
album = PhotosAlbum("Best Photos")
best_photos = [p for p in PhotosDB(verbose=print).photos() if p.score.overall > 0.9]

# use album.add() or album.append() to add a single photo
# use album.update() or album.extend() to add an iterable of photos
album.extend(best_photos)
print(f"Added {len(best_photos)} photos to album {album.name}")
print(f"Album contains {len(album.photos())} photos")
