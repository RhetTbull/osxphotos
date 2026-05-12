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


def test_photoinfo_asdict_cache_returns_independent_copy():
    """Mutating PhotoInfo.asdict() result should not mutate the cached value."""
    photosdb = PhotosDB(dbfile=PHOTOSDB)
    photo = [p for p in photosdb.photos() if p.original_filename == "wedding.jpg"][0]

    photo_dict = photo.asdict()
    photo_dict["uuid"] = "mutated"
    photo_dict["keywords"] = ["mutated"]

    cached_dict = photo.asdict()

    assert cached_dict["uuid"] == photo.uuid
    assert cached_dict["keywords"] == photo.keywords


def test_photoinfo_asdict_cache_same_instance(monkeypatch: pytest.MonkeyPatch):
    """Repeated asdict calls on same PhotoInfo instance should use cached data."""
    photosdb = PhotosDB(dbfile=PHOTOSDB)
    photo = [p for p in photosdb.photos() if p.original_filename == "wedding.jpg"][0]
    expected = photo.asdict()

    def unexpected_uncached_asdict(*args, **kwargs):
        raise AssertionError("asdict should have been read from cache")

    monkeypatch.setattr(photo, "_asdict_uncached", unexpected_uncached_asdict)

    assert photo.asdict() == expected


def test_photoinfo_json_cache_same_instance(monkeypatch: pytest.MonkeyPatch):
    """Repeated json calls on same PhotoInfo instance should use cached data."""
    photosdb = PhotosDB(dbfile=PHOTOSDB)
    photo = [p for p in photosdb.photos() if p.original_filename == "wedding.jpg"][0]
    expected = photo.json(indent=2, shallow=False)

    def unexpected_asdict(*args, **kwargs):
        raise AssertionError("json should have been read from cache")

    monkeypatch.setattr(photo, "asdict", unexpected_asdict)

    assert photo.json(indent=2, shallow=False) == expected
