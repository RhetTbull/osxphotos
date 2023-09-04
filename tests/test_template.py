""" Test template.py """
import os
import re

import pytest

import osxphotos
from osxphotos.exiftool import get_exiftool_path
from osxphotos.export_db import ExportDBInMemory
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.phototemplate import (
    PUNCTUATION,
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
    PhotoTemplate,
    RenderOptions,
)
from osxphotos.platform import is_macos

from .locale_util import setlocale
from .photoinfo_mock import PhotoInfoMock

try:
    exiftool = get_exiftool_path()
except:
    exiftool = None

PHOTOS_DB_PLACES = (
    "./tests/Test-Places-Catalina-10_15_7.photoslibrary/database/photos.db"
)
PHOTOS_DB_15_7 = "./tests/Test-10.15.7.photoslibrary/database/photos.db"
PHOTOS_DB_14_6 = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_COMMENTS = "tests/Test-Cloud-10.15.6.photoslibrary"
PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.15.6.photoslibrary/database/photos.db"
PHOTOS_DB_PROJECTS = "./tests/Test-iPhoto-Projects-10.15.7.photoslibrary"

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "1_1_2": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2_1_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "0_2_0": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "folder_album_1": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "folder_album_no_folder": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "mojave_album_1": "15uNd7%8RguTEgNPKHfTWw",
    "date_modified": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
    "date_not_modified": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "favorite": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
}

UUID_MEDIA_TYPE = {
    "photo": "C2BBC7A4-5333-46EE-BAF0-093E72111B39",
    "video": "45099D34-A414-464F-94A2-60D6823679C8",
    "selfie": "080525C4-1F05-48E5-A3F4-0C53127BB39C",
    "time_lapse": "4614086E-C797-4876-B3B9-3057E8D757C9",
    "panorama": "1C1C8F1F-826B-4A24-B1CB-56628946A834",
    "slow_mo": None,
    "screenshot": None,
    "portrait": "7CDA5F84-AA16-4D28-9AA6-A49E1DF8A332",
    "live_photo": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "burst": None,
}

# multi keywords
UUID_MULTI_KEYWORDS = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"
TEMPLATE_VALUES_MULTI_KEYWORDS = {
    "{keyword}": ["flowers", "wedding"],
    "{keyword|parens}": ["(flowers)", "(wedding)"],
    "{keyword|braces}": ["{flowers}", "{wedding}"],
    "{keyword|brackets}": ["[flowers]", "[wedding]"],
    "{keyword|parens|brackets|capitalize}": ["[(flowers)]", "[(wedding)]"],
    "{keyword|capitalize|parens|brackets}": ["[(Flowers)]", "[(Wedding)]"],
    "{keyword|upper}": ["FLOWERS", "WEDDING"],
    "{keyword|lower}": ["flowers", "wedding"],
    "{keyword|titlecase}": ["Flowers", "Wedding"],
    "{keyword|capitalize}": ["Flowers", "Wedding"],
    "{keyword|shell_quote}": ["flowers", "wedding"],
    "{var:kw,{keyword|sort}}{%kw|join(,)}": ["flowers,wedding"],
    "{var:kw,{keyword|sort}}{%kw|titlecase|join(;)}": ["Flowers;Wedding"],
    "{,+keyword}": ["flowers,wedding"],  # test keywords in sorted order
    "{,+keyword|titlecase}": ["Flowers,Wedding"],  # test keywords in sorted order
    "{,+keyword|upper}": ["FLOWERS,WEDDING"],  # test keywords in sorted order
    "{keyword|appends(:keyword)}": ["flowers:keyword", "wedding:keyword"],
    "{keyword|prepends(keyword:)}": ["keyword:flowers", "keyword:wedding"],
}

UUID_TITLE = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"
TEMPLATE_VALUES_TITLE = {
    "{title}": ["Tulips tied together at a flower shop"],
    "{title|appends(:title)}": ["Tulips tied together at a flower shop:title"],
    "{title|prepends(title:)}": ["title:Tulips tied together at a flower shop"],
    "{title|titlecase}": ["Tulips Tied Together At A Flower Shop"],
    "{title|upper}": ["TULIPS TIED TOGETHER AT A FLOWER SHOP"],
    "{title|titlecase|lower|upper}": ["TULIPS TIED TOGETHER AT A FLOWER SHOP"],
    "{title|titlecase|lower|upper|shell_quote}": [
        "'TULIPS TIED TOGETHER AT A FLOWER SHOP'"
    ],
    "{title|upper|titlecase}": ["Tulips Tied Together At A Flower Shop"],
    "{title|capitalize}": ["Tulips tied together at a flower shop"],
    "{title[ ,_]}": ["Tulips_tied_together_at_a_flower_shop"],
    "{title[ ,_|e,]}": ["Tulips_tid_togthr_at_a_flowr_shop"],
    "{title[ ,|e,]}": ["Tulipstidtogthrataflowrshop"],
    "{title[e,]}": ["Tulips tid togthr at a flowr shop"],
    "{+title}": ["Tulips tied together at a flower shop"],
    "{,+title}": ["Tulips tied together at a flower shop"],
    "{, +title}": ["Tulips tied together at a flower shop"],
    "{title|shell_quote}": ["'Tulips tied together at a flower shop'"],
}

# Boolean type values that render to True
UUID_BOOL_VALUES = {
    "hdr": "D11D25FF-5F31-47D2-ABA9-58418878DC15",
    "edited": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "edited_version": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
}

# Boolean type values that render to False
UUID_BOOL_VALUES_NOT = {
    "hdr": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "edited_version": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "edited": "CCBE0EB9-AE9F-4479-BFFD-107042C75227",
}

