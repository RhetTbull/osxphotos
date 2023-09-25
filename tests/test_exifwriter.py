"""Test ExifWriter class"""


import json
import os
import pathlib
import subprocess

import pytest

from osxphotos import PhotoInfo, PhotosDB
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.exifwriter import ExifOptions, ExifWriter
from osxphotos.phototemplate import RenderOptions

PHOTOS_DB = "tests/Test-13.0.0.photoslibrary"

# Pumkins1 has (almost) all metadata fields
UUID_ALL_METADATA = "F12384F6-CD17-4151-ACBA-AE0E3688539E"  # Pumkins1.jpg
UUID_FAVORITE = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
UUID_NOT_FAVORITE = "F12384F6-CD17-4151-ACBA-AE0E3688539E"  # pumpkins1.jpg
UUID_LOCATION = "DC99FBDD-7A52-4100-A5BB-344131646C30"  # St James Park.jpg
UUID_MERGE_KEYWORDS = "1EB2B765-0765-43BA-A90C-0D0580E6172C"  # Pumpkins3.jpg

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


def test_exifwriter_description_template(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with description_template"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)

    exif_options = ExifOptions(description_template="Hello {descr}")
    exif_writer = ExifWriter(photo)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:ImageDescription" in exif_data
    assert exif_data["EXIF:ImageDescription"] == f"Hello {photo.description}"


def test_exifwriter_description_template_strip(
    photosdb: PhotosDB, tmp_path: pathlib.Path
):
    """Test ExifWriter with description_template with strip"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)

    # first test without strip
    exif_options = ExifOptions(description_template="Hello  ")
    exif_writer = ExifWriter(photo)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:ImageDescription" in exif_data
    assert exif_data["EXIF:ImageDescription"] == "Hello  "

    # next, test with strip=True
    exif_options = ExifOptions(description_template="Hello  ", strip=True)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert exif_data["EXIF:ImageDescription"] == "Hello"


def test_exifwriter_keyword_template(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with keyword_template"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(keyword_template=["Hello"])

    exif_writer = ExifWriter(photo)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "IPTC:Keywords" in exif_data
    assert sorted(exif_data["IPTC:Keywords"]) == sorted(photo.keywords + ["Hello"])

    # test with replace_keywords
    exif_writer.write_exif_data(
        exported, ExifOptions(keyword_template=["Hello"], replace_keywords=True)
    )
    exif_data = ExifTool(exported).asdict()
    got = exif_data["IPTC:Keywords"]
    got = got if isinstance(got, list) else [got]
    assert got == ["Hello"]


def test_exifwriter_keyword_persons_albums(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with use_albums_as_keywords and use_persons_as_keywords"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)
    exif_options = ExifOptions(
        use_persons_as_keywords=True, use_albums_as_keywords=True
    )

    exif_writer = ExifWriter(photo)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "IPTC:Keywords" in exif_data
    assert sorted(exif_data["IPTC:Keywords"]) == sorted(
        photo.keywords + photo.persons + photo.albums
    )


def test_exifwriter_location(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with location"""
    photo = photosdb.get_photo(UUID_LOCATION)
    exported = export_and_wipe_metadata(photo, tmp_path)

    # location = False
    exif_writer = ExifWriter(photo)
    exif_options = ExifOptions(location=False)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:GPSLatitude" not in exif_data

    # with location
    exif_options = ExifOptions()
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:GPSLatitude" in exif_data
    assert exif_data["EXIF:GPSLatitude"] == photo.location[0]


def test_exifwriter_datetime(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with datetime"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)

    # datetime = False
    exif_writer = ExifWriter(photo)
    exif_options = ExifOptions(datetime=False)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:CreateDate" not in exif_data

    # with datetime
    exif_options = ExifOptions()
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "EXIF:CreateDate" in exif_data
    assert exif_data["EXIF:CreateDate"] == photo.date.strftime("%Y:%m:%d %H:%M:%S")


def test_exifwriter_merge_keywords_persons(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test merge_merge_exif_keywords, merge_exif_persons"""
    photo = photosdb.get_photo(UUID_MERGE_KEYWORDS)
    exported = export_and_wipe_metadata(photo, tmp_path)

    # write without merge_*
    exif_writer = ExifWriter(photo)
    exif_options = ExifOptions()
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    keywords = exif_data["IPTC:Keywords"]
    keywords = keywords if isinstance(keywords, list) else [keywords]
    assert sorted(keywords) == sorted(photo.keywords)

    persons = exif_data["XMP:PersonInImage"]
    persons = persons if isinstance(persons, list) else [persons]
    persons.append(_UNKNOWN_PERSON)  # this photo has an untagged face
    assert sorted(persons) == sorted(photo.persons)

    # write with merge_*
    exif_options = ExifOptions(merge_exif_keywords=True, merge_exif_persons=True)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    keywords = exif_data["IPTC:Keywords"]
    keywords = keywords if isinstance(keywords, list) else [keywords]
    assert "Test" in keywords

    persons = exif_data["XMP:PersonInImage"]
    persons = persons if isinstance(persons, list) else [persons]
    assert "Tim" in persons


def test_exifwriter_face_regions(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with face_regions"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    exported = export_and_wipe_metadata(photo, tmp_path)

    # face_regions = False
    exif_writer = ExifWriter(photo)
    exif_options = ExifOptions(face_regions=False)
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "XMP:RegionPersonDisplayName" not in exif_data

    # with face_region
    exif_options = ExifOptions()
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert "XMP:RegionPersonDisplayName" in exif_data
    assert sorted(exif_data["XMP:RegionPersonDisplayName"]) == sorted(photo.persons)


def test_exifwriter_render_options(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test ExifWriter with render_options"""
    photo = photosdb.get_photo(UUID_LOCATION)
    exported = export_and_wipe_metadata(photo, tmp_path)

    exif_writer = ExifWriter(photo)
    exif_options = ExifOptions(
        render_options=RenderOptions(strip=True), description_template="Hello  "
    )
    exif_writer.write_exif_data(exported, exif_options)

    exif_data = ExifTool(exported).asdict()
    assert exif_data["EXIF:ImageDescription"] == "Hello"
