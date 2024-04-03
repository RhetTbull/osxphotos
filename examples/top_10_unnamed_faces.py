"""Find top 10 unnamed faces in Photos library and add them to albums."""

from osxphotos import PhotosDB
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.photosalbum import PhotosAlbum


def get_person_photos(person_info):
    """Workaround for bug #1489 in osxphotos, will be fixed in next release"""
    try:
        return person_info.photos
    except KeyError:
        return []


def main():
    """Find top 10 unnamed faces in Photos library and add them to albums."""
    photosdb = PhotosDB(verbose=print)
    unnamed_persons = [p for p in photosdb.person_info if p.name == _UNKNOWN_PERSON]
    print(f"Found {len(unnamed_persons)} unnamed persons")

    top_10_unnamed = sorted(
        unnamed_persons, key=lambda x: len(get_person_photos(x)), reverse=True
    )[:10]

    for p in top_10_unnamed:
        photos = get_person_photos(p)
        album_name = f"Unnamed person: {p.uuid} ({len(photos)})"
        print(f"Creating album '{album_name}'")
        album = PhotosAlbum(album_name)
        album.add_list(photos)

if __name__ == "__main__":
    main()
