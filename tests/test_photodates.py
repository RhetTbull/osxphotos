"""Test photodates.py"""

# Note: This must be tested with pytest --photodates as it requires a specific
# library be active in the Photos library (uses AppleScript)


import datetime
import zoneinfo

import pytest

from osxphotos.platform import is_macos
from tests.conftest import get_os_version

if not is_macos:
    pytest.skip("Skipping macOS only tests", allow_module_level=True)

from photoscript import Photo

from osxphotos.photodates import get_photo_date_added, get_photo_date_original

if int(get_os_version()[0]) < 13:
    pytest.skip("Skipping; requires macOS >= 13.0 (Ventura)", allow_module_level=True)

TEST_DATA = [
    (
        "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
        datetime.datetime(
            2019,
            7,
            4,
            16,
            24,
            1,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            827957,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
        datetime.datetime(
            2020,
            4,
            15,
            10,
            25,
            51,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)),
        ),
        datetime.datetime(
            2020,
            4,
            19,
            10,
            27,
            55,
            301814,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "1EB2B765-0765-43BA-A90C-0D0580E6172C",
        datetime.datetime(
            2018,
            9,
            28,
            16,
            9,
            33,
            22000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            757001,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "4D521201-92AC-43E5-8F7C-59BC41C37A96",
        datetime.datetime(
            2020,
            4,
            16,
            10,
            42,
            58,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)),
        ),
        datetime.datetime(
            2020,
            4,
            19,
            10,
            29,
            17,
            264402,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
        datetime.datetime(
            2020,
            9,
            19,
            14,
            36,
            26,
            719000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)),
        ),
        datetime.datetime(
            2020,
            9,
            25,
            8,
            19,
            49,
            647434,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
        datetime.datetime(
            2020,
            4,
            12,
            10,
            30,
            23,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)),
        ),
        datetime.datetime(
            2020,
            4,
            19,
            10,
            27,
            32,
            244626,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "8846E3E6-8AC8-4857-8448-E3D025784410",
        # IMG_1693.tif which has a bad date manually edited in the database so
        # photo.date is 1970-01-01 00:00:00 but date original is correctly set in extended attributes
        datetime.datetime(
            2020, 5, 12, 18, 47, 13, tzinfo=zoneinfo.ZoneInfo(key="America/New_York")
        ),
        datetime.datetime(
            2020,
            6,
            6,
            9,
            15,
            24,
            725564,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "DC99FBDD-7A52-4100-A5BB-344131646C30",
        datetime.datetime(
            2018,
            10,
            13,
            9,
            18,
            12,
            501000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            859624,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
        datetime.datetime(
            2019,
            4,
            15,
            14,
            40,
            24,
            86000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            735651,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
        datetime.datetime(
            2017,
            6,
            20,
            17,
            18,
            56,
            518000,
            tzinfo=datetime.timezone(datetime.timedelta(seconds=34200)),
        ),
        datetime.datetime(
            2020,
            4,
            6,
            0,
            52,
            24,
            442561,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
        datetime.datetime(
            2020,
            4,
            16,
            12,
            28,
            21,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200)),
        ),
        datetime.datetime(
            2020,
            4,
            19,
            10,
            30,
            44,
            297306,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
        datetime.datetime(
            2018,
            9,
            28,
            15,
            39,
            59,
            8000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            9,
            8,
            28,
            312111,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        datetime.datetime(
            2018,
            9,
            28,
            15,
            35,
            49,
            63000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            804603,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
        datetime.datetime(
            2018,
            9,
            28,
            16,
            7,
            7,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        datetime.datetime(
            2019,
            7,
            27,
            8,
            16,
            49,
            778432,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
]


@pytest.mark.photodates
@pytest.mark.parametrize("uuid, _, date_added", TEST_DATA)
@pytest.mark.usefixtures("set_tz_central")
def test_get_photo_date_added(uuid, _, date_added):
    photo = Photo(uuid)
    assert get_photo_date_added(photo) == date_added


@pytest.mark.photodates
@pytest.mark.parametrize("uuid, date, _", TEST_DATA)
@pytest.mark.usefixtures("set_tz_central")
def test_get_photo_date_original(uuid, date, _):
    photo = Photo(uuid)
    # test that the date is within a second of the expected date
    # there appears to be a bug in Photos in that the fractional seconds in the extended attributes
    # is shifted from the date stored in ZASSET.ZDATECREATED
    # e.g. 0.630000 in the extended attributes is 0.063000 in ZASSET.ZDATECREATED
    assert get_photo_date_original(photo) - date < datetime.timedelta(seconds=1)
