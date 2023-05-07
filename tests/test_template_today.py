import datetime

import pytest

import osxphotos
from osxphotos.phototemplate import RenderOptions

from .locale_util import setlocale

PHOTOS_DB_PLACES = (
    "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"
)

DATETIME_TODAY = datetime.datetime(2020, 6, 21, 13, 0, 0)
""" Used to patch osxphotos.phototemplate.TODAY for testing """

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "1_1_2": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2_1_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "0_2_0": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "folder_album_1": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "folder_album_no_folder": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "mojave_album_1": "15uNd7%8RguTEgNPKHfTWw",
}

TODAY_VALUES = {
    "{today}": "2020-06-21",
    "{today.date}": "2020-06-21",
    "{today.year}": "2020",
    "{today.yy}": "20",
    "{today.mm}": "06",
    "{today.month}": "June",
    "{today.mon}": "Jun",
    "{today.dd}": "21",
    "{today.dow}": "Sunday",
    "{today.doy}": "173",
    "{today.hour}": "13",
    "{today.min}": "00",
    "{today.sec}": "00",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)


def test_subst_today(photosdb):
    """Test that substitutions are correct for {today.x}"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    photo_template = osxphotos.PhotoTemplate(photo)
    photo_template.today = DATETIME_TODAY

    options = RenderOptions()
    for template in TODAY_VALUES:
        rendered, _ = photo_template.render(template, options)
        assert rendered[0] == TODAY_VALUES[template]


def test_subst_strftime_today(photosdb):
    """Test that strftime substitutions are correct for {today.strftime}"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    photo_template = osxphotos.PhotoTemplate(photo)
    photo_template.today = DATETIME_TODAY
    options = RenderOptions()
    rendered, unmatched = photo_template.render(
        "{today.strftime,%Y-%m-%d-%H%M%S}", options
    )
    assert rendered[0] == "2020-06-21-130000"

    rendered, unmatched = photo.render_template("{today.strftime}")
    assert rendered[0] == "_"
