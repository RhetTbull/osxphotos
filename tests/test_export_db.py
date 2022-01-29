""" Test ExportDB """

import json

import pytest

EXIF_DATA = """[{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", "EXIF:ImageDescription": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "XMP:Description": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "XMP:Title": "Elder Park", "EXIF:GPSLatitude": "34 deg 55' 8.01\" S", "EXIF:GPSLongitude": "138 deg 35' 48.70\" E", "Composite:GPSPosition": "34 deg 55' 8.01\" S, 138 deg 35' 48.70\" E", "EXIF:GPSLatitudeRef": "South", "EXIF:GPSLongitudeRef": "East", "EXIF:DateTimeOriginal": "2017:06:20 17:18:56", "EXIF:OffsetTimeOriginal": "+09:30", "EXIF:ModifyDate": "2020:05:18 14:42:04"}]"""
INFO_DATA = """{"uuid": "3DD2C897-F19E-4CA6-8C22-B027D5A71907", "filename": "3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg", "original_filename": "IMG_4547.jpg", "date": "2017-06-20T17:18:56.518000+09:30", "description": "\u2068Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia\u2069", "title": "Elder Park", "keywords": [], "labels": ["Statue", "Art"], "albums": ["AlbumInFolder"], "folders": {"AlbumInFolder": ["Folder1", "SubFolder2"]}, "persons": [], "path": "/Users/rhet/Pictures/Test-10.15.4.photoslibrary/originals/3/3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg", "ismissing": false, "hasadjustments": true, "external_edit": false, "favorite": false, "hidden": false, "latitude": -34.91889167000001, "longitude": 138.59686167, "path_edited": "/Users/rhet/Pictures/Test-10.15.4.photoslibrary/resources/renders/3/3DD2C897-F19E-4CA6-8C22-B027D5A71907_1_201_a.jpeg", "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null, "date_modified": "2020-05-18T14:42:04.608664+09:30", "portrait": false, "screenshot": false, "slow_mo": false, "time_lapse": false, "hdr": false, "selfie": false, "panorama": false, "has_raw": false, "uti_raw": null, "path_raw": null, "place": {"name": "Elder Park, Adelaide, South Australia, Australia, River Torrens", "names": {"field0": [], "country": ["Australia"], "state_province": ["South Australia"], "sub_administrative_area": ["Adelaide"], "city": ["Adelaide", "Adelaide"], "field5": [], "additional_city_info": ["Adelaide CBD", "Tarndanya"], "ocean": [], "area_of_interest": ["Elder Park", ""], "inland_water": ["River Torrens", "River Torrens"], "field10": [], "region": [], "sub_throughfare": [], "field13": [], "postal_code": [], "field15": [], "field16": [], "street_address": [], "body_of_water": ["River Torrens", "River Torrens"]}, "country_code": "AU", "ishome": false, "address_str": "River Torrens, Adelaide SA, Australia", "address": {"street": null, "sub_locality": "Tarndanya", "city": "Adelaide", "sub_administrative_area": "Adelaide", "state_province": "SA", "postal_code": null, "country": "Australia", "iso_country_code": "AU"}}, "exif": {"flash_fired": false, "iso": 320, "metering_mode": 3, "sample_rate": null, "track_format": null, "white_balance": 0, "aperture": 2.2, "bit_rate": null, "duration": null, "exposure_bias": 0.0, "focal_length": 4.15, "fps": null, "latitude": null, "longitude": null, "shutter_speed": 0.058823529411764705, "camera_make": "Apple", "camera_model": "iPhone 6s", "codec": null, "lens_model": "iPhone 6s back camera 4.15mm f/2.2"}}"""
SIDECAR_DATA = """FOO_BAR"""

