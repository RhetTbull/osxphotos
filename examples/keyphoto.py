"""Get Key photo for an album"""

import osxphotos


def key_asset_for_album(album: osxphotos.AlbumInfo) -> osxphotos.PhotoInfo:
    """Return key asset for a given album or None if it cannot be determined

    Args:
        album: AlbumInfo object

    Returns: PhotoInfo object for key asset

    Raises:
        ValueError if album cannot be found or key asset cannot be found
    """
    query = """
       SELECT ZASSET.ZUUID AS key_asset_uuid
       FROM ZGENERICALBUM
      JOIN ZASSET ON ZASSET.Z_PK = COALESCE(ZGENERICALBUM.ZCUSTOMKEYASSET, ZGENERICALBUM.ZKEYASSET)
      WHERE ZGENERICALBUM.ZUUID = ?;
      """
    results = album._db.execute(query, (album.uuid,)).fetchone()
    if not results:
        raise ValueError(f"Could not get album key asset for album: {album}")
    key_photo_uuid = results[0]
    if photo := photosdb.get_photo(key_photo_uuid):
        return photo
    raise ValueError(f"Could not get photo for UUID {key_photo_uuid}")


if __name__ == "__main__":
    photosdb = osxphotos.PhotosDB()
    for album in photosdb.album_info:
        try:
            key_asset = key_asset_for_album(album)
            print(f"{album.title}: {key_asset.original_filename}, {key_asset.uuid}")
        except ValueError:
            print(f"Could not get key asset for album {album.title}, {album.uuid}")
