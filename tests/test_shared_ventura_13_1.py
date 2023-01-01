"""Test shared iCloud photos on macOS 13.1"""
import pytest

import osxphotos

PHOTOS_DB = "./tests/Test-Cloud-13.1.photoslibrary//database/photos.db"


def test_query_shared_path():
    """Test shared path is not None for shared photos"""
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for p in photosdb.photos():
        if not p.shared or p.ismissing:
            continue
        assert p.path
        assert p.path_derivatives
