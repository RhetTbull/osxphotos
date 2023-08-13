""" Test ExportDB """

import os
import pathlib
import shutil
import sqlite3
import tempfile

import pytest

from osxphotos._version import __version__
from osxphotos.export_db import (
    OSXPHOTOS_EXPORTDB_VERSION,
    ExportDB,
    ExportDBInMemory,
    ExportDBTemp,
    ExportRecord,
)
from osxphotos.export_db_utils import export_db_get_version

EXIF_DATA = """[{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", "EXIF:ImageDescription": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "XMP:Description": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "XMP:Title": "Elder Park", "EXIF:GPSLatitude": "34 deg 55' 8.01\" S", "EXIF:GPSLongitude": "138 deg 35' 48.70\" E", "Composite:GPSPosition": "34 deg 55' 8.01\" S, 138 deg 35' 48.70\" E", "EXIF:GPSLatitudeRef": "South", "EXIF:GPSLongitudeRef": "East", "EXIF:DateTimeOriginal": "2017:06:20 17:18:56", "EXIF:OffsetTimeOriginal": "+09:30", "EXIF:ModifyDate": "2020:05:18 14:42:04"}]"""  # noqa: E501
INFO_DATA = """{"uuid": "3DD2C897-F19E-4CA6-8C22-B027D5A71907", "filename": "3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg", "original_filename": "IMG_4547.jpg", "date": "2017-06-20T17:18:56.518000+09:30", "description": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "title": "Elder Park", "keywords": [], "labels": ["Statue", "Art"], "albums": ["AlbumInFolder"], "folders": {"AlbumInFolder": ["Folder1", "SubFolder2"]}, "persons": [], "path": "/Users/rhet/Pictures/Test-10.15.4.photoslibrary/originals/3/3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg", "ismissing": false, "hasadjustments": true, "external_edit": false, "favorite": false, "hidden": false, "latitude": -34.91889167000001, "longitude": 138.59686167, "path_edited": "/Users/rhet/Pictures/Test-10.15.4.photoslibrary/resources/renders/3/3DD2C897-F19E-4CA6-8C22-B027D5A71907_1_201_a.jpeg", "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null, "date_modified": "2020-05-18T14:42:04.608664+09:30", "portrait": false, "screenshot": false, "slow_mo": false, "time_lapse": false, "hdr": false, "selfie": false, "panorama": false, "has_raw": false, "uti_raw": null, "path_raw": null, "place": {"name": "Elder Park, Adelaide, South Australia, Australia, River Torrens", "names": {"field0": [], "country": ["Australia"], "state_province": ["South Australia"], "sub_administrative_area": ["Adelaide"], "city": ["Adelaide", "Adelaide"], "field5": [], "additional_city_info": ["Adelaide CBD", "Tarndanya"], "ocean": [], "area_of_interest": ["Elder Park", ""], "inland_water": ["River Torrens", "River Torrens"], "field10": [], "region": [], "sub_throughfare": [], "field13": [], "postal_code": [], "field15": [], "field16": [], "street_address": [], "body_of_water": ["River Torrens", "River Torrens"]}, "country_code": "AU", "ishome": false, "address_str": "River Torrens, Adelaide SA, Australia", "address": {"street": null, "sub_locality": "Tarndanya", "city": "Adelaide", "sub_administrative_area": "Adelaide", "state_province": "SA", "postal_code": null, "country": "Australia", "iso_country_code": "AU"}}, "exif": {"flash_fired": false, "iso": 320, "metering_mode": 3, "sample_rate": null, "track_format": null, "white_balance": 0, "aperture": 2.2, "bit_rate": null, "duration": null, "exposure_bias": 0.0, "focal_length": 4.15, "fps": null, "latitude": null, "longitude": null, "shutter_speed": 0.058823529411764705, "camera_make": "Apple", "camera_model": "iPhone 6s", "codec": null, "lens_model": "iPhone 6s back camera 4.15mm f/2.2"}}"""  # noqa: E501
SIDECAR_DATA = """FOO_BAR"""
METADATA_DATA = "FIZZ"
DIGEST_DATA = "FIZZ"