# for exiftool template
UUID_EXIFTOOL = {
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": {
        "{exiftool:EXIF:Make}": ["Canon"],
        "{exiftool:EXIF:Make[Canon,CANON]}": ["CANON"],
        "{exiftool:EXIF:Model}": ["Canon PowerShot G10"],
        "{exiftool:EXIF:Model[ G10,]}": ["Canon PowerShot"],
        "{exiftool:EXIF:Make}/{exiftool:EXIF:Model}": ["Canon/Canon PowerShot G10"],
        "{exiftool:IPTC:Keywords,foo}": ["foo"],
    },
    "DC99FBDD-7A52-4100-A5BB-344131646C30": {
        "{exiftool:IPTC:Keywords}": [
            "England",
            "London",
            "London 2018",
            "St. James's Park",
            "UK",
            "United Kingdom",
        ],
        "{exiftool:IPTC:Keywords[ ,_|.,]}": [
            "England",
            "London",
            "London_2018",
            "St_James's_Park",
            "UK",
            "United_Kingdom",
        ],
        "{exiftool:IPTC:Keywords[ ,_|.,|L,]}": [
            "England",
            "ondon",
            "ondon_2018",
            "St_James's_Park",
            "UK",
            "United_Kingdom",
        ],
        "{,+exiftool:IPTC:Keywords}": [
            "England,London,London 2018,St. James's Park,UK,United Kingdom"
        ],
    },
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": {
        "{exiftool:EXIF:SubSecTimeOriginal}": ["22"]
    },
}

TEMPLATE_VALUES = {
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{original_name[_,-]}": "IMG-1064",
    "{title}": "Glen Ord",
    "{title[ ,]}": "GlenOrd",
    "{descr}": "Jack Rose Dining Saloon",
    "{created}": "2020-02-04",
    "{created.date}": "2020-02-04",
    "{created.year}": "2020",
    "{created.yy}": "20",
    "{created.mm}": "02",
    "{created.month}": "February",
    "{created.mon}": "Feb",
    "{created.dd}": "04",
    "{created.dow}": "Tuesday",
    "{created.doy}": "035",
    "{created.hour}": "19",
    "{created.min}": "07",
    "{created.sec}": "38",
    "{place.name}": "Washington, District of Columbia, United States",
    "{place.country_code}": "US",
    "{place.name.country}": "United States",
    "{place.name.state_province}": "District of Columbia",
    "{place.name.city}": "Washington",
    "{place.name.area_of_interest}": "_",
    "{place.address}": "2038 18th St NW, Washington, DC  20009, United States",
    "{place.address.street}": "2038 18th St NW",
    "{place.address.city}": "Washington",
    "{place.address.state_province}": "DC",
    "{place.address.postal_code}": "20009",
    "{place.address.country}": "United States",
    "{place.address.country_code}": "US",
    "{uuid}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{shortuuid}": "5KFgrKKnwmnN99jkHmJP8M",
    "{shortuuid|sslice(:7)}": "5KFgrKK",
    "{exif.camera_make}": "Apple",
    "{exif.camera_model}": "iPhone 6s",
    "{exif.lens_model}": "iPhone 6s back camera 4.15mm f/2.2",
    "{album?{folder_album},{created.year}/{created.mm}}": "2020/02",
    "{title?Title is '{title} - {descr}',No Title}": "Title is 'Glen Ord - Jack Rose Dining Saloon'",
    "{favorite}": "_",
    "{favorite?FAV,NOTFAV}": "NOTFAV",
    "{var:myvar,{semicolon}}{created.dow}{%myvar}": "Tuesday;",
    "{var:pipe,{pipe}}{place.address[,,%pipe]}": "2038 18th St NW| Washington| DC  20009| United States",
    "{format:float:.2f,{photo.exif_info.aperture}}": "2.20",
    "{format:int:02d,{photo.exif_info.aperture}}": "02",
    "{format:int:03d,{photo.exif_info.aperture}}": "002",
    "{format:float:10.4f,{photo.exif_info.aperture}}": "    2.2000",
    "{format:str:-^10,{photo.exif_info.aperture}}": "---2.2----",
    "{descr|lower}": "jack rose dining saloon",
    "{descr|upper}": "JACK ROSE DINING SALOON",
    "{var:spaces,  {descr}}{%spaces|strip,}": "Jack Rose Dining Saloon",
    "{descr|titlecase}": "Jack Rose Dining Saloon",
    "{descr|capitalize}": "Jack rose dining saloon",
    "{descr|braces}": "{Jack Rose Dining Saloon}",
    "{descr|parens}": "(Jack Rose Dining Saloon)",
    "{descr|brackets}": "[Jack Rose Dining Saloon]",
    "{descr|split( )|join(|)}": "Jack|Rose|Dining|Saloon",
    "{descr|autosplit|join(|)}": "Jack|Rose|Dining|Saloon",
    "{descr|autosplit|join()}": "JackRoseDiningSaloon",
    "{descr|autosplit|chop(1)|join(|)}": "Jac|Ros|Dinin|Saloo",
    "{descr|autosplit|chomp(1)|join(|)}": "ack|ose|ining|aloon",
    "{descr|chop(2)}": "Jack Rose Dining Salo",
    "{descr|chomp(2)}": "ck Rose Dining Saloon",
    "{descr|autosplit|sort|join(|)}": "Dining|Jack|Rose|Saloon",
    "{descr|autosplit|rsort|join(|)}": "Saloon|Rose|Jack|Dining",
    "{descr|autosplit|reverse|join(|)}": "Saloon|Dining|Rose|Jack",
    "{var:myvar,a e a b d c c d e}{%myvar|autosplit|uniq|sort|join(,)}": "a,b,c,d,e",
    "{descr|chop(6)|autosplit|append(Restaurant)|join( )}": "Jack Rose Dining Restaurant",
    "{descr|chomp(4)|autosplit|prepend(Mack)|join( )}": "Mack Rose Dining Saloon",
    "{descr|autosplit|remove(Rose)|join( )}": "Jack Dining Saloon",
    "{descr|sslice(0:3)}": "Jac",
    "{descr|sslice(5:11)}": "Rose D",
    "{descr|sslice(:-6)}": "Jack Rose Dining ",
    "{descr|sslice(::2)}": "Jc oeDnn aon",
    "{descr|autosplit|slice(1:3)|join()}": "RoseDining",
    "{descr|autosplit|slice(2:)|join()}": "DiningSaloon",
    "{descr|autosplit|slice(:2)|join()}": "JackRose",
    "{descr|autosplit|slice(:-1)|join()}": "JackRoseDining",
    "{descr|autosplit|slice(::2)|join()}": "JackDining",
    "{descr|filter(startswith Jack)}": "Jack Rose Dining Saloon",
    "{descr|filter(startswith Rose)}": "_",
    "{descr|filter(endswith Saloon)}": "Jack Rose Dining Saloon",
    "{descr|filter(endswith Rose)}": "_",
    "{descr|filter(contains Rose)}": "Jack Rose Dining Saloon",
    "{descr|filter(not contains Rose)}": "_",
    "{descr|filter(matches Jack Rose Dining Saloon)}": "Jack Rose Dining Saloon",
    "{created.mm|filter(== 02)}": "02",
    "{created.mm|filter(<= 2)}": "02",
    "{created.mm|filter(>= 2)}": "02",
    "{created.mm|filter(> 3)}": "_",
    "{created.mm|filter(< 1)}": "_",
    "{created.mm|filter(!= 02)}": "_",
    "{created.mm|int|filter(== 2)}": "2",
    "{created.mm|float|filter(== 2.0)}": "2.0",
}


