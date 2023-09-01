"""Test SidecarWriter """

import json
import os
import pathlib

import pytest

from osxphotos import PhotosDB
from osxphotos._constants import (
    _UNKNOWN_PERSON,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
)
from osxphotos.exiftool import get_exiftool_path
from osxphotos.exifwriter import ExifOptions
from osxphotos.exportoptions import ExportOptions
from osxphotos.sidecars import SidecarWriter, exiftool_json_sidecar, xmp_sidecar

PHOTOS_DB = "tests/Test-13.0.0.photoslibrary"

# Pumkins1 has (almost) all metadata fields
UUID_ALL_METADATA = "F12384F6-CD17-4151-ACBA-AE0E3688539E"  # Pumkins1.jpg
UUID_MERGE_KEYWORDS = "1EB2B765-0765-43BA-A90C-0D0580E6172C"  # Pumpkins3.jpg

# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None


@pytest.fixture(scope="module")
def photosdb():
    return PhotosDB(dbfile=os.path.join(os.getcwd(), PHOTOS_DB))


def test_xmp_sidecar(photosdb: PhotosDB):
    """Test xmp_sidecar function"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    options = ExportOptions()
    sidecar = xmp_sidecar(photo, options)

    # this doesn't validate the entire XMP sidecar, just that expected metadata appears in the sidecar
    assert "Girls with pumpkins" in sidecar
    assert "<stArea:h>0.090346</stArea:h>" in sidecar


def test_xmp_sidecar_template(photosdb: PhotosDB):
    """Test xmp_sidecar function with a template"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    options = ExportOptions(keyword_template=["FooBar"])
    sidecar = xmp_sidecar(photo=photo, options=options)
    assert "FooBar" in sidecar


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_xmp_sidecar_merge_keywords_persons(photosdb: PhotosDB):
    """Test merge_merge_exif_keywords, merge_exif_persons"""
    photo = photosdb.get_photo(UUID_MERGE_KEYWORDS)

    # sourcery skip: extract-duplicate-method, no-conditionals-in-tests, no-loop-in-tests

    # first without merge_*
    options = ExportOptions()
    sidecar = xmp_sidecar(photo, options)

    for person in photo.persons:
        if person == _UNKNOWN_PERSON:
            continue
        assert f"<rdf:li>{person}</rdf:li>" in sidecar

    for keyword in photo.keywords:
        assert f"<rdf:li>{keyword}</rdf:li>" in sidecar

    assert "<rdf:li>Tim</rdf:li>" not in sidecar
    assert "<rdf:li>Test</rdf:li>" not in sidecar

    # now with merge_*
    options = ExportOptions(merge_exif_keywords=True, merge_exif_persons=True)
    sidecar = xmp_sidecar(photo, options)

    for person in photo.persons:
        if person == _UNKNOWN_PERSON:
            continue
        assert f"<rdf:li>{person}</rdf:li>" in sidecar

    for keyword in photo.keywords:
        assert f"<rdf:li>{keyword}</rdf:li>" in sidecar

    assert "<rdf:li>Tim</rdf:li>" in sidecar
    assert "<rdf:li>Test</rdf:li>" in sidecar


def test_sidecarwriter_json(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test SidecarWriter with JSON output"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    sidecar_writer = SidecarWriter(photo)
    options = ExportOptions(sidecar=SIDECAR_JSON)
    results = sidecar_writer.write_sidecar_files(tmp_path / "test.jpg", options)
    assert len(results.sidecar_json_written) == 1
    assert pathlib.Path(results.sidecar_json_written[0]).name == "test.jpg.json"
    with open(results.sidecar_json_written[0], "r") as fp:
        sidecar_dict = json.load(fp)[0]
    assert sidecar_dict["IPTC:Keywords"] == photo.keywords


def test_sidecarwriter_exiftool(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test SidecarWriter with exiftool JSON output"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    sidecar_writer = SidecarWriter(photo)
    options = ExportOptions(sidecar=SIDECAR_EXIFTOOL)
    results = sidecar_writer.write_sidecar_files(tmp_path / "test.jpg", options)
    assert len(results.sidecar_exiftool_written) == 1
    assert pathlib.Path(results.sidecar_exiftool_written[0]).name == "test.jpg.json"
    with open(results.sidecar_exiftool_written[0], "r") as fp:
        sidecar_dict = json.load(fp)[0]
    assert sidecar_dict["Keywords"] == photo.keywords


def test_sidecarwriter_xmp_exiftool(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test SidecarWriter with multi-sidecar output"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    sidecar_writer = SidecarWriter(photo)
    options = ExportOptions(sidecar=SIDECAR_EXIFTOOL | SIDECAR_XMP)
    results = sidecar_writer.write_sidecar_files(tmp_path / "test.jpg", options)
    assert len(results.sidecar_exiftool_written) == 1
    assert len(results.sidecar_xmp_written) == 1
    assert pathlib.Path(results.sidecar_exiftool_written[0]).name == "test.jpg.json"
    assert pathlib.Path(results.sidecar_xmp_written[0]).name == "test.jpg.xmp"


def test_sidecarwriter_xmp_json(photosdb: PhotosDB, tmp_path: pathlib.Path):
    """Test SidecarWriter with multi-sidecar output and drop extension"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    sidecar_writer = SidecarWriter(photo)
    options = ExportOptions(sidecar=SIDECAR_JSON | SIDECAR_XMP, sidecar_drop_ext=True)
    results = sidecar_writer.write_sidecar_files(tmp_path / "test.jpg", options)
    assert len(results.sidecar_json_written) == 1
    assert len(results.sidecar_xmp_written) == 1
    assert pathlib.Path(results.sidecar_json_written[0]).name == "test.json"
    assert pathlib.Path(results.sidecar_xmp_written[0]).name == "test.xmp"


def test_exiftool_json_sidecar(photosdb: PhotosDB):
    """Test exiftool_json_sidecar()"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    options = ExportOptions()
    sidecar = exiftool_json_sidecar(photo=photo, options=options)
    sidecar_dict = json.loads(sidecar)[0]
    assert sidecar_dict["XMP:Description"] == "Girls with pumpkins"
    assert "SourceFile" not in sidecar_dict  # didn't pass filename arg


def test_exiftool_json_sidecar_filename(photosdb: PhotosDB):
    """Test exiftool_json_sidecar() with filename arg"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    options = ExportOptions()
    sidecar = exiftool_json_sidecar(photo=photo, options=options, filename="Test.jpg")
    sidecar_dict = json.loads(sidecar)[0]
    assert sidecar_dict["XMP:Description"] == "Girls with pumpkins"
    assert sidecar_dict["SourceFile"] == "Test.jpg"


def test_exiftool_json_sidecar_exifoptions(photosdb: PhotosDB):
    """Test exiftool_json_sidecar() with ExifOptions"""
    photo = photosdb.get_photo(UUID_ALL_METADATA)
    options = ExifOptions()
    sidecar = exiftool_json_sidecar(photo=photo, options=options)
    sidecar_dict = json.loads(sidecar)[0]
    assert sidecar_dict["XMP:Description"] == "Girls with pumpkins"
    assert "SourceFile" not in sidecar_dict  # didn't pass filename arg