EXIF_DATA2 = """[{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", "XMP:Title": "St. James's Park", "XMP:TagsList": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "IPTC:Keywords": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "XMP:Subject": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "EXIF:GPSLatitude": "51 deg 30' 12.86\" N", "EXIF:GPSLongitude": "0 deg 7' 54.50\" W", "Composite:GPSPosition": "51 deg 30' 12.86\" N, 0 deg 7' 54.50\" W", "EXIF:GPSLatitudeRef": "North", "EXIF:GPSLongitudeRef": "West", "EXIF:DateTimeOriginal": "2018:10:13 09:18:12", "EXIF:OffsetTimeOriginal": "-04:00", "EXIF:ModifyDate": "2019:12:08 14:06:44"}]"""  # noqa: E501
INFO_DATA2 = """{"uuid": "F2BB3F98-90F0-4E4C-A09B-25C6822A4529", "filename": "F2BB3F98-90F0-4E4C-A09B-25C6822A4529.jpeg", "original_filename": "IMG_8440.JPG", "date": "2019-06-11T11:42:06.711805-07:00", "description": null, "title": null, "keywords": [], "labels": ["Sky", "Cloudy", "Fence", "Land", "Outdoor", "Park", "Amusement Park", "Roller Coaster"], "albums": [], "folders": {}, "persons": [], "path": "/Volumes/MacBook Catalina - Data/Users/rhet/Pictures/Photos Library.photoslibrary/originals/F/F2BB3F98-90F0-4E4C-A09B-25C6822A4529.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": 33.81558666666667, "longitude": -117.99298, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": true, "incloud": true, "date_modified": "2019-10-14T00:51:47.141950-07:00", "portrait": false, "screenshot": false, "slow_mo": false, "time_lapse": false, "hdr": false, "selfie": false, "panorama": false, "has_raw": false, "uti_raw": null, "path_raw": null, "place": {"name": "Adventure City, Stanton, California, United States", "names": {"field0": [], "country": ["United States"], "state_province": ["California"], "sub_administrative_area": ["Orange"], "city": ["Stanton", "Anaheim", "Anaheim"], "field5": [], "additional_city_info": ["West Anaheim"], "ocean": [], "area_of_interest": ["Adventure City", "Adventure City"], "inland_water": [], "field10": [], "region": [], "sub_throughfare": [], "field13": [], "postal_code": [], "field15": [], "field16": [], "street_address": [], "body_of_water": []}, "country_code": "US", "ishome": false, "address_str": "Adventure City, 1240 S Beach Blvd, Anaheim, CA  92804, United States", "address": {"street": "1240 S Beach Blvd", "sub_locality": "West Anaheim", "city": "Stanton", "sub_administrative_area": "Orange", "state_province": "CA", "postal_code": "92804", "country": "United States", "iso_country_code": "US"}}, "exif": {"flash_fired": false, "iso": 25, "metering_mode": 5, "sample_rate": null, "track_format": null, "white_balance": 0, "aperture": 2.2, "bit_rate": null, "duration": null, "exposure_bias": 0.0, "focal_length": 4.15, "fps": null, "latitude": null, "longitude": null, "shutter_speed": 0.0004940711462450593, "camera_make": "Apple", "camera_model": "iPhone 6s", "codec": null, "lens_model": "iPhone 6s back camera 4.15mm f/2.2"}}"""  # noqa: E501
DIGEST_DATA2 = "BUZZ"
EXPORT_DATABASE_V1 = "tests/export_db_version1.db"