TEMPLATE_VALUES_DEU = {
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{title}": "Glen Ord",
    "{descr}": "Jack Rose Dining Saloon",
    "{created.date}": "2020-02-04",
    "{created.year}": "2020",
    "{created.yy}": "20",
    "{created.mm}": "02",
    "{created.month}": "Februar",
    "{created.mon}": "Feb",
    "{created.dd}": "04",
    "{created.doy}": "035",
    "{created.dow}": "Dienstag",
    "{place.name}": "Washington, District of Columbia, United States",
    "{place.country_code}": "US",
    "{place.name.country}": "United States",
    "{place.name.state_province}": "District of Columbia",
    "{place.name.city}": "Washington",
    "{place.name.area_of_interest}": "_",
    "{place.address}": "2038 18th St NW, Washington, DC  20009, United States",
    "{place.address.street}": "2038 18th St NW",
    "{place.address.city}": "Washington",
    "{place.address.state_province}": "DC",
    "{place.address.postal_code}": "20009",
    "{place.address.country}": "United States",
    "{place.address.country_code}": "US",
}

TEMPLATE_VALUES_DATE_MODIFIED = {
    "{name}": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
    "{original_name}": "IMG_3984",
    "{modified}": "2020-10-31",
    "{modified.date}": "2020-10-31",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "10",
    "{modified.month}": "October",
    "{modified.mon}": "Oct",
    "{modified.dd}": "31",
    "{modified.doy}": "305",
    "{modified.dow}": "Saturday",
    "{modified.strftime,%Y-%m-%d-%H%M%S}": "2020-10-31-080321",
    "{modified.strftime}": "_",
}

TEMPLATE_VALUES_DATE_NOT_MODIFIED = {
    # uses creation date instead of modified date
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{modified.date}": "2020-02-04",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "02",
    "{modified.month}": "February",
    "{modified.mon}": "Feb",
    "{modified.dd}": "04",
    "{modified.dow}": "Tuesday",
    "{modified.doy}": "035",
    "{modified.hour}": "19",
    "{modified.min}": "07",
    "{modified.sec}": "38",
    "{modified.strftime,%Y-%m-%d-%H%M%S}": "2020-02-04-190738",
}

UUID_DETECTED_TEXT = "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91"
TEMPLATE_VALUES_DETECTED_TEXT = {
    "{detected_text}": " ",
    "{;+detected_text:0.5}": " ",
}

COMMENT_UUID_DICT = {
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE": [
        "Rhet Turnbull: Nice photo!",
        "None: Wish I was back here!",
    ],
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": ["_"],
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB": ["None: Nice trophy"],
}

UUID_PHOTO = {
    "DC99FBDD-7A52-4100-A5BB-344131646C30": {
        "{photo.title}": ["St. James's Park"],
        "{photo.favorite?FAVORITE,NOTFAVORITE}": ["NOTFAVORITE"],
        "{photo.hdr}": ["_"],
        "{photo.keywords}": [
            "England",
            "London",
            "London 2018",
            "St. James's Park",
            "UK",
            "United Kingdom",
        ],
        "{photo.keywords|lower}": [
            "england",
            "london",
            "london 2018",
            "st. james's park",
            "uk",
            "united kingdom",
        ],
    },
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": {"{photo.place.country_code}": ["AU"]},
    "F12384F6-CD17-4151-ACBA-AE0E3688539E": {"{photo.place.name}": ["_"]},
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {"{photo.favorite}": ["favorite"]},
}