EXIF_DATA2 = """[{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", "XMP:Title": "St. James's Park", "XMP:TagsList": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "IPTC:Keywords": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "XMP:Subject": ["London 2018", "St. James's Park", "England", "United Kingdom", "UK", "London"], "EXIF:GPSLatitude": "51 deg 30' 12.86\" N", "EXIF:GPSLongitude": "0 deg 7' 54.50\" W", "Composite:GPSPosition": "51 deg 30' 12.86\" N, 0 deg 7' 54.50\" W", "EXIF:GPSLatitudeRef": "North", "EXIF:GPSLongitudeRef": "West", "EXIF:DateTimeOriginal": "2018:10:13 09:18:12", "EXIF:OffsetTimeOriginal": "-04:00", "EXIF:ModifyDate": "2019:12:08 14:06:44"}]"""
INFO_DATA2 = """{"uuid": "F2BB3F98-90F0-4E4C-A09B-25C6822A4529", "filename": "F2BB3F98-90F0-4E4C-A09B-25C6822A4529.jpeg", "original_filename": "IMG_8440.JPG", "date": "2019-06-11T11:42:06.711805-07:00", "description": null, "title": null, "keywords": [], "labels": ["Sky", "Cloudy", "Fence", "Land", "Outdoor", "Park", "Amusement Park", "Roller Coaster"], "albums": [], "folders": {}, "persons": [], "path": "/Volumes/MacBook Catalina - Data/Users/rhet/Pictures/Photos Library.photoslibrary/originals/F/F2BB3F98-90F0-4E4C-A09B-25C6822A4529.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": 33.81558666666667, "longitude": -117.99298, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": true, "incloud": true, "date_modified": "2019-10-14T00:51:47.141950-07:00", "portrait": false, "screenshot": false, "slow_mo": false, "time_lapse": false, "hdr": false, "selfie": false, "panorama": false, "has_raw": false, "uti_raw": null, "path_raw": null, "place": {"name": "Adventure City, Stanton, California, United States", "names": {"field0": [], "country": ["United States"], "state_province": ["California"], "sub_administrative_area": ["Orange"], "city": ["Stanton", "Anaheim", "Anaheim"], "field5": [], "additional_city_info": ["West Anaheim"], "ocean": [], "area_of_interest": ["Adventure City", "Adventure City"], "inland_water": [], "field10": [], "region": [], "sub_throughfare": [], "field13": [], "postal_code": [], "field15": [], "field16": [], "street_address": [], "body_of_water": []}, "country_code": "US", "ishome": false, "address_str": "Adventure City, 1240 S Beach Blvd, Anaheim, CA  92804, United States", "address": {"street": "1240 S Beach Blvd", "sub_locality": "West Anaheim", "city": "Stanton", "sub_administrative_area": "Orange", "state_province": "CA", "postal_code": "92804", "country": "United States", "iso_country_code": "US"}}, "exif": {"flash_fired": false, "iso": 25, "metering_mode": 5, "sample_rate": null, "track_format": null, "white_balance": 0, "aperture": 2.2, "bit_rate": null, "duration": null, "exposure_bias": 0.0, "focal_length": 4.15, "fps": null, "latitude": null, "longitude": null, "shutter_speed": 0.0004940711462450593, "camera_make": "Apple", "camera_model": "iPhone 6s", "codec": null, "lens_model": "iPhone 6s back camera 4.15mm f/2.2"}}"""
DATABASE_VERSION1 = "tests/export_db_version1.db"