def test_export_db():
    """test ExportDB"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)
    assert db.was_created
    assert not db.was_upgraded
    assert db.version == OSXPHOTOS_EXPORTDB_VERSION

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    uuid = "FOOBAR"
    assert db.get_photoinfo_for_uuid(uuid) is None
    db.set_photoinfo_for_uuid(uuid, INFO_DATA)
    assert db.get_photoinfo_for_uuid(uuid) == INFO_DATA

    assert db.get_uuid_for_file(filepath) is None
    db.create_file_record(filepath, uuid)
    assert db.get_uuid_for_file(filepath) == uuid
    assert db.get_files_for_uuid(uuid) == [filepath]

    record = db.get_file_record(filepath)
    assert record.uuid == uuid
    assert record.photoinfo == INFO_DATA
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    assert record.src_sig == (None, None, None)
    assert record.dest_sig == (None, None, None)
    assert record.digest is None
    assert record.exifdata is None
    record.digest = DIGEST_DATA  # for next assert

    # test create_or_get_file_record
    # existing record
    record2 = db.create_or_get_file_record(filepath, uuid)
    assert record2.uuid == uuid
    assert record.photoinfo == INFO_DATA
    assert record.digest == DIGEST_DATA

    # new record
    filepath3 = os.path.join(tempdir.name, "test3.JPG")
    record3 = db.create_or_get_file_record(filepath3, "new_uuid")
    assert record3.uuid == "new_uuid"
    assert record3.photoinfo is None
    assert record3.digest is None

    # all uuids
    uuids = db.get_previous_uuids()
    assert sorted(uuids) == sorted(["new_uuid", uuid])


def test_export_db_constraints():
    """test ExportDB constraints"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)
    assert db.was_created
    assert not db.was_upgraded
    assert db.version == OSXPHOTOS_EXPORTDB_VERSION

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    uuid = "FOOBAR"
    db.set_photoinfo_for_uuid(uuid, INFO_DATA)
    record = db.create_file_record(filepath, uuid)
    record.photoinfo = INFO_DATA
    record.exifdata = EXIF_DATA
    record.digest = DIGEST_DATA
    record.src_sig = (7, 8, 9)
    record.dest_sig = (10, 11, 12)

    with pytest.raises(AttributeError):
        record.uuid = "BARFOO"

    with pytest.raises(sqlite3.IntegrityError):
        record2 = db.create_file_record(filepath, "NEW_UUID")

    with pytest.raises(AttributeError):
        # verify we can't add new attributes
        record.src_stats = (7, 8, 9)


def test_export_db_in_memory():
    """test ExportDBInMemory"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    uuid = "FOOBAR"
    record = db.create_file_record(filepath, uuid)
    record.photoinfo = INFO_DATA
    record.exifdata = EXIF_DATA
    record.digest = DIGEST_DATA
    record.src_sig = (7, 8, 9)
    record.dest_sig = (10, 11, 12)
    db.close()

    # create in memory version
    dbram = ExportDBInMemory(dbname, tempdir.name)
    record2 = dbram.get_file_record(filepath)
    assert record2.uuid == uuid
    assert record2.photoinfo == INFO_DATA
    assert record2.exifdata == EXIF_DATA
    assert record2.digest == DIGEST_DATA
    assert record2.src_sig == (7, 8, 9)
    assert record2.dest_sig == (10, 11, 12)
    assert dbram.get_files_for_uuid(uuid) == [filepath]

    # change some values
    record2.photoinfo = INFO_DATA2
    record2.exifdata = EXIF_DATA2
    record2.digest = DIGEST_DATA2
    record2.src_sig = (13, 14, 15)
    record2.dest_sig = (16, 17, 18)

    assert record2.photoinfo == INFO_DATA2
    assert record2.exifdata == EXIF_DATA2
    assert record2.digest == DIGEST_DATA2
    assert record2.src_sig == (13, 14, 15)
    assert record2.dest_sig == (16, 17, 18)

    # all uuids
    uuids = dbram.get_previous_uuids()
    assert uuids == [uuid]

    dbram.close()

    # re-open original, assert no changes
    db = ExportDB(dbname, tempdir.name)
    record = db.get_file_record(filepath)
    assert record.uuid == uuid
    assert record.photoinfo == INFO_DATA
    assert record.exifdata == EXIF_DATA
    assert record.digest == DIGEST_DATA
    assert record.src_sig == (7, 8, 9)
    assert record.dest_sig == (10, 11, 12)

    # all uuids
    uuids = db.get_previous_uuids()
    assert uuids == [uuid]


def test_export_db_in_memory_write_to_disk():
    """test ExportDBInMemory with write back to disk"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)

    filepath = os.path.join(tempdir.name, "test.JPG")

    uuid = "FOOBAR"
    record = db.create_file_record(filepath, uuid)
    record.photoinfo = INFO_DATA
    record.exifdata = EXIF_DATA
    record.digest = DIGEST_DATA
    record.src_sig = (7, 8, 9)
    record.dest_sig = (10, 11, 12)
    db.close()

    # create in memory version
    dbram = ExportDBInMemory(dbname, tempdir.name)
    record2 = dbram.get_file_record(filepath)
    assert record2.uuid == uuid
    assert record2.photoinfo == INFO_DATA
    assert record2.exifdata == EXIF_DATA
    assert record2.digest == DIGEST_DATA
    assert record2.src_sig == (7, 8, 9)
    assert record2.dest_sig == (10, 11, 12)

    # change some values
    record2.photoinfo = INFO_DATA2
    record2.exifdata = EXIF_DATA2
    record2.digest = DIGEST_DATA2
    record2.src_sig = (13, 14, 15)
    record2.dest_sig = (16, 17, 18)

    assert record2.photoinfo == INFO_DATA2
    assert record2.exifdata == EXIF_DATA2
    assert record2.digest == DIGEST_DATA2
    assert record2.src_sig == (13, 14, 15)
    assert record2.dest_sig == (16, 17, 18)

    # all uuids
    uuids = dbram.get_previous_uuids()
    assert uuids == [uuid]

    # write to disk
    dbram.write_to_disk()
    dbram.close()

    # re-open original, assert changes are written back
    db = ExportDB(dbname, tempdir.name)
    record = db.get_file_record(filepath)
    assert record.photoinfo == INFO_DATA2
    assert record.exifdata == EXIF_DATA2
    assert record.digest == DIGEST_DATA2
    assert record.src_sig == (13, 14, 15)
    assert record.dest_sig == (16, 17, 18)

    # all uuids
    uuids = db.get_previous_uuids()
    assert uuids == [uuid]