UUID_CONDITIONAL = {
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": {
        "{title matches Elder Park?YES,NO}": ["YES"],
        "{title matches not Elder Park?YES,NO}": ["NO"],
        "{title contains Park?YES,NO}": ["YES"],
        "{title not contains Park?YES,NO}": ["NO"],
        "{title matches Park?YES,NO}": ["NO"],
        "{title == Elder Park?YES,NO}": ["YES"],
        "{title != Elder Park?YES,NO}": ["NO"],
        "{title[ ,] == ElderPark?YES,NO}": ["YES"],
        "{title not != Elder Park?YES,NO}": ["YES"],
        "{title not == Elder Park?YES,NO}": ["NO"],
        "{title endswith Park?YES,NO}": ["YES"],
        "{title endswith Elder?YES,NO}": ["NO"],
        "{title startswith Elder?YES,NO}": ["YES"],
        "{title startswith Elder|endswith Park?YES,NO}": ["YES"],
        "{photo.place.name contains Adelaide?YES,NO}": ["YES"],
        "{photo.place.name|lower contains adelaide?YES,NO}": ["YES"],
        "{photo.place.name|lower contains adelaide|australia?YES,NO}": ["YES"],
        "{photo.place.name|lower not contains adelaide?YES,NO}": ["NO"],
        "{photo.score.overall < 0.7?YES,NO}": ["YES"],
        "{photo.score.overall <= 0.7?YES,NO}": ["YES"],
        "{photo.score.overall > 0.7?YES,NO}": ["NO"],
        "{photo.score.overall >= 0.7?YES,NO}": ["NO"],
        "{photo.score.overall not < 0.7?YES,NO}": ["NO"],
        "{folder_album(-) contains Folder1-SubFolder2-AlbumInFolder?YES,NO}": ["YES"],
        "{folder_album( - ) contains Folder1 - SubFolder2 - AlbumInFolder?YES,NO}": [
            "YES"
        ],
        "{folder_album(-)[In,] contains Folder1-SubFolder2-AlbumFolder?YES,NO}": [
            "YES"
        ],
    },
    "DC99FBDD-7A52-4100-A5BB-344131646C30": {
        "{keyword == {keyword}?YES,NO}": ["YES"],
        "{keyword contains England?YES,NO}": ["YES"],
        "{keyword contains Eng?YES,NO}": ["YES"],
        "{keyword contains Foo?YES,NO}": ["NO"],
        "{keyword matches England?YES,NO}": ["YES"],
        "{keyword matches Eng?YES,NO}": ["NO"],
        "{keyword contains Foo|Bar|England?YES,NO}": ["YES"],
        "{keyword contains Foo|Bar?YES,NO}": ["NO"],
        "{keyword matches Foo|Bar|England?YES,NO}": ["YES"],
        "{keyword matches Foo|Bar?YES,NO}": ["NO"],
    },
}

UUID_ALBUM_SEQ = {
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": {
        "album": "/Sorted Manual",
        "templates": {
            "{album_seq}": "0",
            "{album_seq:02d}": "00",
            "{album_seq(1)}": "1",
            "{album_seq(2)}": "2",
            "{album_seq:03d(1)}": "001",
            "{folder_album_seq}": "0",
            "{folder_album_seq:02d}": "00",
            "{folder_album_seq(1)}": "1",
            "{folder_album_seq(2)}": "2",
            "{folder_album_seq:03d(1)}": "001",
        },
    },
    "F12384F6-CD17-4151-ACBA-AE0E3688539E": {
        "album": "/Sorted Manual",
        "templates": {
            "{album_seq}": "2",
            "{album_seq:02d}": "02",
            "{album_seq(1)}": "3",
            "{album_seq:03d(1)}": "003",
            "{folder_album_seq}": "2",
            "{folder_album_seq:02d}": "02",
            "{folder_album_seq(1)}": "3",
            "{folder_album_seq:03d(1)}": "003",
        },
    },
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {
        "album": "/Folder1/SubFolder2/AlbumInFolder",
        "templates": {
            "{album_seq}": "1",
            "{album_seq:02d}": "01",
            "{album_seq(1)}": "2",
            "{album_seq:03d(1)}": "002",
            "{folder_album_seq}": "1",
            "{folder_album_seq:02d}": "01",
            "{folder_album_seq(1)}": "2",
            "{folder_album_seq(0)}": "1",
            "{folder_album_seq:03d(1)}": "002",
            "{folder_album|filter(startswith Folder1)}": "Folder1/SubFolder2/AlbumInFolder",
        },
    },
}

UUID_MOMENT = {
    "7FD37B5F-6FAA-4DB1-8A29-BF9C37E38091": {
        "templates": {
            "{moment}": ["Hawaiian Islands"],
        }
    }
}

UUID_EMPTY_TITLE = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"  # IMG_3092.heic
UUID_EMPTY_TITLE_HAS_DESCRIPTION = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
UUID_LAT_LON = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"  # IMG_3092.heic

TEMPLATE_VALUES_EMPTY_TITLE = {
    "{title,No Title} and {descr,No Descr}": "No Title and No Descr",
    "{title?true,false}": "false",
}

TEMPLATE_VALUES_EMPTY_TITLE_HAS_DESCRIPTION = {
    "{title,} {descr} ": " Bride Wedding day ",
    "{strip,{title,} {descr} }": "Bride Wedding day",
}

UUID_PROJECT = "96615063-993E-458B-A9E5-7A68C75A04B6"
TEMPLATE_VALUES_PROJECT = {
    "{project}": ["Photos Card"],
    "{album}": ["_"],
    "{album_project}": ["Photos Card"],
    "{folder_album}": ["_"],
    "{folder_album_project}": ["Photos Card"],
}

