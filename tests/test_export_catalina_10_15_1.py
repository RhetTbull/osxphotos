import pytest

from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.utils import dd_to_dms_str

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-10.15.1.photoslibrary/database/photos.db"

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
    "no_adjustments": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "location": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_location": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "external_edit": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_external_edit": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "export": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
    "xmp": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
}


def test_export_1():
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_2():
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_3():
    # test file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
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


def test_export_4():
    # test user supplied file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
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


def test_export_5():
    # test file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_6():
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_7():
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())


def test_export_8():
    # try to export missing file
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_9():
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == ValueError


def test_export_10():
    # try to export edited file that's not edited and name provided
    # should raise exception
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == ValueError


def test_export_11():
    # export edited file with name provided
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    assert got_dest == expected_dest


def test_export_12():
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = pathlib.Path(photos[0].filename).stem + "_edited" + edited_suffix
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)[0]
    assert got_dest == expected_dest


def test_export_13():
    # export to invalid destination
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_no_xattr():
    # test basic export with no_xattr=True
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, no_xattr=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_dd_to_dms_str_1():
    import osxphotos

    lat_str, lon_str = dd_to_dms_str(
        34.559331096, 69.206499174
    )  # Kabul, 34°33'33.59" N 69°12'23.40" E

    assert lat_str == "34 deg 33' 33.59\" N"
    assert lon_str == "69 deg 12' 23.40\" E"


def test_dd_to_dms_str_2():
    import osxphotos

    lat_str, lon_str = dd_to_dms_str(
        -34.601997592, -58.375665164
    )  # Buenos Aires, 34°36'7.19" S 58°22'32.39" W

    assert lat_str == "34 deg 36' 7.19\" S"
    assert lon_str == "58 deg 22' 32.39\" W"


def test_dd_to_dms_str_3():
    import osxphotos

    lat_str, lon_str = dd_to_dms_str(
        -1.2666656, 36.7999968
    )  # Nairobi, 1°15'60.00" S 36°47'59.99" E

    assert lat_str == "1 deg 15' 60.00\" S"
    assert lon_str == "36 deg 47' 59.99\" E"


def test_dd_to_dms_str_4():
    import osxphotos

    lat_str, lon_str = dd_to_dms_str(
        38.889248, -77.050636
    )  # DC: 38° 53' 21.2928" N, 77° 3' 2.2896" W

    assert lat_str == "38 deg 53' 21.29\" N"
    assert lon_str == "77 deg 3' 2.29\" W"


def test_exiftool_json_sidecar():
    import osxphotos
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])

    json_expected = json.loads(
        """
    [{"XMP:Title": "St. James\'s Park", 
    "XMP:TagsList": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "IPTC:Keywords": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "XMP:Subject": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "EXIF:GPSLatitude": "51 deg 30\' 12.86\\" N", 
    "EXIF:GPSLongitude": "0 deg 7\' 54.50\\" W", 
    "EXIF:GPSLatitudeRef": "North", "EXIF:GPSLongitudeRef": "West", 
    "EXIF:DateTimeOriginal": "2018:10:13 09:18:12",
    "EXIF:OffsetTimeOriginal": "-04:00",
    "EXIF:ModifyDate": "2019:12:08 14:06:44",
    "_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos"
    }] """
    )[0]

    json_got = photos[0]._exiftool_json_sidecar()
    json_got = json.loads(json_got)[0]

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_exiftool_json_sidecar_use_persons_keyword():
    import osxphotos
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    json_expected = json.loads(
        """
        [{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", 
        "EXIF:ImageDescription": "Girls with pumpkins", 
        "XMP:Description": "Girls with pumpkins", 
        "XMP:Title": "Can we carry this?", 
        "XMP:TagsList": ["Kids", "Suzy", "Katie"], 
        "IPTC:Keywords": ["Kids", "Suzy", "Katie"], 
        "XMP:PersonInImage": ["Suzy", "Katie"], 
        "XMP:Subject": ["Kids", "Suzy", "Katie"], 
        "EXIF:DateTimeOriginal": "2018:09:28 15:35:49", 
        "EXIF:OffsetTimeOriginal": "-04:00", 
        "EXIF:ModifyDate": "2019:11:24 13:09:17"}]
        """
    )[0]

    json_got = photos[0]._exiftool_json_sidecar(use_persons_as_keywords=True)
    json_got = json.loads(json_got)[0]

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_exiftool_json_sidecar_use_albums_keyword():
    import osxphotos
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    json_expected = json.loads(
        """
        [{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", 
        "EXIF:ImageDescription": "Girls with pumpkins", 
        "XMP:Description": "Girls with pumpkins", 
        "XMP:Title": "Can we carry this?", 
        "XMP:TagsList": ["Kids", "Pumpkin Farm", "Test Album"], 
        "IPTC:Keywords": ["Kids", "Pumpkin Farm", "Test Album"], 
        "XMP:PersonInImage": ["Suzy", "Katie"], 
        "XMP:Subject": ["Kids", "Suzy", "Katie"], 
        "EXIF:DateTimeOriginal": "2018:09:28 15:35:49", 
        "EXIF:OffsetTimeOriginal": "-04:00", 
        "EXIF:ModifyDate": "2019:11:24 13:09:17"}]
        """
    )[0]

    json_got = photos[0]._exiftool_json_sidecar(use_albums_as_keywords=True)
    json_got = json.loads(json_got)[0]

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_xmp_sidecar():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
        <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description>Girls with pumpkins</dc:description>
        <dc:title>Can we carry this?</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-09-28T15:35:49.063000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        <Iptc4xmpExt:PersonInImage>
            <rdf:Bag>
                    <rdf:li>Suzy</rdf:li>
                    <rdf:li>Katie</rdf:li>
            </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-09-28T15:35:49</xmp:CreateDate>
        <xmp:ModifyDate>2018-09-28T15:35:49</xmp:ModifyDate>
        </rdf:Description>
         <rdf:Description rdf:about=""
            xmlns:exif='http://ns.adobe.com/exif/1.0/'>
        </rdf:Description>
        </rdf:RDF>
    </x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar()
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(
        sorted(xmp_expected_lines), sorted(xmp_got_lines)
    ):
        assert line_expected == line_got


