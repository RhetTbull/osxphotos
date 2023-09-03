""" Test XMP sidecar """

import pathlib
import tempfile

import pytest

import osxphotos
from osxphotos._constants import SIDECAR_XMP
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.exportoptions import ExportOptions
from osxphotos.fileutil import FileUtil
from osxphotos.photoexporter import PhotoExporter

PHOTOS_DB_15_7 = "tests/Test-10.15.7.photoslibrary"

XMP_TEST_CASES = {
    "no_title": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "no_keywords": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "video": "35329C57-B963-48D6-BB75-6AFF9370CBBC",
    "title_descr_tag_person": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "descr_tag_person": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
}


# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool = get_exiftool_path()
except:
    exiftool = None


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_7)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_sidecar_xmp(photosdb):
    for test_case, uuid in XMP_TEST_CASES.items():
        tempdir = tempfile.TemporaryDirectory(prefix="osxphotos")
        dest = tempdir.name
        photo = photosdb.get_photo(uuid)
        export_options = ExportOptions(sidecar=SIDECAR_XMP)
        PhotoExporter(photo).export(
            dest, photo.original_filename, options=export_options
        )
        filepath = str(pathlib.Path(dest) / photo.original_filename)
        xmppath = filepath + ".xmp"

        # update the exif and ensure no warnings or errors
        exif = ExifTool(filepath)
        output, warning, error = exif.run_commands("-tagsfromfile", xmppath, "-all:all")
        assert not warning
        assert not error

        # merge xmp sidecar and ensure no warnings or errors
        test_xmp = str(pathlib.Path(dest) / "test.xmp")
        FileUtil.copy(xmppath, test_xmp)
        exif = ExifTool(test_xmp)
        output, warning, error = exif.run_commands(
            "-tagsfromfile", xmppath, "-all:all", test_xmp, no_file=True
        )
        assert not warning
        assert not error