UUID_NO_PROJECT = "C4EA300F-50AD-4FCB-9173-D29B57B52BCF"
TEMPLATE_VALUES_NO_PROJECT = {"{project}": ["_"]}


@pytest.fixture(scope="module")
def photosdb_places():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_7)


@pytest.fixture(scope="module")
def photosdb_14_6():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_14_6)


@pytest.fixture(scope="module")
def photosdb_comments():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_COMMENTS)


@pytest.fixture(scope="module")
def photosdb_cloud():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_CLOUD)


@pytest.fixture(scope="module")
def photosdb_project():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_PROJECTS)


def test_lookup(photosdb_places):
    """Test that a lookup is returned for every possible value"""

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        lookup = template.get_template_value(lookup_str, None, None, None)
        assert lookup or lookup is None


def test_lookup_multi(photosdb_places):
    """Test that a lookup is returned for every possible value"""
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        if subst in ["{exiftool}", "{photo}", "{function}", "{format}"]:
            continue
        if subst == "{detected_text}" and not is_macos:
            continue
        lookup = template.get_template_value_multi(
            lookup_str,
            path_sep=os.path.sep,
            default=[],
            subfield=None,
        )
        assert isinstance(lookup, list)


def test_subst(photosdb_places):
    """Test that substitutions are correct"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES[template]


def test_subst_date_modified(photosdb_places):
    """Test that substitutions are correct for date modified"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["date_modified"]])[0]

    for template in TEMPLATE_VALUES_DATE_MODIFIED:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DATE_MODIFIED[template]


def test_subst_date_not_modified(photosdb_places):
    """Test that substitutions are correct for date modified when photo isn't modified"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["date_not_modified"]])[0]

    for template in TEMPLATE_VALUES_DATE_NOT_MODIFIED:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DATE_NOT_MODIFIED[template]


def test_subst_locale_1(photosdb_places):
    """Test that substitutions are correct in user locale"""
    import locale

    # osxphotos.template sets local on load so set the environment first
    # set locale to DE
    setlocale(locale.LC_ALL, "de_DE.UTF-8")

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_locale_2(photosdb_places):
    """Test that substitutions are correct in user locale"""
    import locale
    import os

    # Check if locale is available
    setlocale(locale.LC_ALL, "de_DE.UTF-8")

    # osxphotos.template sets local on load so set the environment first
    os.environ["LANG"] = "de_DE.UTF-8"
    os.environ["LC_COLLATE"] = "de_DE.UTF-8"
    os.environ["LC_CTYPE"] = "de_DE.UTF-8"
    os.environ["LC_MESSAGES"] = "de_DE.UTF-8"
    os.environ["LC_MONETARY"] = "de_DE.UTF-8"
    os.environ["LC_NUMERIC"] = "de_DE.UTF-8"
    os.environ["LC_TIME"] = "de_DE.UTF-8"

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_default_val(photosdb_places):
    """Test substitution with default value specified"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,UNKNOWN}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == "UNKNOWN"


def test_subst_default_val_2(photosdb_places):
    """Test substitution with ',' but no default value"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == ""


def test_subst_unknown_val(photosdb_places):
    """Test substitution with unknown value specified"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo}"
    rendered, unknown = photo.render_template(template)
    # assert rendered[0] == "2020/{foo}"
    assert unknown == ["foo"]


# def test_subst_double_brace(photosdb_places):
#     """ Test substitution with double brace {{ which should be ignored """

#     photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

#     template = "{created.year}/{{foo}}"
#     rendered, unknown = photo.render_template(template)
#     assert rendered[0] == "2020/{foo}"
#     assert not unknown


