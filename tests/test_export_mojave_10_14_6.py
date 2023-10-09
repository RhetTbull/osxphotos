import json
import pathlib

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.exportoptions import ExportOptions
from osxphotos.sidecars import exiftool_json_sidecar, xmp_sidecar

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.14.6.photoslibrary"

KEYWORDS = [
    "Kids",
    "wedding",
    "flowers",
    "England",
    "London",
    "London 2018",
    "St. James's Park",
    "UK",
    "United Kingdom",
]
PERSONS = ["Katie", "Suzy", "Maria"]
ALBUMS = ["Pumpkin Farm", "Test Album", "Test Album (1)"]
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 2,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1}
ALBUM_DICT = {"Pumpkin Farm": 3, "Test Album": 1, "Test Album (1)": 1}

UUID_DICT = {
    "missing": "od0fmC7NQx+ayVr+%i06XA",
    "has_adjustments": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "no_adjustments": "15uNd7%8RguTEgNPKHfTWw",
    "export": "15uNd7%8RguTEgNPKHfTWw",
    "location": "3Jn73XpSQQCluzRBMWRsMA",
    "xmp": "8SOE9s0XQVGsuq4ONohTng",
}

SIDECAR_DIR = "./tests/sidecars"


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_export_1(photosdb):
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_2(photosdb):
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_3(photosdb):
    # test file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_4(photosdb):
    # test user supplied file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_5(photosdb):
    # test file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_6(photosdb):
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_7(photosdb):
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)[0]
    assert e.type == type(FileExistsError())


def test_export_8(photosdb):
    # try to export missing file
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    assert photos[0].export(dest) == []


def test_export_9(photosdb):
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == ValueError


def test_export_10(photosdb):
    # try to export edited file that's not edited and name provided
    # should raise exception
    import os
    import os.path
    import tempfile
    import time

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)[0]
    assert e.type == ValueError


def test_export_11(photosdb):
    # export edited file with name provided
    import os
    import os.path
    import tempfile
    import time

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    assert got_dest == expected_dest


def test_export_12(photosdb):
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = pathlib.Path(photos[0].filename).stem + "_edited" + edited_suffix
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)[0]
    assert got_dest == expected_dest


def test_export_13(photosdb):
    # export to invalid destination
    # should raise exception
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)[0]
    assert e.type == type(FileNotFoundError())


def test_exiftool_json_sidecar(photosdb):
    uuid = UUID_DICT["location"]
    photo = photosdb.get_photo(uuid)

    with open(str(pathlib.Path(SIDECAR_DIR) / f"{uuid}.json"), "r") as fp:
        json_expected = json.load(fp)[0]

    json_got = exiftool_json_sidecar(photo)
    json_got = json.loads(json_got)[0]

    assert json_got == json_expected


def test_xmp_sidecar(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_ext.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(photo, extension="jpg")

    assert xmp_got == xmp_expected


def test_xmp_sidecar_keyword_template(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_keyword_template.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(
        photo,
        ExportOptions(keyword_template=["{created.year}", "{folder_album}"]),
        extension="jpg",
    )

    assert xmp_got == xmp_expected
