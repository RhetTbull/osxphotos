"""Find manually added faces in Photos library and add them to an album."""

import click

from osxphotos import PhotosDB
from osxphotos._constants import _DB_TABLE_NAMES
from osxphotos.photosalbum import PhotosAlbum


def get_person_photos(person_info):
    """Workaround for bug #1489 in osxphotos, will be fixed in next release"""
    try:
        return person_info.photos
    except KeyError:
        return []


@click.command()
@click.option(
    "-u", "--unnamed", is_flag=True, help="Find only unnamed manually added faces"
)
@click.option(
    "-a", "--album", help="Add photos to this album; default = 'Manual Faces'"
)
def main(unnamed: bool, album: str):
    """Find photos with manually added faces and add them to an album in Photos."""
    photosdb = PhotosDB(verbose=print)
    photos = photosdb.photos()

    if unnamed:
        # Currently, osxphotos doesn't provide API access to manually added faces with no associated person
        # So need to query the database directly
        photos_version = photosdb.photos_version
        asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
        asset_fk = _DB_TABLE_NAMES[photos_version]["DETECTED_FACE_ASSET_FK"]
        results = photosdb.execute(
            f""" SELECT {asset_table}.ZUUID
                FROM {asset_table}
                INNER JOIN ZDETECTEDFACE
                ON {asset_table}.Z_PK = {asset_fk}
                WHERE ZDETECTEDFACE.ZMANUAL = 1 AND ZDETECTEDFACE.ZPERSON IS NULL;
            """
        )
        uuids = [r[0] for r in results]
        manual_faces = photosdb.photos(uuid=uuids)
        print(f"Found {len(manual_faces)} photos with unnamed manually added faces")
    else:
        manual_faces = [p for p in photos for f in p.face_info if f.manual]
        print(f"Found {len(manual_faces)} photos with manually added faces")

    if album is None:
        album = "Manual Faces"

    print(f"Adding photos to album '{album}'")
    album = PhotosAlbum(album)
    album.add_list(manual_faces)


if __name__ == "__main__":
    main()
