"""Test shared albums stored as CollectionShare records in ZSHARE (Photos 11+, macOS 26+)

The test libraries do not contain shared albums so a shared album is added
to a copy of the test library database.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sqlite3

import pytest

from osxphotos import PhotosDB
from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip(
        "requires macOS to create NSPersonNameComponents", allow_module_level=True
    )

from Foundation import NSKeyedArchiver, NSPersonNameComponents

TEST_LIBRARIES = [
    "./tests/Test-26.1.photoslibrary",
    "./tests/Test-27.0_DevBeta.photoslibrary",
]

ALBUM_UUID = "11111111-2222-3333-4444-555555555555"
ALBUM_TITLE = "My Shared Album"
TRASHED_ALBUM_UUID = "66666666-7777-8888-9999-000000000000"
LIBRARY_SCOPE_UUID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
OWNER_HASHED_ID = "owner_hashed_person_id"
CONTRIBUTOR_HASHED_ID = "contributor_hashed_person_id"
OWNER_NAME = "Jane Owner"
CONTRIBUTOR_NAME = "John Contributor"
PARTICIPANT_ROLE_OWNER = 1
PARTICIPANT_ROLE_CONTRIBUTOR = 2
SHARED_VIDEO_DATASTORE_SUBTYPE = 8


def name_components(given: str, family: str) -> bytes:
    """Return NSKeyedArchiver data for NSPersonNameComponents"""
    components = NSPersonNameComponents.alloc().init()
    components.setGivenName_(given)
    components.setFamilyName_(family)
    data, error = (
        NSKeyedArchiver.archivedDataWithRootObject_requiringSecureCoding_error_(
            components, True, None
        )
    )
    assert error is None
    return bytes(data)


def entity(conn: sqlite3.Connection, name: str) -> int:
    """Return the Core Data entity number for name"""
    return conn.execute(
        "SELECT Z_ENT FROM Z_PRIMARYKEY WHERE Z_NAME = ?", (name,)
    ).fetchone()[0]


def add_share(
    conn: sqlite3.Connection, pk: int, ent: int, uuid: str, title: str, trashed: int
):
    """Add a record to ZSHARE"""
    conn.execute(
        """INSERT INTO ZSHARE
        (Z_PK, Z_ENT, Z_OPT, ZUUID, ZTITLE, ZTRASHEDSTATE, ZCLOUDLOCALSTATE,
        ZCREATIONDATE, ZSTARTDATE, ZENDDATE, ZSCOPEIDENTIFIER)
        VALUES (?, ?, 1, ?, ?, ?, 0, 700000000, 600000000, 700000000, ?)""",
        (pk, ent, uuid, title, trashed, f"scope-{uuid}"),
    )


def add_participant(
    conn: sqlite3.Connection,
    pk: int,
    share_pk: int,
    hashed_id: str,
    role: int,
    names: tuple[str, str],
):
    """Add a record to ZSHAREPARTICIPANT"""
    # role column is ZROLE on macOS 26, renamed ZCPLROLE on macOS 27
    columns = [row[1] for row in conn.execute("PRAGMA table_info(ZSHAREPARTICIPANT)")]
    role_column = "ZCPLROLE" if "ZCPLROLE" in columns else "ZROLE"
    conn.execute(
        f"""INSERT INTO ZSHAREPARTICIPANT
        (Z_PK, Z_ENT, Z_OPT, ZSHARE, ZHASHEDPERSONID, {role_column}, ZNAMECOMPONENTS)
        VALUES (?, ?, 1, ?, ?, ?, ?)""",
        (
            pk,
            entity(conn, "ShareParticipant"),
            share_pk,
            hashed_id,
            role,
            name_components(*names),
        ),
    )


def open_photos_db(dbfile: pathlib.Path) -> sqlite3.Connection:
    """Open Photos database for writing; Photos triggers call Core Data functions
    which aren't available outside Photos so register no-op versions of them"""
    conn = sqlite3.connect(dbfile)
    schema = " ".join(
        row[0] for row in conn.execute("SELECT sql FROM sqlite_master") if row[0]
    )
    for name in set(re.findall(r"\b(NSCoreData\w+)\(", schema)):
        conn.create_function(name, -1, lambda *args: None)
    return conn


