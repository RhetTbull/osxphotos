"""Test PhotoInfoFromDict class"""

from __future__ import annotations

import pytest

from osxphotos.photoinfo_dict import PhotoInfoFromDict, photoinfo_from_dict
from osxphotos.photoinfo_protocol import PhotoInfoProtocol
from osxphotos.photosdb import PhotosDB

PHOTOSDB = "tests/Test-13.0.0.photoslibrary"


def test_rehydrate_dict():
    """Test rehydrating a dictionary"""
    photosdb = PhotosDB(dbfile=PHOTOSDB)
    photo = [p for p in photosdb.photos() if p.original_filename == "wedding.jpg"][0]
    photo_dict = photo.asdict()
    photo2 = photoinfo_from_dict(photo_dict)
    assert isinstance(photo2, PhotoInfoFromDict)
    assert photo.uuid == photo2.uuid
    photo2_dict = photo2.asdict()
    assert photo_dict == photo2_dict


def test_rehydrate_dict_methods(tmp_path):
    """Test rehydrating a dictionary with methods not implemented"""
    photosdb = PhotosDB(dbfile=PHOTOSDB)
    photo = [p for p in photosdb.photos() if p.original_filename == "wedding.jpg"][0]
    photo_dict = photo.asdict()
    photo2 = photoinfo_from_dict(photo_dict)
    with pytest.raises(NotImplementedError):
        photo2.export(tmp_path)