def test_subst_unknown_val_with_default(photosdb_places):
    """Test substitution with unknown value specified"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo,bar}"
    rendered, unknown = photo.render_template(template)
    # assert rendered[0] == "2020/{foo,bar}"
    assert unknown == ["foo"]


def test_subst_multi_1_1_2(photosdb):
    """Test that substitutions are correct"""
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Pumpkin Farm/Kids/Suzy"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1(photosdb):
    """Test that substitutions are correct"""
    # 2 albums, 1 keyword, 1 person

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = [
        "2018/Pumpkin Farm/Kids/Katie",
        "2018/Test Album/Kids/Katie",
        "2018/Multi Keyword/Kids/Katie",
    ]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1_single(photosdb):
    """Test that substitutions are correct"""
    # 2 albums, 1 keyword, 1 person but only do keywords

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{keyword}"
    expected = ["Kids"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0(photosdb):
    """Test that substitutions are correct"""
    # 0 albums, 2 keywords, 0 persons

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2019/_/wedding/_", "2019/_/flowers/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_single(photosdb):
    """Test that substitutions are correct"""
    # 0 albums, 2 keywords, 0 persons, but only do albums

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}"
    expected = ["2019/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val(photosdb):
    """Test that substitutions are correct"""
    # 0 albums, 2 keywords, 0 persons, default vals provided

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person,NOPERSON}"
    expected = ["2019/NOALBUM/wedding/NOPERSON", "2019/NOALBUM/flowers/NOPERSON"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val_unknown_val(photosdb):
    """Test that substitutions are correct"""
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo}/{baz}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo}/{baz}",
        "2019/NOALBUM/flowers/_/{foo}/{baz}",
    ]
    rendered, unknown = photo.render_template(template)
    # assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo", "baz"]


def test_subst_multi_0_2_0_default_val_unknown_val_2(photosdb):
    """Test that substitutions are correct"""
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo,bar}/{baz,bar}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo,bar}/{baz,bar}",
        "2019/NOALBUM/flowers/_/{foo,bar}/{baz,bar}",
    ]
    rendered, unknown = photo.render_template(template)
    # assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo", "baz"]


def test_subst_multi_folder_albums_1(photosdb):
    """Test substitutions for folder_album are correct"""

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album}"
    expected = [
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
        "2019-10/11 Paris Clermont",
        "Folder1/SubFolder2/AlbumInFolder",
        "Sorted Manual",
        "Sorted Newest First",
        "Sorted Oldest First",
        "Sorted Title",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_1_path_sep(photosdb):
    """Test substitutions for folder_album are correct with custom PATH_SEP"""

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album(:)}"
    expected = [
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
        "2019-10/11 Paris Clermont",
        "Folder1:SubFolder2:AlbumInFolder",
        "Sorted Manual",
        "Sorted Newest First",
        "Sorted Oldest First",
        "Sorted Title",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_1_path_sep_lower(photosdb):
    """Test substitutions for folder_album are correct with custom PATH_SEP"""

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album(:)|lower}"
    expected = [
        "2018-10 - sponsion, museum, frühstück, römermuseum",
        "2019-10/11 paris clermont",
        "folder1:subfolder2:albuminfolder",
        "sorted manual",
        "sorted newest first",
        "sorted oldest first",
        "sorted title",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_2(photosdb):
    """Test substitutions for folder_album are correct"""

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_no_folder"]])[0]
    template = "{folder_album}"
    expected = ["Multi Keyword", "Pumpkin Farm", "Test Album"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_2_path_sep(photosdb):
    """Test substitutions for folder_album are correct with custom PATH_SEP"""

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_no_folder"]])[0]
    template = "{folder_album(:)}"
    expected = ["Multi Keyword", "Pumpkin Farm", "Test Album"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_3(photosdb_14_6):
    """Test substitutions for folder_album on < Photos 5"""

    # photo in an album in a folder
    photo = photosdb_14_6.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album}"
    expected = ["Folder1/SubFolder2/AlbumInFolder", "Pumpkin Farm", "Test Album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_3_path_sep(photosdb_14_6):
    """Test substitutions for folder_album on < Photos 5 with custom PATH_SEP"""

    # photo in an album in a folder
    photo = photosdb_14_6.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album(>)}"
    expected = ["Folder1>SubFolder2>AlbumInFolder", "Pumpkin Farm", "Test Album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_4_path_sep_lower(photosdb_14_6):
    """Test substitutions for folder_album on < Photos 5 with custom PATH_SEP"""

    # photo in an album in a folder
    photo = photosdb_14_6.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album(>)|lower}"
    expected = ["folder1>subfolder2>albuminfolder", "pumpkin farm", "test album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_strftime(photosdb_places):
    """Test that strftime substitutions are correct"""
    import locale

    setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    rendered, unmatched = photo.render_template("{created.strftime,%Y-%m-%d-%H%M%S}")
    assert rendered[0] == "2020-02-04-190738"

    rendered, unmatched = photo.render_template("{created.strftime}")
    assert rendered[0] == "_"


def test_subst_expand_inplace_1(photosdb):
    """Test that substitutions are correct when expand_inplace=True"""

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}"
    expected = ["Katie,Suzy"]
    options = RenderOptions(expand_inplace=True)
    rendered, unknown = photo.render_template(template, options)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_2(photosdb):
    """Test that substitutions are correct when expand_inplace=True"""
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie,Suzy-Kids"]
    options = RenderOptions(expand_inplace=True)
    rendered, unknown = photo.render_template(template, options)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_3(photosdb):
    """Test that substitutions are correct when expand_inplace=True and inplace_sep specified"""
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie; Suzy-Kids"]

    options = RenderOptions(expand_inplace=True, inplace_sep="; ")
    rendered, unknown = photo.render_template(template, options)
    assert sorted(rendered) == sorted(expected)


def test_comment(photosdb_comments):
    import osxphotos

    for uuid in COMMENT_UUID_DICT:
        photo = photosdb_comments.get_photo(uuid)
        comments = photo.render_template("{comment}")
        assert comments[0] == COMMENT_UUID_DICT[uuid]


def test_media_type(photosdb_cloud):
    """test {media_type} template"""

    for field, uuid in UUID_MEDIA_TYPE.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{media_type}")
            assert rendered[0] == osxphotos.phototemplate.MEDIA_TYPE_DEFAULTS[field]


def test_media_type_default(photosdb_cloud):
    """test {media_type,photo=foo} template style"""

    for field, uuid in UUID_MEDIA_TYPE.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{media_type," + f"{field}" + "=foo}")
            assert rendered[0] == "foo"


def test_bool_values(photosdb_cloud):
    """test {bool?TRUE,FALSE} template values"""

    for field, uuid in UUID_BOOL_VALUES.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            edited = field == "edited_version"
            options = RenderOptions(edited_version=edited)
            rendered, _ = photo.render_template(
                "{" + f"{field}" + "?True,False}", options
            )
            assert rendered[0] == "True"


def test_bool_values_not(photosdb_cloud):
    """test {bool?TRUE,FALSE} template values for FALSE values"""

    for field, uuid in UUID_BOOL_VALUES_NOT.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{" + f"{field}" + "?True,False}")
            assert rendered[0] == "False"


def test_partial_match(photosdb_cloud):
    """test that template successfully rejects a field that is superset of valid field"""

    for uuid in COMMENT_UUID_DICT:
        photo = photosdb_cloud.get_photo(uuid)
        rendered, notmatched = photo.render_template("{keywords}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{keywords,}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{keywords,foo}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{,+keywords,foo}")
        assert [rendered, notmatched] == [[], ["keywords"]]


def test_expand_in_place_with_delim(photosdb):
    """Test that substitutions are correct when {DELIM+FIELD} format used"""
    import osxphotos

    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)

    for template in TEMPLATE_VALUES_MULTI_KEYWORDS:
        rendered, _ = photo.render_template(template)
        assert sorted(rendered) == sorted(TEMPLATE_VALUES_MULTI_KEYWORDS[template])


def test_expand_in_place_with_delim_single_value(photosdb):
    """Test that single-value substitutions are correct when {DELIM+FIELD} format used"""

    photo = photosdb.get_photo(UUID_TITLE)

    for template in TEMPLATE_VALUES_TITLE:
        rendered, _ = photo.render_template(template)
        assert sorted(rendered) == sorted(TEMPLATE_VALUES_TITLE[template])


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_exiftool_template(photosdb):
    for uuid in UUID_EXIFTOOL:
        photo = photosdb.get_photo(uuid)
        for template in UUID_EXIFTOOL[uuid]:
            rendered, _ = photo.render_template(template)
            assert sorted(rendered) == sorted(UUID_EXIFTOOL[uuid][template])


def test_hdr(photosdb):
    """Test hdr"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, hdr="hdr")
    rendered, _ = photomock.render_template("{hdr}")
    assert rendered == ["hdr"]