@pytest.fixture(params=TEST_LIBRARIES, ids=lambda p: pathlib.Path(p).stem)
def shared_album_db(request, tmp_path):
    """Copy test library database and add a shared album, returns (PhotosDB, dict of asset uuids)"""
    library = tmp_path / pathlib.Path(request.param).name
    shutil.copytree(
        pathlib.Path(request.param) / "database",
        library / "database",
        ignore=shutil.ignore_patterns("search", "*.lock"),
    )
    dbfile = library / "database" / "Photos.sqlite"
    conn = open_photos_db(dbfile)

    collection_share_ent = entity(conn, "CollectionShare")
    add_share(conn, 9001, collection_share_ent, ALBUM_UUID, ALBUM_TITLE, 0)
    add_share(conn, 9002, collection_share_ent, TRASHED_ALBUM_UUID, "Trashed Shared", 1)
    # a shared library scope is also stored in ZSHARE but is not a shared album
    add_share(
        conn, 9003, entity(conn, "LibraryScope"), LIBRARY_SCOPE_UUID, "Library", 0
    )

    add_participant(
        conn, 9001, 9001, OWNER_HASHED_ID, PARTICIPANT_ROLE_OWNER, ("Jane", "Owner")
    )
    add_participant(
        conn,
        9002,
        9001,
        CONTRIBUTOR_HASHED_ID,
        PARTICIPANT_ROLE_CONTRIBUTOR,
        ("John", "Contributor"),
    )

    assets = conn.execute(
        "SELECT Z_PK, ZUUID FROM ZASSET WHERE ZTRASHEDSTATE = 0 ORDER BY Z_PK LIMIT 4"
    ).fetchall()
    uuids = {
        "owner": assets[0][1],
        "contributor": assets[1][1],
        "video_missing": assets[2][1],
        "library_scope": assets[3][1],
    }

    # add assets to the shared album in reverse publish order to test sort order
    for publish_date, (pk, hashed_id) in enumerate(
        [
            (assets[2][0], OWNER_HASHED_ID),
            (assets[1][0], CONTRIBUTOR_HASHED_ID),
            (assets[0][0], OWNER_HASHED_ID),
        ]
    ):
        conn.execute(
            """UPDATE ZASSET SET ZCOLLECTIONSHARE = 9001,
            ZCLOUDBATCHPUBLISHDATE = ?, ZCLOUDOWNERHASHEDPERSONID = ?
            WHERE Z_PK = ?""",
            (700000000 + publish_date, hashed_id, pk),
        )
    conn.execute(
        "UPDATE ZASSET SET ZCOLLECTIONSHARE = 9003 WHERE Z_PK = ?", (assets[3][0],)
    )

    # make one asset a shared video whose video file has not been downloaded
    conn.execute("UPDATE ZASSET SET ZKIND = 1 WHERE Z_PK = ?", (assets[2][0],))
    conn.execute(
        """INSERT INTO ZINTERNALRESOURCE
        (Z_ENT, Z_OPT, ZASSET, ZDATASTORESUBTYPE, ZRESOURCETYPE, ZLOCALAVAILABILITY, ZREMOTEAVAILABILITY)
        VALUES (?, 1, ?, ?, 1, -1, 1)""",
        (
            entity(conn, "InternalResource"),
            assets[2][0],
            SHARED_VIDEO_DATASTORE_SUBTYPE,
        ),
    )
    conn.commit()
    conn.close()

    return PhotosDB(dbfile=str(dbfile)), uuids