def test_xmp_sidecar_use_persons_keyword():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
        <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description>Girls with pumpkins</dc:description>
        <dc:title>Can we carry this?</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-09-28T15:35:49.063000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        <Iptc4xmpExt:PersonInImage>
            <rdf:Bag>
                    <rdf:li>Suzy</rdf:li>
                    <rdf:li>Katie</rdf:li>
            </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-09-28T15:35:49</xmp:CreateDate>
        <xmp:ModifyDate>2018-09-28T15:35:49</xmp:ModifyDate>
        </rdf:Description>
        <rdf:Description rdf:about=""
            xmlns:exif='http://ns.adobe.com/exif/1.0/'>
        </rdf:Description>
        </rdf:RDF>
    </x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar(use_persons_as_keywords=True)
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(
        sorted(xmp_expected_lines), sorted(xmp_got_lines)
    ):
        assert line_expected == line_got


def test_xmp_sidecar_use_albums_keyword():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
        <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description>Girls with pumpkins</dc:description>
        <dc:title>Can we carry this?</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-09-28T15:35:49.063000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        <Iptc4xmpExt:PersonInImage>
            <rdf:Bag>
                    <rdf:li>Suzy</rdf:li>
                    <rdf:li>Katie</rdf:li>
            </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Pumpkin Farm</rdf:li>
                <rdf:li>Test Album</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-09-28T15:35:49</xmp:CreateDate>
        <xmp:ModifyDate>2018-09-28T15:35:49</xmp:ModifyDate>
        </rdf:Description>
        <rdf:Description rdf:about=""
            xmlns:exif='http://ns.adobe.com/exif/1.0/'>
        </rdf:Description>
        </rdf:RDF>
    </x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar(use_albums_as_keywords=True)
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(
        sorted(xmp_expected_lines), sorted(xmp_got_lines)
    ):
        assert line_expected == line_got


def test_xmp_sidecar_gps():
    """ Test export XMP sidecar with GPS info """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
    <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description></dc:description>
        <dc:title>St. James's Park</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>UK</rdf:li>
                <rdf:li>England</rdf:li>
                <rdf:li>London</rdf:li>
                <rdf:li>United Kingdom</rdf:li>
                <rdf:li>London 2018</rdf:li>
                <rdf:li>St. James's Park</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-10-13T09:18:12.501000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about=""  
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>UK</rdf:li>
                <rdf:li>England</rdf:li>
                <rdf:li>London</rdf:li>
                <rdf:li>United Kingdom</rdf:li>
                <rdf:li>London 2018</rdf:li>
                <rdf:li>St. James's Park</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-10-13T09:18:12</xmp:CreateDate>
        <xmp:ModifyDate>2018-10-13T09:18:12</xmp:ModifyDate>
        </rdf:Description>
        <rdf:Description rdf:about=""
            xmlns:exif='http://ns.adobe.com/exif/1.0/'>
        <exif:GPSLongitudeRef>W</exif:GPSLongitudeRef>
        <exif:GPSLongitude>0.1318055</exif:GPSLongitude>
        <exif:GPSLatitude>51.50357167</exif:GPSLatitude>
        <exif:GPSLatitudeRef>N</exif:GPSLatitudeRef>
        </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar()
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(
        sorted(xmp_expected_lines), sorted(xmp_got_lines)
    ):
        assert line_expected == line_got