def test_edited(photosdb):
    """Test edited"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, hasadjustments=True)
    rendered, _ = photomock.render_template("{edited}")
    assert rendered == ["edited"]


def test_favorite(photosdb):
    """Test favorite"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, favorite=True)
    rendered, _ = photomock.render_template("{favorite}")
    assert rendered == ["favorite"]


def test_nested_template_bool(photosdb):
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    template = "{hdr?{edited?HDR_EDITED,HDR_NOT_EDITED},{edited?NOT_HDR_EDITED,NOT_HDR_NOT_EDITED}}"

    photomock = PhotoInfoMock(photo, hdr=True, hasadjustments=True)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["HDR_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=True, hasadjustments=False)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["HDR_NOT_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=False, hasadjustments=False)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["NOT_HDR_NOT_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=False, hasadjustments=True)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["NOT_HDR_EDITED"]


def test_nested_template(photosdb):
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, keywords=[], title="My Title")

    rendered, _ = photomock.render_template("{keyword,{title}}")
    assert rendered == ["My Title"]


def test_punctuation_1(photosdb):
    """Test punctuation template fields"""
    from osxphotos.phototemplate import PUNCTUATION

    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    for punc in PUNCTUATION:
        rendered, _ = photo.render_template("{" + punc + "}")
        assert rendered[0] == PUNCTUATION[punc]


def test_punctuation_2():
    """Test punctuation template fields"""
    template_string = ""
    expected_string = ""
    for field, value in PUNCTUATION.items():
        template_string += "{" + field + "}"
        expected_string += f"{value}"
    template = PhotoTemplate(PhotoInfoNone())
    options = RenderOptions()
    rendered, _ = template.render(template_string, options)
    assert rendered == [expected_string]


def test_photo_template(photosdb):
    for uuid in UUID_PHOTO:
        photo = photosdb.get_photo(uuid)
        for template in UUID_PHOTO[uuid]:
            rendered, _ = photo.render_template(template)
            assert sorted(rendered) == sorted(UUID_PHOTO[uuid][template])


def test_conditional(photosdb):
    for uuid in UUID_CONDITIONAL:
        photo = photosdb.get_photo(uuid)
        for template in UUID_CONDITIONAL[uuid]:
            rendered, _ = photo.render_template(template)
            assert sorted(rendered) == sorted(UUID_CONDITIONAL[uuid][template])


def test_function_hyphen_dir(photosdb):
    """Test {function} with a hyphenated directory (#477)"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    rendered, _ = photo.render_template(
        "{function:tests/hyphen-dir/template_function.py::foo}"
    )
    assert rendered == [f"{photo.original_filename}-FOO"]


def test_function(photosdb):
    """Test {function}"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    rendered, _ = photo.render_template("{function:tests/template_function.py::foo}")
    assert rendered == [f"{photo.original_filename}-FOO"]


def test_function_bad(photosdb):
    """Test invalid {function}"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    with pytest.raises(ValueError):
        rendered, _ = photo.render_template(
            "{function:tests/template_function.py::foobar}"
        )


def test_function_filter(photosdb):
    """Test {field|function} filter"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)

    rendered, _ = photo.render_template(
        "{photo.original_filename|function:tests/template_filter.py::myfilter}"
    )
    assert rendered == [f"foo-{photo.original_filename}"]

    rendered, _ = photo.render_template(
        "{photo.original_filename|lower|function:tests/template_filter.py::myfilter}"
    )
    assert rendered == [f"foo-{photo.original_filename.lower()}"]

    rendered, _ = photo.render_template(
        "{photo.original_filename|function:tests/template_filter.py::myfilter|lower}"
    )
    assert rendered == [f"foo-{photo.original_filename.lower()}"]


