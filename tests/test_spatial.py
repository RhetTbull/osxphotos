"""Test PhotoInfo.spatial property and --spatial/--not-spatial query options"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos.cli import cli_main

# Test-Media-Types-15.7.2 contains a single spatial photo (IMG_4076.HEIC);
# no other asset in the library is spatial
SPATIAL_PHOTOS_DB = "tests/Test-Media-Types-15.7.2.photoslibrary"
SPATIAL_UUID = "CDFC3B62-EDFD-4A49-A80F-00BB7822D0E8"
SPATIAL_TYPE = 1

# Test-13.0.0 predates the ZASSET.ZSPATIALTYPE column
NO_SPATIAL_COLUMN_DB = "tests/Test-13.0.0.photoslibrary"


def test_spatial_property():
    """Test that the spatial photo reports its spatial type and others report 0"""
    photosdb = osxphotos.PhotosDB(dbfile=SPATIAL_PHOTOS_DB)
    spatial = photosdb.get_photo(SPATIAL_UUID)
    assert spatial.spatial == SPATIAL_TYPE
    assert isinstance(spatial.spatial, int)

    # only one photo in the library is spatial
    spatial_photos = [p for p in photosdb.photos() if p.spatial]
    assert len(spatial_photos) == 1
    assert spatial_photos[0].uuid == SPATIAL_UUID


def test_spatial_property_non_spatial():
    """Test that non-spatial photos report spatial == 0"""
    photosdb = osxphotos.PhotosDB(dbfile=SPATIAL_PHOTOS_DB)
    for photo in photosdb.photos():
        if photo.uuid == SPATIAL_UUID:
            continue
        assert photo.spatial == 0


def test_spatial_property_no_column():
    """Test that libraries without ZSPATIALTYPE report spatial == 0 for all photos"""
    photosdb = osxphotos.PhotosDB(dbfile=NO_SPATIAL_COLUMN_DB)
    assert all(p.spatial == 0 for p in photosdb.photos())


def test_spatial_asdict_json():
    """Test that spatial is included in asdict() and json() as a non-shallow property"""
    photosdb = osxphotos.PhotosDB(dbfile=SPATIAL_PHOTOS_DB)
    spatial = photosdb.get_photo(SPATIAL_UUID)

    # non-shallow representation contains spatial
    asdict_data = spatial.asdict(shallow=False)
    assert asdict_data["spatial"] == SPATIAL_TYPE

    json_data = json.loads(spatial.json(shallow=False))
    assert json_data["spatial"] == SPATIAL_TYPE

    # shallow representation does not contain spatial
    assert "spatial" not in spatial.asdict(shallow=True)


def test_query_spatial():
    """Test osxphotos query --spatial"""
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["query", "--db", SPATIAL_PHOTOS_DB, "--spatial", "--count"],
    )
    assert result.exit_code == 0
    assert result.output.strip().splitlines()[-1] == "1"


def test_query_not_spatial():
    """Test osxphotos query --not-spatial"""
    photosdb = osxphotos.PhotosDB(dbfile=SPATIAL_PHOTOS_DB)
    expected = len([p for p in photosdb.photos() if not p.spatial])

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["query", "--db", SPATIAL_PHOTOS_DB, "--not-spatial", "--count"],
    )
    assert result.exit_code == 0
    assert result.output.strip().splitlines()[-1] == str(expected)


def test_query_spatial_not_spatial_mutually_exclusive():
    """Test that --spatial and --not-spatial are mutually exclusive"""
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "query",
            "--db",
            SPATIAL_PHOTOS_DB,
            "--spatial",
            "--not-spatial",
            "--count",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output
