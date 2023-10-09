""" Test export for 10.15.7 """

import json
import os
import os.path
import pathlib
import tempfile
import time

import pytest

import osxphotos
from osxphotos._constants import _MAX_IPTC_KEYWORD_LEN, _UNKNOWN_PERSON
from osxphotos.exiftool import get_exiftool_path
from osxphotos.exportoptions import ExportOptions
from osxphotos.sidecars import exiftool_json_sidecar, xmp_sidecar
from osxphotos.utils import dd_to_dms_str

# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool = get_exiftool_path()
except:
    exiftool = None

PHOTOS_DB = "./tests/Test-10.15.7.photoslibrary/database/photos.db"
SIDECAR_DIR = "./tests/sidecars"


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


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
    "Maria",
]
# Photos 5 includes blank person for detected face
PERSONS = ["Katie", "Suzy", "Maria", _UNKNOWN_PERSON]
ALBUMS = [
    "Pumpkin Farm",
    "Test Album",
]  # Note: there are 2 albums named "Test Album" for testing duplicate album names
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
    "Maria": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1, _UNKNOWN_PERSON: 1}
ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "Test Album": 2,
}  # Note: there are 2 albums named "Test Album" for testing duplicate album names

UUID_DICT = {
    "missing": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "favorite": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "not_favorite": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "hidden": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "not_hidden": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "has_adjustments": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "no_adjustments": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "location": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_location": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "external_edit": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_external_edit": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "export": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
    "xmp": "F12384F6-CD17-4151-ACBA-AE0E3688539E",  # Pumkins1.jpg
}

# used with UUID_DICT["xmp"]
XMP_FILENAME = "Pumkins1.jpg.xmp"
XMP_JPG_FILENAME = "Pumkins1.jpg"

EXIF_JSON_UUID = UUID_DICT["has_adjustments"]


def test_export_1(photosdb):
    # test basic export
    # get an unedited image and export it using default filename

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_2(photosdb):
    # test export with user provided filename

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

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest_1 = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_4(photosdb):
    # test user supplied file already exists and test increment=True (default)

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest_1 = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_5(photosdb):
    # test file already exists and test increment=True (default)
    # and overwrite = True

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_6(photosdb):
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True

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

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())


def test_export_8(photosdb):
    # try to export missing file

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    assert photos[0].export(dest) == []


def test_export_9(photosdb):
    # try to export edited file that's not edited
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == ValueError


def test_export_10(photosdb):
    # try to export edited file that's not edited and name provided
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == ValueError


def test_export_11(photosdb):
    # export edited file with name provided

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

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = (
        pathlib.Path(photos[0].original_filename).stem + "_edited" + edited_suffix
    )
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)[0]
    assert got_dest == expected_dest


def test_export_13(photosdb):
    # export to invalid destination
    # should raise exception

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
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_dd_to_dms_str_1():
    lat_str, lon_str = dd_to_dms_str(
        34.559331096, 69.206499174
    )  # Kabul, 34°33'33.59" N 69°12'23.40" E

    assert lat_str == "34 deg 33' 33.59\" N"
    assert lon_str == "69 deg 12' 23.40\" E"


def test_dd_to_dms_str_2():
    lat_str, lon_str = dd_to_dms_str(
        -34.601997592, -58.375665164
    )  # Buenos Aires, 34°36'7.19" S 58°22'32.39" W

    assert lat_str == "34 deg 36' 7.19\" S"
    assert lon_str == "58 deg 22' 32.39\" W"


def test_dd_to_dms_str_3():
    lat_str, lon_str = dd_to_dms_str(
        -1.2666656, 36.7999968
    )  # Nairobi, 1°15'60.00" S 36°47'59.99" E

    assert lat_str == "1 deg 15' 60.00\" S"
    assert lon_str == "36 deg 47' 59.99\" E"


def test_dd_to_dms_str_4():
    lat_str, lon_str = dd_to_dms_str(
        38.889248, -77.050636
    )  # DC: 38° 53' 21.2928" N, 77° 3' 2.2896" W

    assert lat_str == "38 deg 53' 21.29\" N"
    assert lon_str == "77 deg 3' 2.29\" W"


def test_exiftool_json_sidecar(photosdb):
    uuid = EXIF_JSON_UUID
    photo = photosdb.get_photo(uuid)

    with open(str(pathlib.Path(SIDECAR_DIR) / f"{uuid}.json"), "r") as fp:
        json_expected = json.load(fp)[0]

    json_got = exiftool_json_sidecar(photo)
    json_got = json.loads(json_got)[0]

    assert json_got == json_expected


def test_exiftool_json_sidecar_ignore_date_modified(photosdb):
    uuid = EXIF_JSON_UUID
    photo = photosdb.get_photo(uuid)

    with open(
        str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_ignore_date_modified.json"), "r"
    ) as fp:
        json_expected = json.load(fp)[0]

    json_got = exiftool_json_sidecar(photo, ExportOptions(ignore_date_modified=True))
    json_got = json.loads(json_got)[0]

    assert json_got == json_expected