def test_function_filter_bad(photosdb):
    """Test invalid {field|function} filter"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    # bad field raises SyntaxError
    # bad function raises ValueError
    with pytest.raises((SyntaxError, ValueError)):
        rendered, _ = photo.render_template(
            "{photo.original_filename|function:tests/template_filter.py::foobar}"
        )


def test_export_dir():
    """Test {export_dir} template"""
    from osxphotos.photoinfo import PhotoInfoNone
    from osxphotos.phototemplate import PhotoTemplate

    options = RenderOptions(export_dir="/foo/bar")
    template = PhotoTemplate(PhotoInfoNone())
    rendered, _ = template.render("{export_dir}", options)
    assert rendered[0] == "/foo/bar"

    rendered, _ = template.render("{export_dir.name}", options)
    assert rendered[0] == "bar"

    rendered, _ = template.render("{export_dir.parent}", options)
    assert rendered[0] == "/foo"

    rendered, _ = template.render("{export_dir.stem}", options)
    assert rendered[0] == "bar"

    rendered, _ = template.render("{export_dir.suffix}", options)
    assert rendered[0] == ""

    with pytest.raises(ValueError):
        rendered, _ = template.render("{export_dir.foo}", options)


def test_filepath():
    """Test {filepath} template"""
    from osxphotos.photoinfo import PhotoInfoNone
    from osxphotos.phototemplate import PhotoTemplate

    options = RenderOptions(filepath="/foo/bar.jpeg")
    template = PhotoTemplate(PhotoInfoNone())
    rendered, _ = template.render("{filepath}", options)
    assert rendered[0] == "/foo/bar.jpeg"

    rendered, _ = template.render("{filepath.name}", options)
    assert rendered[0] == "bar.jpeg"

    rendered, _ = template.render("{filepath.parent}", options)
    assert rendered[0] == "/foo"

    rendered, _ = template.render("{filepath.parent.name}", options)
    assert rendered[0] == "foo"

    rendered, _ = template.render("{filepath.stem}", options)
    assert rendered[0] == "bar"

    rendered, _ = template.render("{filepath.suffix}", options)
    assert rendered[0] == ".jpeg"

    with pytest.raises(ValueError):
        rendered, _ = template.render("{filepath.foo}", options)


def test_id(photosdb):
    """Test {id} template"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    rendered, _ = photo.render_template("{id}")
    assert rendered[0] == "7"

    rendered, _ = photo.render_template("{id:03d}")
    assert rendered[0] == "007"


def test_album_seq(photosdb):
    """Test {album_seq} and {folder_album_seq} templates"""
    from osxphotos.phototemplate import RenderOptions

    for uuid in UUID_ALBUM_SEQ:
        photo = photosdb.get_photo(uuid)
        album = UUID_ALBUM_SEQ[uuid]["album"]
        options = RenderOptions(dest_path=album)
        for template, value in UUID_ALBUM_SEQ[uuid]["templates"].items():
            rendered, _ = photo.render_template(template, options=options)
            assert rendered[0] == value


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_detected_text(photosdb):
    """Test {detected_text} template"""
    photo = photosdb.get_photo(UUID_DETECTED_TEXT)
    for template, value in TEMPLATE_VALUES_DETECTED_TEXT.items():
        rendered, _ = photo.render_template(template)
        assert value in "".join(rendered)


def test_empty_title(photosdb):
    """Test for issue #506"""
    photo = photosdb.get_photo(UUID_EMPTY_TITLE)
    for template, value in TEMPLATE_VALUES_EMPTY_TITLE.items():
        rendered, _ = photo.render_template(template)
        assert value in "".join(rendered)


def test_strip(photosdb):
    """Test {strip} template"""
    photo = photosdb.get_photo(UUID_EMPTY_TITLE_HAS_DESCRIPTION)
    for template, value in TEMPLATE_VALUES_EMPTY_TITLE_HAS_DESCRIPTION.items():
        rendered, _ = photo.render_template(template)
        assert value in "".join(rendered)


def test_project(photosdb_project):
    """Test {project} template"""
    photo = photosdb_project.get_photo(UUID_PROJECT)
    for template, value in TEMPLATE_VALUES_PROJECT.items():
        rendered, _ = photo.render_template(template)
        assert rendered == value


def test_no_project(photosdb_project):
    """Test {project} template with no project"""
    photo = photosdb_project.get_photo(UUID_NO_PROJECT)
    for template, value in TEMPLATE_VALUES_NO_PROJECT.items():
        rendered, _ = photo.render_template(template)
        assert rendered == value


def test_moment(photosdb):
    """Test {moment} template"""
    for uuid in UUID_MOMENT:
        photo = photosdb.get_photo(uuid)
        for template, value in UUID_MOMENT[uuid]["templates"].items():
            rendered, _ = photo.render_template(template)
            assert rendered == value


def test_bad_slice(photosdb):
    """Test invalid {|slice} filter"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    # bad field raises SyntaxError
    # bad function raises ValueError
    with pytest.raises((SyntaxError, ValueError)):
        rendered, _ = photo.render_template("{photo.original_filename|slice(1:2:3:4)}")


def test_bad_sslice(photosdb):
    """Test invalid {|sslice} filter"""
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    # bad field raises SyntaxError
    # bad function raises ValueError
    with pytest.raises((SyntaxError, ValueError)):
        rendered, _ = photo.render_template("{photo.original_filename|sslice(1:2:3:4)}")


def test_location_latitude_longitude(photosdb):
    """Test {photo.location}, {photo.latitude}, {photo.longitude} #1187"""
    photo = photosdb.get_photo(UUID_LAT_LON)
    rendered, _ = photo.render_template("{photo.location}")
    assert len(rendered) == 2
    assert float(rendered[0]) == pytest.approx(41.256566)
    assert float(rendered[1]) == pytest.approx(-95.940257)

    rendered, _ = photo.render_template("{photo.latitude}")
    assert float(rendered[0]) == pytest.approx(41.256566)

    rendered, _ = photo.render_template("{photo.longitude}")
    assert float(rendered[0]) == pytest.approx(-95.940257)


def test_float_concatenation(photosdb):
    """Test {,+photo.location} #1197"""
    photo = photosdb.get_photo(UUID_LAT_LON)
    rendered, _ = photo.render_template("{,+photo.location}")
    assert len(rendered) == 1
    assert rendered[0] == f"{photo.location[0]},{photo.location[1]}"
