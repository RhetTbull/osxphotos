"""osxphotos script to find which albums and shared albums a photo is contained in

Run with: osxphotos run albums.py
"""

from __future__ import annotations

import osxphotos
from osxphotos._constants import _DB_TABLE_NAMES
from osxphotos.cli import echo, selection_command


def shared_originating_asset_identifier(
    db: osxphotos.PhotosDB,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Returns tuple of 2 dictionaries: asset_id: [uuid,...] and uuid: asset_id"""
    assets = {}
    uuids = {}
    photos_ver = db._photos_ver
    asset_table = _DB_TABLE_NAMES[photos_ver]["ASSET"]

    results = db.execute(
        f"""
        SELECT
        {asset_table}.ZUUID,
        ZADDITIONALASSETATTRIBUTES.ZORIGINATINGASSETIDENTIFIER
        FROM {asset_table}
        JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK;
        """
    ).fetchall()
    for uuid, assetid in results:
        if assetid in assets:
            assets[assetid].append(uuid)
        else:
            assets[assetid] = [uuid]
        uuids[uuid] = assetid
    return assets, uuids


def cloud_guid_photos(db: osxphotos.PhotosDB, guid: str) -> list[str]:
    """Return UUIDs of photos that have a cloud_guid matching guid"""
    return [p.uuid for p in db.photos() if p.cloud_guid == guid]


def print_results(albums: list[str], shared_albums: list[str]):
    """Print the results"""
    print("Albums:")
    if not albums:
        print("   None")
    for a in albums:
        print(f"   {a}")
    print("Shared Albums:")
    if not shared_albums:
        print("   None")
    for a in shared_albums:
        print(f"   {a}")


@selection_command
def albums(photos: list[osxphotos.PhotoInfo], **kwargs):
    """For the currently selected photo(s), list all albums and shared albums each photo is contained in."""

    echo(f"Found {len(photos)} selected photo(s)")

    echo("Scanning Photos database to match shared images to originals...")
    db = photos[0]._db
    assetids, uuids = shared_originating_asset_identifier(db)

    for photo in photos:
        echo(f"Checking photo {photo.original_filename} ({photo.uuid})")
        if not photo.cloud_guid and not photo.shared:
            echo("Photo does not have a cloud GUID, skipping (not a shared photo).")
            continue
        albums = []
        shared_albums = []
        assets = [photo.uuid]
        if photo.cloud_guid and photo.cloud_guid in assetids:
            # an original in the library (not a shared photo) has a cloud GUID
            # assets is list of all photo UUIDs with the given cloud_guid asset ID
            assets.extend(assetids[photo.cloud_guid])
        elif photo.shared:
            # the selected photos is a shared photo so it's in at least one album
            # need list of all UUIDs with given asset id as well as all photos with cloud_guid matching asset id
            if photo.uuid in uuids:
                asset = uuids[photo.uuid]
                assets.extend(assetids[asset])
            assets.extend(cloud_guid_photos(db, asset))
        for uuid in set(assets):
            p = db.get_photo(uuid)
            for a in p.album_info:
                if a.owner:  # shared albums have owners
                    shared_albums.append(a.title)
                else:
                    albums.append(a.title)
        print_results(albums, shared_albums)


if __name__ == "__main__":
    echo("Checking albums for selected photo(s)")
    albums()