def test_export_db():
    """test ExportDB"""
    import os
    import tempfile

    from osxphotos.export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDB

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)
    assert db.was_created
    assert not db.was_upgraded
    assert db.version == OSXPHOTOS_EXPORTDB_VERSION

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    db.set_uuid_for_file(filepath, "FOO-BAR")
    # filename should be case-insensitive
    assert db.get_uuid_for_file(filepath_lower) == "FOO-BAR"
    db.set_info_for_uuid("FOO-BAR", INFO_DATA)
    assert db.get_info_for_uuid("FOO-BAR") == INFO_DATA
    db.set_exifdata_for_file(filepath, EXIF_DATA)
    assert db.get_exifdata_for_file(filepath) == EXIF_DATA
    db.set_stat_orig_for_file(filepath, (1, 2, 3))
    assert db.get_stat_orig_for_file(filepath) == (1, 2, 3)
    db.set_stat_exif_for_file(filepath, (4, 5, 6))
    assert db.get_stat_exif_for_file(filepath) == (4, 5, 6)
    db.set_stat_edited_for_file(filepath, (10, 11, 12))
    assert db.get_stat_edited_for_file(filepath) == (10, 11, 12)
    db.set_stat_converted_for_file(filepath, (7, 8, 9))
    assert db.get_stat_converted_for_file(filepath) == (7, 8, 9)
    db.set_sidecar_for_file(filepath, SIDECAR_DATA, (13, 14, 15))
    assert db.get_sidecar_for_file(filepath) == (SIDECAR_DATA, (13, 14, 15))
    assert db.get_previous_uuids() == ["FOO-BAR"]

    db.set_detected_text_for_uuid("FOO-BAR", json.dumps([["foo", 0.5]]))
    assert json.loads(db.get_detected_text_for_uuid("FOO-BAR")) == [["foo", 0.5]]

    # test set_data which sets all at the same time
    filepath2 = os.path.join(tempdir.name, "test2.jpg")
    db.set_data(
        filepath2,
        "BAR-FOO",
        (1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        (10, 11, 12),
        INFO_DATA,
        EXIF_DATA,
    )
    assert db.get_uuid_for_file(filepath2) == "BAR-FOO"
    assert db.get_info_for_uuid("BAR-FOO") == INFO_DATA
    assert db.get_exifdata_for_file(filepath2) == EXIF_DATA
    assert db.get_stat_orig_for_file(filepath2) == (1, 2, 3)
    assert db.get_stat_exif_for_file(filepath2) == (4, 5, 6)
    assert db.get_stat_converted_for_file(filepath2) == (7, 8, 9)
    assert db.get_stat_edited_for_file(filepath2) == (10, 11, 12)
    assert sorted(db.get_previous_uuids()) == (["BAR-FOO", "FOO-BAR"])

    # test set_data value=None doesn't overwrite existing data
    db.set_data(
        filepath2,
        "BAR-FOO",
        None,
        None,
        None,
        None,
        None,
        None,
    )
    assert db.get_uuid_for_file(filepath2) == "BAR-FOO"
    assert db.get_info_for_uuid("BAR-FOO") == INFO_DATA
    assert db.get_exifdata_for_file(filepath2) == EXIF_DATA
    assert db.get_stat_orig_for_file(filepath2) == (1, 2, 3)
    assert db.get_stat_exif_for_file(filepath2) == (4, 5, 6)
    assert db.get_stat_converted_for_file(filepath2) == (7, 8, 9)
    assert db.get_stat_edited_for_file(filepath2) == (10, 11, 12)
    assert sorted(db.get_previous_uuids()) == (["BAR-FOO", "FOO-BAR"])

    # close and re-open
    db.close()
    db = ExportDB(dbname, tempdir.name)
    assert not db.was_created
    assert db.get_uuid_for_file(filepath2) == "BAR-FOO"
    assert db.get_info_for_uuid("BAR-FOO") == INFO_DATA
    assert db.get_exifdata_for_file(filepath2) == EXIF_DATA
    assert db.get_stat_orig_for_file(filepath2) == (1, 2, 3)
    assert db.get_stat_exif_for_file(filepath2) == (4, 5, 6)
    assert db.get_stat_converted_for_file(filepath2) == (7, 8, 9)
    assert db.get_stat_edited_for_file(filepath2) == (10, 11, 12)
    assert sorted(db.get_previous_uuids()) == (["BAR-FOO", "FOO-BAR"])
    assert json.loads(db.get_detected_text_for_uuid("FOO-BAR")) == [["foo", 0.5]]

    # update data
    db.set_uuid_for_file(filepath, "FUBAR")
    assert db.get_uuid_for_file(filepath) == "FUBAR"
    assert sorted(db.get_previous_uuids()) == (["BAR-FOO", "FUBAR"])


def test_export_db_no_op():
    """test ExportDBNoOp"""
    import os
    import tempfile

    from osxphotos.export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDBNoOp

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    db = ExportDBNoOp()
    assert db.was_created
    assert not db.was_upgraded
    assert db.version == OSXPHOTOS_EXPORTDB_VERSION

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    db.set_uuid_for_file(filepath, "FOO-BAR")
    # filename should be case-insensitive
    assert db.get_uuid_for_file(filepath_lower) is None
    db.set_info_for_uuid("FOO-BAR", INFO_DATA)
    assert db.get_info_for_uuid("FOO-BAR") is None
    db.set_exifdata_for_file(filepath, EXIF_DATA)
    assert db.get_exifdata_for_file(filepath) is None
    db.set_stat_orig_for_file(filepath, (1, 2, 3))
    assert db.get_stat_orig_for_file(filepath) is None
    db.set_stat_exif_for_file(filepath, (4, 5, 6))
    assert db.get_stat_exif_for_file(filepath) is None
    db.set_stat_converted_for_file(filepath, (7, 8, 9))
    assert db.get_stat_converted_for_file(filepath) is None
    db.set_stat_edited_for_file(filepath, (10, 11, 12))
    assert db.get_stat_edited_for_file(filepath) is None
    db.set_sidecar_for_file(filepath, SIDECAR_DATA, (13, 14, 15))
    assert db.get_sidecar_for_file(filepath) == (None, (None, None, None))
    assert db.get_previous_uuids() == []

    db.set_detected_text_for_uuid("FOO-BAR", json.dumps([["foo", 0.5]]))
    assert db.get_detected_text_for_uuid("FOO-BAR") is None

    # test set_data which sets all at the same time
    filepath2 = os.path.join(tempdir.name, "test2.jpg")
    db.set_data(
        filepath2,
        "BAR-FOO",
        (1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        (10, 11, 12),
        INFO_DATA,
        EXIF_DATA,
    )
    assert db.get_uuid_for_file(filepath2) is None
    assert db.get_info_for_uuid("BAR-FOO") is None
    assert db.get_exifdata_for_file(filepath2) is None
    assert db.get_stat_orig_for_file(filepath2) is None
    assert db.get_stat_exif_for_file(filepath2) is None
    assert db.get_stat_converted_for_file(filepath) is None
    assert db.get_stat_edited_for_file(filepath) is None
    assert db.get_previous_uuids() == []

    # update data
    db.set_uuid_for_file(filepath, "FUBAR")
    assert db.get_uuid_for_file(filepath) is None


def test_export_db_in_memory():
    """test ExportDBInMemory"""
    import os
    import tempfile

    from osxphotos.export_db import (
        OSXPHOTOS_EXPORTDB_VERSION,
        ExportDB,
        ExportDBInMemory,
    )

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dbname = os.path.join(tempdir.name, ".osxphotos_export.db")
    db = ExportDB(dbname, tempdir.name)
    assert os.path.isfile(dbname)

    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    db.set_uuid_for_file(filepath, "FOO-BAR")
    db.set_info_for_uuid("FOO-BAR", INFO_DATA)
    db.set_exifdata_for_file(filepath, EXIF_DATA)
    db.set_stat_orig_for_file(filepath, (1, 2, 3))
    db.set_stat_exif_for_file(filepath, (4, 5, 6))
    db.set_stat_converted_for_file(filepath, (7, 8, 9))
    db.set_stat_edited_for_file(filepath, (10, 11, 12))
    db.set_sidecar_for_file(filepath, SIDECAR_DATA, (13, 14, 15))
    assert db.get_previous_uuids() == ["FOO-BAR"]
    db.set_detected_text_for_uuid("FOO-BAR", json.dumps([["foo", 0.5]]))

    db.close()

    dbram = ExportDBInMemory(dbname, tempdir.name)
    assert not dbram.was_created
    assert not dbram.was_upgraded
    assert dbram.version == OSXPHOTOS_EXPORTDB_VERSION

    # verify values as expected
    assert dbram.get_uuid_for_file(filepath_lower) == "FOO-BAR"
    assert dbram.get_info_for_uuid("FOO-BAR") == INFO_DATA
    assert dbram.get_exifdata_for_file(filepath) == EXIF_DATA
    assert dbram.get_stat_orig_for_file(filepath) == (1, 2, 3)
    assert dbram.get_stat_exif_for_file(filepath) == (4, 5, 6)
    assert dbram.get_stat_converted_for_file(filepath) == (7, 8, 9)
    assert dbram.get_stat_edited_for_file(filepath) == (10, 11, 12)
    assert dbram.get_sidecar_for_file(filepath) == (SIDECAR_DATA, (13, 14, 15))
    assert dbram.get_previous_uuids() == ["FOO-BAR"]
    assert json.loads(dbram.get_detected_text_for_uuid("FOO-BAR")) == [["foo", 0.5]]

    # change a value
    dbram.set_uuid_for_file(filepath, "FUBAR")
    dbram.set_info_for_uuid("FUBAR", INFO_DATA2)
    dbram.set_exifdata_for_file(filepath, EXIF_DATA2)
    dbram.set_stat_orig_for_file(filepath, (7, 8, 9))
    dbram.set_stat_exif_for_file(filepath, (10, 11, 12))
    dbram.set_stat_converted_for_file(filepath, (1, 2, 3))
    dbram.set_stat_edited_for_file(filepath, (4, 5, 6))
    dbram.set_sidecar_for_file(filepath, "FUBAR", (20, 21, 22))
    dbram.set_detected_text_for_uuid("FUBAR", json.dumps([["bar", 0.5]]))

    assert dbram.get_uuid_for_file(filepath_lower) == "FUBAR"
    assert dbram.get_info_for_uuid("FUBAR") == INFO_DATA2
    assert dbram.get_exifdata_for_file(filepath) == EXIF_DATA2
    assert dbram.get_stat_orig_for_file(filepath) == (7, 8, 9)
    assert dbram.get_stat_exif_for_file(filepath) == (10, 11, 12)
    assert dbram.get_stat_converted_for_file(filepath) == (1, 2, 3)
    assert dbram.get_stat_edited_for_file(filepath) == (4, 5, 6)
    assert dbram.get_sidecar_for_file(filepath) == ("FUBAR", (20, 21, 22))
    assert dbram.get_previous_uuids() == ["FUBAR"]
    assert json.loads(dbram.get_detected_text_for_uuid("FUBAR")) == [["bar", 0.5]]

    dbram.close()

    # re-open on disk and verify no changes
    db = ExportDB(dbname, tempdir.name)
    assert db.get_uuid_for_file(filepath_lower) == "FOO-BAR"
    assert db.get_info_for_uuid("FOO-BAR") == INFO_DATA
    assert db.get_exifdata_for_file(filepath) == EXIF_DATA
    assert db.get_stat_orig_for_file(filepath) == (1, 2, 3)
    assert db.get_stat_exif_for_file(filepath) == (4, 5, 6)
    assert db.get_stat_converted_for_file(filepath) == (7, 8, 9)
    assert db.get_stat_edited_for_file(filepath) == (10, 11, 12)
    assert db.get_sidecar_for_file(filepath) == (SIDECAR_DATA, (13, 14, 15))
    assert db.get_previous_uuids() == ["FOO-BAR"]

    assert db.get_info_for_uuid("FUBAR") is None
    assert db.get_detected_text_for_uuid("FUBAR") is None


def test_export_db_in_memory_nofile():
    """test ExportDBInMemory with no dbfile"""
    import os
    import tempfile

    from osxphotos.export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDBInMemory

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    filepath = os.path.join(tempdir.name, "test.JPG")
    filepath_lower = os.path.join(tempdir.name, "test.jpg")

    dbram = ExportDBInMemory(
        os.path.join(tempdir.name, "NOT_A_DATABASE_FILE.db"), tempdir.name
    )
    assert dbram.was_created
    assert not dbram.was_upgraded
    assert dbram.version == OSXPHOTOS_EXPORTDB_VERSION

    # change a value
    dbram.set_uuid_for_file(filepath, "FUBAR")
    dbram.set_info_for_uuid("FUBAR", INFO_DATA2)
    dbram.set_exifdata_for_file(filepath, EXIF_DATA2)
    dbram.set_stat_orig_for_file(filepath, (7, 8, 9))
    dbram.set_stat_exif_for_file(filepath, (10, 11, 12))
    dbram.set_stat_converted_for_file(filepath, (1, 2, 3))
    dbram.set_stat_edited_for_file(filepath, (4, 5, 6))
    dbram.set_sidecar_for_file(filepath, "FUBAR", (20, 21, 22))
    dbram.set_detected_text_for_uuid("FUBAR", json.dumps([["bar", 0.5]]))

    assert dbram.get_uuid_for_file(filepath_lower) == "FUBAR"
    assert dbram.get_info_for_uuid("FUBAR") == INFO_DATA2
    assert dbram.get_exifdata_for_file(filepath) == EXIF_DATA2
    assert dbram.get_stat_orig_for_file(filepath) == (7, 8, 9)
    assert dbram.get_stat_exif_for_file(filepath) == (10, 11, 12)
    assert dbram.get_stat_converted_for_file(filepath) == (1, 2, 3)
    assert dbram.get_stat_edited_for_file(filepath) == (4, 5, 6)
    assert dbram.get_sidecar_for_file(filepath) == ("FUBAR", (20, 21, 22))
    assert dbram.get_previous_uuids() == ["FUBAR"]
    assert json.loads(dbram.get_detected_text_for_uuid("FUBAR")) == [["bar", 0.5]]

    dbram.close()
