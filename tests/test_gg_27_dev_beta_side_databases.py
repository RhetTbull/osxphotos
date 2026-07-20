"""Test macOS 27 Photos side database schema support."""

from __future__ import annotations

import sqlite3
import struct
from types import SimpleNamespace

from osxphotos.media_analysis import get_caption, get_media_analysis_results
from osxphotos.photos_datetime import photos_datetime_local
from osxphotos.photosdb._photosdb_process_searchinfo import (
    _process_leo_searchinfo,
    decode_leo_lexeme_ids,
)


def test_decode_leo_lexeme_ids():
    """Test decoding leo.sqlite little-endian UInt32 lexeme IDs."""
    data = struct.pack("<III", 1, 256, 65536) + b"\xff"

    assert decode_leo_lexeme_ids(data) == [1, 256, 65536]


def test_process_leo_searchinfo(tmp_path):
    """Test processing macOS 27 leo.sqlite search info."""
    search_db_path = tmp_path / "leo.sqlite"
    conn = sqlite3.connect(search_db_path)
    conn.executescript(
        """
        CREATE TABLE lexicon (
            lexeme_id INTEGER,
            type INTEGER,
            category INTEGER,
            content TEXT,
            identifier TEXT,
            score REAL
        );
        CREATE TABLE items (
            identifier TEXT,
            type INTEGER,
            lexeme_ids BLOB
        );
        """
    )
    conn.executemany(
        "INSERT INTO lexicon VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 4000, "Bridge\x00", "scene/1", 1.0),
            (1, 2, 4000, "Overpass", "scene/1", 1.0),
            (2, 1, 4120, "OPEN", "ocr/open", 1.0),
            (3, 1, 6000, "Nikon Z 8", "camera/nikon", 1.0),
            (4, 1, 9999, "Internal", "internal/1", 1.0),
        ],
    )
    uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    conn.executemany(
        "INSERT INTO items VALUES (?, ?, ?)",
        [
            (uuid, 1, struct.pack("<IIII", 1, 2, 3, 4)),
            ("ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee", 2, struct.pack("<I", 1)),
        ],
    )
    conn.commit()
    conn.close()

    photosdb = SimpleNamespace(_photos_ver=12, _copy_db_file=lambda path: path)
    by_uuid = {}
    by_category = {}
    labels = {}
    labels_normalized = {}

    _process_leo_searchinfo(
        photosdb, search_db_path, by_uuid, by_category, labels, labels_normalized
    )

    uuid = uuid.upper()
    assert [rec["content_string"] for rec in by_uuid[uuid]] == [
        "Bridge",
        "OPEN",
        "Nikon Z 8",
    ]
    assert [rec["category"] for rec in by_uuid[uuid]] == [1500, 1203, 2300]
    assert labels == {"Bridge": [uuid]}
    assert labels_normalized == {"bridge": [uuid]}
    assert by_category[1500] == ["bridge"]


def test_typed_media_analysis_caption(tmp_path):
    """Test macOS 27 typed MediaAnalysis caption tables."""
    library_path = tmp_path / "Test.photoslibrary"
    database_path = library_path / "database"
    database_path.mkdir(parents=True)
    photos_db_path = database_path / "photos.db"
    photos_db_path.touch()

    media_analysis_dir = library_path / "private/com.apple.mediaanalysisd/MediaAnalysis"
    media_analysis_dir.mkdir(parents=True)
    media_analysis_path = media_analysis_dir / "MediaAnalysis.sqlite"
    conn = sqlite3.connect(media_analysis_path)
    conn.executescript(
        """
        CREATE TABLE ZASSET (
            Z_PK INTEGER PRIMARY KEY,
            ZLOCALIDENTIFIER TEXT,
            ZDATEANALYZED FLOAT
        );
        CREATE TABLE ZRESULT (
            Z_PK INTEGER PRIMARY KEY,
            ZASSET INTEGER,
            ZRESULTS BLOB
        );
        CREATE TABLE ZIMAGECAPTIONRESULT (
            Z_PK INTEGER PRIMARY KEY,
            ZASSET INTEGER,
            ZCONFIDENCE FLOAT,
            ZCAPTION TEXT
        );
        CREATE TABLE ZVIDEOCAPTIONRESULT (
            Z_PK INTEGER PRIMARY KEY,
            ZASSET INTEGER,
            ZCONFIDENCE FLOAT,
            ZCAPTION TEXT
        );
        CREATE TABLE ZVIDEOSEGMENTCAPTIONRESULT (
            Z_PK INTEGER PRIMARY KEY,
            ZASSET INTEGER,
            ZCONFIDENCE FLOAT,
            ZCAPTION TEXT
        );
        """
    )
    uuid = "11111111-2222-3333-4444-555555555555"
    local_identifier = f"{uuid}/L0/001"
    date_seconds = 42.0
    conn.execute(
        "INSERT INTO ZASSET VALUES (?, ?, ?)", (1, local_identifier, date_seconds)
    )
    conn.execute(
        "INSERT INTO ZIMAGECAPTIONRESULT VALUES (?, ?, ?, ?)",
        (1, 1, 0.75, "A red bridge over water"),
    )
    conn.commit()
    conn.close()

    photo = SimpleNamespace(
        uuid=uuid,
        filename="IMG_0001.JPG",
        original_filename="IMG_0001.JPG",
        _db=SimpleNamespace(db_path=str(photos_db_path), photos_version=12),
    )

    results = get_media_analysis_results(photo)

    assert results["uuid"] == uuid
    assert results["image_caption"] == {
        "imageCaptionText": "A red bridge over water",
        "imageCaptionConfidence": 0.75,
    }
    assert get_caption(results) == "A red bridge over water"
    assert results["date_analyzed"] == photos_datetime_local(date_seconds)