def test_albums_shared(shared_album_db):
    """Test shared albums are found and trashed albums / library scopes are excluded"""
    photosdb, _ = shared_album_db
    assert photosdb.albums_shared == [ALBUM_TITLE]
    assert [a.uuid for a in photosdb.album_info_shared] == [ALBUM_UUID]
    assert ALBUM_TITLE not in photosdb.albums
    assert photosdb.albums_shared_as_dict == {ALBUM_TITLE: 3}


def test_album_info_shared(shared_album_db):
    """Test AlbumInfo for a shared album"""
    photosdb, uuids = shared_album_db
    album = photosdb.album_info_shared[0]
    assert album.title == ALBUM_TITLE
    assert album.owner == OWNER_NAME
    assert album.folder_names == []
    assert album.parent is None
    # photos sorted in order published to the shared album
    assert [p.uuid for p in album.photos] == [
        uuids["video_missing"],
        uuids["contributor"],
        uuids["owner"],
    ]


def test_album_shared_does_not_clobber_albums(shared_album_db):
    """Test that adding shared albums doesn't change folder hierarchy of regular albums"""
    photosdb, _ = shared_album_db
    for album in photosdb.album_info:
        assert ALBUM_TITLE not in album.folder_names


def test_photo_shared_album(shared_album_db):
    """Test PhotoInfo for photos in a shared album"""
    photosdb, uuids = shared_album_db
    photo = photosdb.get_photo(uuids["contributor"])
    assert photo.shared
    assert ALBUM_TITLE in photo.albums
    assert ALBUM_UUID in [a.uuid for a in photo.album_info]
    assert photo.owner == CONTRIBUTOR_NAME
    assert photosdb.get_photo(uuids["owner"]).owner == OWNER_NAME


def test_photo_library_scope_not_in_shared_album(shared_album_db):
    """Test that assets in a shared library scope are not in a shared album"""
    photosdb, uuids = shared_album_db
    photo = photosdb.get_photo(uuids["library_scope"])
    assert LIBRARY_SCOPE_UUID not in [a.uuid for a in photo.album_info]


def test_query_shared_album(shared_album_db):
    """Test querying photos by shared album name"""
    photosdb, uuids = shared_album_db
    photos = photosdb.photos(albums=[ALBUM_TITLE])
    assert sorted(p.uuid for p in photos) == sorted(
        [uuids["owner"], uuids["contributor"], uuids["video_missing"]]
    )


def test_shared_video_missing(shared_album_db):
    """Test that a shared video that has not been downloaded is missing"""
    photosdb, uuids = shared_album_db
    photo = photosdb.get_photo(uuids["video_missing"])
    assert photo.ismovie
    assert photo.ismissing
    assert photo.path is None


def test_share_info_shared_album_photo(shared_album_db):
    """Test share_info / shared_moment_info don't crash on macOS 26.1+ where
    ZSHARE.ZUPLOADEDPHOTOSCOUNT and ZUPLOADEDVIDEOSCOUNT were removed"""
    photosdb, uuids = shared_album_db
    photo = photosdb.get_photo(uuids["owner"])
    assert photo.share_info is None
    assert photo.shared_moment_info is None


def test_share_info_library_scope(shared_album_db):
    """Test share_info for a photo in a shared library scope on macOS 26.1+"""
    photosdb, uuids = shared_album_db
    conn = open_photos_db(pathlib.Path(photosdb.db_path))
    conn.execute(
        "UPDATE ZASSET SET ZLIBRARYSCOPE = 9003 WHERE ZUUID = ?",
        (uuids["library_scope"],),
    )
    conn.commit()
    conn.close()
    photosdb = PhotosDB(dbfile=photosdb.db_path)
    share_info = photosdb.get_photo(uuids["library_scope"]).share_info
    assert share_info.uuid == LIBRARY_SCOPE_UUID
    assert share_info.title == "Library"
    assert share_info.uploaded_photos_count is None