def test_export_db_in_memory_nofile():
    """test ExportDBInMemory with no dbfile"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    dbram = ExportDBInMemory(
        os.path.join(tempdir.name, "NOT_A_DATABASE_FILE.db"), tempdir.name
    )
    assert dbram.was_created
    assert not dbram.was_upgraded
    assert dbram.version == OSXPHOTOS_EXPORTDB_VERSION

    # set values
    uuid = "FOOBAR"
    record = dbram.create_file_record(filepath, uuid)
    record.photoinfo = INFO_DATA
    record.exifdata = EXIF_DATA
    record.digest = DIGEST_DATA
    record.src_sig = (7, 8, 9)
    record.dest_sig = (10, 11, 12)

    assert record.photoinfo == INFO_DATA
    assert record.exifdata == EXIF_DATA
    assert record.digest == DIGEST_DATA
    assert record.src_sig == (7, 8, 9)
    assert record.dest_sig == (10, 11, 12)
    assert record.uuid == uuid

    # change some values
    record.photoinfo = INFO_DATA2
    record.digest = DIGEST_DATA2
    assert record.photoinfo == INFO_DATA2
    assert record.digest == DIGEST_DATA2
    assert record.exifdata == EXIF_DATA


def test_export_db_temp():
    """test ExportDBTemp"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    dbram = ExportDBTemp()
    assert dbram.was_created
    assert not dbram.was_upgraded
    assert dbram.version == OSXPHOTOS_EXPORTDB_VERSION

    # set values
    uuid = "FOOBAR"
    record = dbram.create_file_record(filepath, uuid)
    record.photoinfo = INFO_DATA
    record.exifdata = EXIF_DATA
    record.digest = DIGEST_DATA
    record.src_sig = (7, 8, 9)
    record.dest_sig = (10, 11, 12)

    assert record.photoinfo == INFO_DATA
    assert record.exifdata == EXIF_DATA
    assert record.digest == DIGEST_DATA
    assert record.src_sig == (7, 8, 9)
    assert record.dest_sig == (10, 11, 12)
    assert record.uuid == uuid

    # change some values
    record.photoinfo = INFO_DATA2
    record.digest = DIGEST_DATA2
    assert record.photoinfo == INFO_DATA2
    assert record.digest == DIGEST_DATA2
    assert record.exifdata == EXIF_DATA

    dbram.close()


