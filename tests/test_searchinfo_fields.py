"""Test SearchInfo fields added for macOS 27 leo.sqlite search categories"""

from __future__ import annotations

import sqlite3
import struct
from types import SimpleNamespace

import pytest

import osxphotos
from osxphotos.photosdb._photosdb_process_searchinfo import _process_leo_searchinfo
from osxphotos.searchinfo import SearchInfo

UUID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"

# (SearchInfo property, [(leo category, content)], expected value)
LEO_FIELDS = [
    ("times_of_day", [(1050, "Noon"), (1050, "Afternoon")], ["Afternoon", "Noon"]),
    ("week_part", [(1060, "Weekend")], "Weekend"),
    ("day_of_week", [(1070, "Saturday")], "Saturday"),
    ("home", [(2010, "Home")], "Home"),
    ("areas_of_interest", [(2130, "Golden Gate Park")], ["Golden Gate Park"]),
    ("country_code", [(2170, "US")], "US"),
    ("region", [(2180, "Northern America")], "Northern America"),
    ("continent", [(2190, "Americas")], "Americas"),
    ("events", [(2240, "The Piano Guys Concert")], ["The Piano Guys Concert"]),
    ("event_performers", [(2250, "The Piano Guys")], ["The Piano Guys"]),
    ("event_types", [(2260, "Music")], ["Music"]),
    ("pets", [(3010, "Pau")], ["Pau"]),
    ("age_groups", [(3030, "Child"), (3030, "Adult")], ["Adult", "Child"]),
    ("landmarks", [(4020, "Space Needle")], ["Space Needle"]),
    ("sounds", [(4050, "Laughter")], ["Laughter"]),
    ("human_actions", [(4060, "Dancing")], ["Dancing"]),
    ("document_types", [(4080, "Receipts")], ["Receipts"]),
    ("activities", [(4090, "Sporting Event")], ["Sporting Event"]),
    ("trip", [(4100, "Trips")], "Trips"),
    ("photographic_style", [(5200, "Standard Style")], "Standard Style"),
    ("file_type", [(8051, "HEIF Image")], "HEIF Image"),
    ("captured_by_me", [(8170, "Captured by Me")], "Captured by Me"),
    (
        "id_document_types",
        [(4130, "Passport"), (11000, "Passport"), (11000, "Student ID")],
        ["Passport", "Student ID"],
    ),
    ("id_document_names", [(11010, "Jane Doe")], ["Jane Doe"]),
    ("venue_types", [(2230, "Stadium")], ["Stadium"]),
    ("venues", [(2220, "Falcon Stadium")], ["Falcon Stadium"]),
    ("bodies_of_water", [(2210, "San Diego Bay")], ["San Diego Bay"]),
    ("source", [(8060, "Messages")], "Messages"),
    ("media_types", [(5030, "Cinematic"), (5190, "Spatial")], ["Cinematic", "Spatial"]),
]

NEW_LIST_FIELDS = [
    "times_of_day",
    "areas_of_interest",
    "events",
    "event_performers",
    "event_types",
    "pets",
    "age_groups",
    "landmarks",
    "sounds",
    "human_actions",
    "document_types",
    "id_document_types",
    "id_document_names",
]

NEW_STR_FIELDS = [
    "week_part",
    "day_of_week",
    "home",
    "country_code",
    "region",
    "continent",
    "trip",
    "photographic_style",
    "file_type",
    "captured_by_me",
]


def _leo_search_info(tmp_path, lexemes: list[tuple[int, str]]) -> SearchInfo:
    """Build a leo.sqlite with lexemes for a single photo and return its SearchInfo"""
    search_db_path = tmp_path / "leo.sqlite"
    conn = sqlite3.connect(search_db_path)
    conn.executescript("""
        CREATE TABLE lexicon (lexeme_id INTEGER, type INTEGER, category INTEGER, content TEXT);
        CREATE TABLE items (identifier TEXT, type INTEGER, lexeme_ids BLOB);
        """)
    conn.executemany(
        "INSERT INTO lexicon VALUES (?, 1, ?, ?)",
        [(i, category, content) for i, (category, content) in enumerate(lexemes, 1)],
    )
    ids = range(1, len(lexemes) + 1)
    conn.execute(
        "INSERT INTO items VALUES (?, 1, ?)",
        (UUID.lower(), struct.pack(f"<{len(lexemes)}I", *ids)),
    )
    conn.commit()
    conn.close()

    by_uuid = {}
    photosdb = SimpleNamespace(_photos_ver=12, _copy_db_file=lambda path: path)
    _process_leo_searchinfo(photosdb, search_db_path, by_uuid, {}, {}, {})
    db = SimpleNamespace(
        _db_version="6000", _photos_ver=12, _db_searchinfo_uuid=by_uuid
    )
    return SearchInfo(SimpleNamespace(uuid=UUID, _db=db))


@pytest.mark.parametrize("field,lexemes,expected", LEO_FIELDS)
def test_leo_search_info_fields(tmp_path, field, lexemes, expected):
    """Test SearchInfo fields read from macOS 27 leo.sqlite"""
    search_info = _leo_search_info(tmp_path, lexemes)
    assert getattr(search_info, field) == expected
    assert search_info.asdict()[field] == expected


def test_leo_search_info_all_excludes_id_documents(tmp_path):
    """Test that identity document info is not included in SearchInfo.all"""
    search_info = _leo_search_info(
        tmp_path,
        [(4130, "Passport"), (11010, "Jane Doe"), (3030, "Adult"), (1070, "Monday")],
    )
    assert sorted(search_info.all) == ["Adult", "Monday"]


@pytest.mark.parametrize(
    "library",
    [
        "tests/Test-10.15.7.photoslibrary/database/photos.db",
        "tests/Test-13.0.0.photoslibrary/database/photos.db",
    ],
)
def test_new_search_info_fields_empty(library):
    """Test new SearchInfo fields return empty values for libraries without the data"""
    photosdb = osxphotos.PhotosDB(dbfile=library)
    for photo in photosdb.photos():
        search_info = photo.search_info
        for field in NEW_LIST_FIELDS:
            assert getattr(search_info, field) == []
        for field in NEW_STR_FIELDS:
            assert getattr(search_info, field) == ""
