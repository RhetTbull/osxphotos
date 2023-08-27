"""Test ExifWriter class"""


import os
import pathlib
import subprocess

import pytest

from osxphotos import PhotoInfo, PhotosDB
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.exifwriter import ExifOptions, ExifWriter

PHOTOS_DB = "tests/Test-13.0.0.photoslibrary"

# Pumkins1 has all metadata fields
UUID_ALL_METADATA = "F12384F6-CD17-4151-ACBA-AE0E3688539E"

UUID_FAVORITE = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
UUID_NOT_FAVORITE = "F12384F6-CD17-4151-ACBA-AE0E3688539E"  # pumpkins1.jpg

# options: all keywords location faces date title description favorite

METADATA_FIELDS = {
    "description": {
        "property": "description",
        "fields": ["EXIF:ImageDescription", "XMP:Description", "IPTC:Caption-Abstract"],
        "list": False,
    },
    "title": {
        "property": "title",
        "fields": ["XMP:Title", "IPTC:ObjectName"],
        "list": False,
    },
    "keywords": {
        "property": "keywords",
        "fields": ["IPTC:Keywords", "XMP:Subject", "XMP:TagsList"],
        "list": True,
    },
    "persons": {"property": "persons", "fields": ["XMP:PersonInImage"], "list": True},
}

try:
    exiftool = get_exiftool_path()
except Exception:
    exiftool = None

if exiftool is None:
    pytest.skip("could not find exiftool in path", allow_module_level=True)


@pytest.fixture(scope="module")
def photosdb():
    return PhotosDB(dbfile=os.path.join(os.getcwd(), PHOTOS_DB))


def export_and_wipe_metadata(photo: PhotoInfo, tmpdir: pathlib.Path) -> str:
    """Export a photo to a temp directory and wipe all metadata"""
    exported = photo.export(tmpdir)[0]
    # run exiftool on exported to erase all metadata
    cmd = [exiftool, "-overwrite_original", "-all=", exported]
    subprocess.run(cmd, check=True)
    return exported


@pytest.mark.parametrize("field", METADATA_FIELDS.keys())
def test_exifwriter_single(photosdb: PhotosDB, tmp_path: pathlib.Path, field: str):
    """Test ExifWriter with single metadata field"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(
        description=False,
        keywords=False,
        persons=False,
        title=False,
        favorite_rating=False,
        face_regions=False,
        location=False,
        datetime=False,
    )
    setattr(exif_options, field, True)
    exif_writer = ExifWriter(photo)
    warning, error = exif_writer.write_exif_data(exported, exif_options)
    assert not warning
    assert not error

    exif_data = ExifTool(exported).asdict()
    # sourcery skip: no-loop-in-tests
    for exif_field in METADATA_FIELDS[field]["fields"]:
        assert exif_field in exif_data
        got = exif_data[exif_field]
        # sourcery skip: no-conditionals-in-tests
        if METADATA_FIELDS[field]["list"] and not isinstance(got, list):
            got = sorted([got])
        expected = getattr(photo, METADATA_FIELDS[field]["property"])
        # sourcery skip: no-conditionals-in-tests
        if isinstance(expected, list):
            expected = sorted(expected)
        assert got == expected

    # sourcery skip: no-loop-in-tests
    for exif_field in METADATA_FIELDS.keys():
        # sourcery skip: no-conditionals-in-tests
        if exif_field == field:
            continue
        for exif_field in METADATA_FIELDS[exif_field]["fields"]:
            assert exif_field not in exif_data


def test_exifwriter_favorite(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with favorite_rating metadata field"""
    photo = photosdb.get_photo(UUID_FAVORITE)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(
        description=False,
        keywords=False,
        persons=False,
        title=False,
        favorite_rating=True,
        face_regions=False,
        location=False,
        datetime=False,
    )

    exif_writer = ExifWriter(photo)
    warning, error = exif_writer.write_exif_data(exported, exif_options)
    assert not warning
    assert not error

    exif_data = ExifTool(exported).asdict()
    assert "XMP:Rating" in exif_data
    assert exif_data["XMP:Rating"] == 5
    assert "IPTC:Keywords" not in exif_data

    photo = photosdb.get_photo(UUID_NOT_FAVORITE)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(
        description=False,
        keywords=False,
        persons=False,
        title=False,
        favorite_rating=True,
        face_regions=False,
        location=False,
        datetime=False,
    )

    exif_writer = ExifWriter(photo)
    warning, error = exif_writer.write_exif_data(exported, exif_options)
    assert not warning
    assert not error

    exif_data = ExifTool(exported).asdict()
    assert "XMP:Rating" in exif_data
    assert exif_data["XMP:Rating"] == 0
    assert "IPTC:Keywords" not in exif_data


def test_exifwriter_all(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with all metadata fields"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(favorite_rating=True)

    exif_writer = ExifWriter(photo)
    warning, error = exif_writer.write_exif_data(exported, exif_options)
    assert not warning
    assert not error

    exif_data = ExifTool(exported).asdict()
    # sourcery skip: no-loop-in-tests
    for field in METADATA_FIELDS.keys():
        for exif_field in METADATA_FIELDS[field]["fields"]:
            assert exif_field in exif_data
            got = exif_data[exif_field]
            # sourcery skip: no-conditionals-in-tests
            if METADATA_FIELDS[field]["list"] and not isinstance(got, list):
                got = sorted([got])
            expected = getattr(photo, METADATA_FIELDS[field]["property"])
            # sourcery skip: no-conditionals-in-tests
            if isinstance(expected, list):
                expected = sorted(expected)
            assert got == expected

    assert "XMP:Rating" in exif_data
    # sourcery skip: no-conditionals-in-tests
    if photo.favorite:
        assert exif_data["XMP:Rating"] == 5
    else:
        assert exif_data["XMP:Rating"] == 0