def test_export_record():
    """Test ExportRecord"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test.JPG")
    uuid = "FOOBAR"
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)

    assert db.get_file_record(filepath) is None
    record = db.create_file_record(filepath, uuid)
    assert record.uuid == uuid
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    record.src_sig = (1, 2, 3.0)
    assert record.src_sig == (1, 2, 3)
    record.dest_sig = (4, 5, 6.0)
    assert record.dest_sig == (4, 5, 6)
    record.digest = DIGEST_DATA
    assert record.digest == DIGEST_DATA
    record.exifdata = EXIF_DATA
    assert record.exifdata == EXIF_DATA
    record.photoinfo = INFO_DATA
    assert record.photoinfo == INFO_DATA
    record.export_options = 1
    assert record.export_options == 1

    # close and re-open
    db.close()
    db2 = ExportDB(dbname, tempdir.name)
    record = db2.get_file_record(filepath)
    assert record.uuid == uuid
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    assert record.src_sig == (1, 2, 3)
    assert record.dest_sig == (4, 5, 6)
    assert record.digest == "FIZZ"
    assert record.exifdata == EXIF_DATA
    assert record.photoinfo == INFO_DATA
    assert record.export_options == 1


def test_export_record_context_manager():
    """Test ExportRecord as context manager"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test.JPG")
    uuid = "FOOBAR_CONTEXT"
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)

    assert db.get_file_record(filepath) is None

    with db.create_file_record(filepath, uuid) as record:
        record.src_sig = (1, 2, 3.0)
        record.dest_sig = (4, 5, 6.0)
        record.digest = DIGEST_DATA
        record.exifdata = EXIF_DATA
        record.photoinfo = INFO_DATA
        record.export_options = 1

    assert record.uuid == uuid
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    assert record.src_sig == (1, 2, 3)
    assert record.dest_sig == (4, 5, 6)
    assert record.digest == "FIZZ"
    assert record.exifdata == EXIF_DATA
    assert record.photoinfo == INFO_DATA
    assert record.export_options == 1

    # close and re-open
    db.close()
    db2 = ExportDB(dbname, tempdir.name)
    record = db2.get_file_record(filepath)
    assert record.uuid == uuid
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    assert record.src_sig == (1, 2, 3)
    assert record.dest_sig == (4, 5, 6)
    assert record.digest == "FIZZ"
    assert record.exifdata == EXIF_DATA
    assert record.photoinfo == INFO_DATA
    assert record.export_options == 1


def test_export_record_context_manager_error():
    """Test ExportRecord as context manager doesn't commit data on error"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test_boom.JPG")
    uuid = "FOOBAR_CONTEXT_BOOM"
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)

    try:
        with db.create_file_record(filepath, uuid) as record:
            record.src_sig = (1, 2, 3.0)
            record.dest_sig = (4, 5, 6.0)
            record.digest = DIGEST_DATA
            record.exifdata = EXIF_DATA
            record.photoinfo = INFO_DATA
            raise Exception("Boom")
    except Exception:
        pass

    record = db.get_file_record(filepath)
    assert record.uuid == uuid
    assert record.filepath == pathlib.Path(filepath).name
    assert record.filepath_normalized == pathlib.Path(filepath).name.lower()
    assert record.src_sig == (None, None, None)
    assert record.dest_sig == (None, None, None)
    assert record.digest is None
    assert record.exifdata is None
    assert record.photoinfo is None


def test_get_export_db_version():
    """Test export_db_get_version"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)

    osxphotos_ver, export_db_ver = export_db_get_version(dbname)
    assert osxphotos_ver == __version__
    assert export_db_ver == OSXPHOTOS_EXPORTDB_VERSION


def test_export_db_migration(tmp_path):
    """Test export_db migration"""
    # create export db with version 1
    test_db = tmp_path / "osxphotos_export.db"
    shutil.copyfile(EXPORT_DATABASE_V1, test_db)
    export_db = ExportDB(test_db, tmp_path)
    assert export_db.was_upgraded
    assert export_db.version == OSXPHOTOS_EXPORTDB_VERSION

    # now open again, should not be upgraded
    export_db = ExportDB(test_db, tmp_path)
    assert not export_db.was_upgraded
    assert export_db.version == OSXPHOTOS_EXPORTDB_VERSION

    # now let's mess with the version to force a migration, see #794
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("DELETE FROM version;")
    c.execute("INSERT INTO version VALUES (1, '0.34.3', '1.0');")
    conn.commit()
    conn.close()
    export_db = ExportDB(test_db, tmp_path)
    assert export_db.was_upgraded
    assert export_db.version == OSXPHOTOS_EXPORTDB_VERSION