def test_exiftool_json_sidecar_keyword_template_long(caplog, photosdb):
    """Test that long keywords generate a warning"""
    caplog.set_level("WARNING")

    photos = photosdb.photos(uuid=[EXIF_JSON_UUID])

    json_expected = json.loads(
        """
        [{"EXIF:ImageDescription": "Bride Wedding day", 
        "XMP:Description": "Bride Wedding day", 
        "IPTC:Caption-Abstract": "Bride Wedding day", 
        "XMP:TagsList": ["Maria", "wedding", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"], 
        "IPTC:Keywords": ["Maria", "wedding", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"], 
        "XMP:Subject": ["Maria", "wedding", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"], 
        "XMP:PersonInImage": ["Maria"], 
        "EXIF:DateTimeOriginal": "2019:04:15 14:40:24", 
        "EXIF:CreateDate": "2019:04:15 14:40:24", 
        "EXIF:OffsetTimeOriginal": "-04:00", 
        "IPTC:DateCreated": "2019:04:15", 
        "IPTC:TimeCreated": "14:40:24-04:00", 
        "EXIF:ModifyDate": "2019:07:27 17:33:28"}]
        """
    )[0]

    long_str = "x" * (_MAX_IPTC_KEYWORD_LEN + 1)
    photos[0]._verbose = print
    json_got = exiftool_json_sidecar(
        photos[0], ExportOptions(keyword_template=[long_str])
    )
    json_got = json.loads(json_got)[0]

    assert "some keywords exceed max IPTC Keyword length" in caplog.text

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_exiftool_json_sidecar_keyword_template(photosdb):
    uuid = EXIF_JSON_UUID
    photo = photosdb.get_photo(uuid)

    with open(
        str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_keyword_template.json"), "r"
    ) as fp:
        json_expected = json.load(fp)
    json_got = exiftool_json_sidecar(
        photo, ExportOptions(keyword_template=["{folder_album}"])
    )
    json_got = json.loads(json_got)

    assert json_got == json_expected


def test_exiftool_json_sidecar_use_persons_keyword(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(
        str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_persons_as_keywords.json"), "r"
    ) as fp:
        json_expected = json.load(fp)[0]

    json_got = exiftool_json_sidecar(photo, ExportOptions(use_persons_as_keywords=True))
    json_got = json.loads(json_got)[0]

    assert json_got == json_expected


def test_exiftool_json_sidecar_use_albums_keywords(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(
        str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_albums_as_keywords.json"), "r"
    ) as fp:
        json_expected = json.load(fp)

    json_got = exiftool_json_sidecar(photo, ExportOptions(use_albums_as_keywords=True))
    json_got = json.loads(json_got)

    assert json_got == json_expected


def test_exiftool_sidecar(photosdb):
    uuid = EXIF_JSON_UUID
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_no_tag_groups.json", "r") as fp:
        json_expected = fp.read()

    json_got = exiftool_json_sidecar(photo, tag_groups=False)

    assert json_got == json_expected


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_xmp_sidecar_is_valid(tmp_path, photosdb):
    """validate XMP sidecar file with exiftool"""
    from osxphotos.exiftool import ExifTool

    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])
    photos[0].export(str(tmp_path), XMP_JPG_FILENAME, sidecar_xmp=True)
    xmp_file = tmp_path / XMP_FILENAME
    assert xmp_file.is_file()
    exiftool = ExifTool(str(xmp_file))
    output, _, _ = exiftool.run_commands("-validate", "-warning")
    assert output == b"[ExifTool]      Validate                        : 0 0 0"


def test_xmp_sidecar(photosdb):
    uuid = UUID_DICT["xmp"]
    photos = photosdb.photos(uuid=[uuid])

    with open(f"tests/sidecars/{uuid}.xmp", "r") as file:
        xmp_expected = file.read()
    xmp_got = xmp_sidecar(photos[0], extension="jpg")
    assert xmp_got == xmp_expected


def test_xmp_sidecar_extension(photosdb):
    """test XMP sidecar when no extension is passed"""

    uuid = UUID_DICT["xmp"]
    photos = photosdb.photos(uuid=[uuid])

    with open(f"tests/sidecars/{uuid}.xmp", "r") as file:
        xmp_expected = file.read()
        xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = xmp_sidecar(photos[0])
    assert xmp_got == xmp_expected


def test_xmp_sidecar_use_persons_keyword(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_persons_as_keywords.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(
        photo, ExportOptions(use_persons_as_keywords=True), extension="jpg"
    )
    assert xmp_got == xmp_expected


def test_xmp_sidecar_use_albums_keyword(photosdb):
    uuid = UUID_DICT["xmp"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_albums_as_keywords.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(
        photo, ExportOptions(use_albums_as_keywords=True), extension="jpg"
    )
    assert xmp_got == xmp_expected


def test_xmp_sidecar_gps(photosdb):
    """Test export XMP sidecar with GPS info"""

    uuid = UUID_DICT["location"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(photo)
    assert xmp_got == xmp_expected


def test_xmp_sidecar_keyword_template(photosdb):
    uuid = UUID_DICT["location"]
    photo = photosdb.get_photo(uuid)

    with open(pathlib.Path(SIDECAR_DIR) / f"{uuid}_keyword_template.xmp") as fp:
        xmp_expected = fp.read()

    xmp_got = xmp_sidecar(
        photo,
        ExportOptions(keyword_template=["{created.year}", "{folder_album}"]),
        extension="jpg",
    )
    assert xmp_got == xmp_expected
