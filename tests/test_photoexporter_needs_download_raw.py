"""Tests for evicted RAW+JPEG pairs in export --update --download-missing

On Photos 7+, PhotoInfo.uti_raw came only from the RAW file on disk, so it was
None while the RAW was evicted to iCloud. The pre-download check
(PhotoExporter._needs_download_for_update) then looked for <stem>.raw on the
destination, never found it, and downloaded the pair on every run; with
--cleanup, the real RAW on the destination was deleted. uti_raw now falls back
to the RAW's type in the Photos database.

These run at the PhotoExporter level, and through the CLI for --cleanup.
_stage_missing_photos_for_export_helper, the one place a download through
AppleScript or PhotoKit would start, is replaced by a fake that stages copies
of test files, so nothing is downloaded and Photos is never touched.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
from dataclasses import dataclass
from typing import NamedTuple

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos.cli.export import export as cli_export
from osxphotos.exportoptions import ExportOptions
from osxphotos.photoexporter import PhotoExporter, StagedFiles
from osxphotos.photoinfo import PhotoInfo
from osxphotos.photosdb.photosdb_utils import uti_for_compact_uti
from osxphotos.stat_cache import DirectoryStatCache
from osxphotos.uti import get_uti_for_extension


class FakeDownload:
    """Stands in for _stage_missing_photos_for_export_helper and records each call

    It stages copies of the files given to stage() under the given names, as
    an AppleScript download does; with no files it stages nothing, as a failed
    download does.
    """

    def __init__(self, staging: pathlib.Path):
        self.staging = staging
        self.calls = []
        self.files = {}

    def stage(self, files):
        """Stage files, {kind: (source, name)}, on each call from now on"""
        self.files = files

    def reset(self):
        """Forget the calls so far and stage nothing from now on"""
        self.calls = []
        self.files = {}

    def __call__(self, exporter, options):
        self.calls.append(options)
        staged = StagedFiles()
        for kind, (src, name) in self.files.items():
            staged_path = self.staging / name
            shutil.copy(src, staged_path)
            setattr(staged, kind, str(staged_path))
        return staged


@pytest.fixture
def download(monkeypatch, tmp_path):
    """A FakeDownload in place of the download helper, so nothing is downloaded"""
    staging = tmp_path / "staging"
    staging.mkdir()
    fake = FakeDownload(staging)
    monkeypatch.setattr(
        PhotoExporter,
        "_stage_missing_photos_for_export_helper",
        lambda self, options: fake(self, options),
    )
    return fake


def _export(photo, dest_dir, case_sensitive=False, **options):
    """Export photo with --update and options as a separate run, with the
    export DB and a DirectoryStatCache opened afresh as the CLI does

    The stat cache matches names on the destination case-insensitively, as the
    CLI's does on macOS, or exactly with case_sensitive, so the results don't
    depend on the case behaviour of the filesystem under tmp_path.
    """
    export_db = osxphotos.ExportDB(dest_dir.parent / "export.db", dest_dir)
    stat_cache = DirectoryStatCache(case_sensitive=case_sensitive)
    try:
        return PhotoExporter(photo).export(
            dest_dir,
            options=ExportOptions(
                update=True, export_db=export_db, stat_cache=stat_cache, **options
            ),
        )
    finally:
        export_db.close()


# RAW+JPEG pairs. On Photos 7+ these libraries have no RAW type in the
# column osxphotos reads for Photos 5 and 6, and uti_raw came from the RAW file
# on disk, so it was None while the RAW was evicted.
RAW_PAIR_LIBRARIES = [
    "./tests/Test-13.0.0.photoslibrary",
    "./tests/Test-15.4.1.photoslibrary",
    "./tests/Test-26.1.photoslibrary",
]
CR2_UTI = "com.canon.cr2-raw-image"
RAF_UTI = "com.fuji.raw-image"
# IMG_2000.JPG: a pair not copied into the library, missing: path_raw is None
UUID_MISSING_PAIR = "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A"
# IMG_1994.JPG: a pair stored in the library with its CR2 on disk
UUID_RAW_PAIR = "A92D9C26-3A50-4197-9388-CB5F7DB9FA91"
RAW_PAIRS = [(UUID_MISSING_PAIR, "IMG_2000"), (UUID_RAW_PAIR, "IMG_1994")]


@dataclass(frozen=True)
class RawType:
    """A RAW format under test: its extension, its UTI, and the extension a
    download stages it under, whose case comes from Photos (.CR2 for the test
    libraries' Canon pairs, lower-case .raf for a Fuji pair)"""

    name: str
    uti: str
    staged_ext: str


CR2 = RawType("cr2", CR2_UTI, "CR2")
RAF = RawType("raf", RAF_UTI, "raf")
# ZINTERNALRESOURCE.ZCOMPACTUTI code for a Fuji RAF (com.fuji.raw-image)
RAF_COMPACT_UTI = 21
# Pumkins2.jpg, made an evicted RAF-only original (no JPEG pair) named
# DSCF5273.RAF in the RAF copies
UUID_RAF_ONLY = "D79B8D77-BFFC-460B-9312-034F2877D35B"
RAF_ONLY_FILENAME = "DSCF5273.RAF"


def _make_raf_library(library: str, dest: pathlib.Path) -> pathlib.Path:
    """Copy a test library and turn its CR2+JPEG pairs into RAF+JPEG pairs

    The test libraries have no Fuji photos. In the copy, the RAW resources of
    IMG_2000 and IMG_1994 get the compact UTI code for RAF,
    IMG_2000's referenced RAW is renamed IMG_2000.RAF, and IMG_1994's RAW in
    originals/ is renamed from _4.cr2 to _4.raf. The checked-in library is
    not modified.
    """
    copy = dest / pathlib.Path(library).name
    shutil.copytree(library, copy)
    conn = sqlite3.connect(copy / "database" / "Photos.sqlite")
    try:
        uuids = (UUID_MISSING_PAIR, UUID_RAW_PAIR)
        raw_resources = """ SELECT ZINTERNALRESOURCE.Z_PK FROM ZINTERNALRESOURCE
            JOIN ZASSET ON ZASSET.Z_PK = ZINTERNALRESOURCE.ZASSET
            WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17 AND ZASSET.ZUUID IN (?, ?)
        """
        cur = conn.execute(
            f"UPDATE ZINTERNALRESOURCE SET ZCOMPACTUTI = ? WHERE Z_PK IN ({raw_resources})",
            (RAF_COMPACT_UTI, *uuids),
        )
        assert cur.rowcount == 2
        cur = conn.execute(
            f""" UPDATE ZFILESYSTEMBOOKMARK
            SET ZPATHRELATIVETOVOLUME = replace(ZPATHRELATIVETOVOLUME, '.CR2', '.RAF')
            WHERE ZRESOURCE IN ({raw_resources})""",
            uuids,
        )
        assert cur.rowcount == 1  # IMG_2000, a referenced file
        _make_raf_only_original(conn)
        conn.commit()
    finally:
        conn.close()
    (raw_cr2,) = (copy / "originals").glob(f"*/{UUID_RAW_PAIR}_4.cr2")
    raw_cr2.rename(raw_cr2.with_suffix(".raf"))
    # the RAF-only original is evicted: its file isn't in originals/
    (copy / "originals" / "D" / f"{UUID_RAF_ONLY}.jpeg").unlink()
    return copy


def _make_raf_only_original(conn):
    """Turn Pumkins2.jpg into an evicted RAF-only original, DSCF5273.RAF

    As Photos stores one: asset UTI com.fuji.raw-image, compact UTI 21 on the
    original resource, not available locally.
    """
    (asset_pk,) = conn.execute(
        "SELECT Z_PK FROM ZASSET WHERE ZUUID = ?", (UUID_RAF_ONLY,)
    ).fetchone()
    conn.execute(
        "UPDATE ZASSET SET ZUNIFORMTYPEIDENTIFIER = ?, ZFILENAME = ? WHERE Z_PK = ?",
        (RAF_UTI, f"{UUID_RAF_ONLY}.raf", asset_pk),
    )
    conn.execute(
        "UPDATE ZADDITIONALASSETATTRIBUTES SET ZORIGINALFILENAME = ? WHERE ZASSET = ?",
        (RAF_ONLY_FILENAME, asset_pk),
    )
    cur = conn.execute(
        """ UPDATE ZINTERNALRESOURCE SET ZCOMPACTUTI = ?, ZDATALENGTH = ?
        WHERE ZASSET = ? AND ZRESOURCETYPE = 0 AND ZDATASTORESUBTYPE = 1""",
        (RAF_COMPACT_UTI, 33790976, asset_pk),
    )
    assert cur.rowcount == 1
    conn.execute(
        "UPDATE ZINTERNALRESOURCE SET ZLOCALAVAILABILITY = -1 WHERE ZASSET = ?",
        (asset_pk,),
    )


@pytest.fixture(scope="module")
def raf_libraries(tmp_path_factory):
    """RAF copies of the test libraries, made when first asked for"""
    copies = {}

    def get(library):
        if library not in copies:
            copies[library] = _make_raf_library(
                library, tmp_path_factory.mktemp("raf_library")
            )
        return copies[library]

    return get


RAW_LIBRARIES = [
    pytest.param(
        (library, raw_type), id=f"{pathlib.Path(library).stem}-{raw_type.name}"
    )
    for raw_type in (CR2, RAF)
    for library in RAW_PAIR_LIBRARIES
]


@pytest.fixture(scope="module", params=RAW_LIBRARIES)
def raw_library(request, raf_libraries):
    """(PhotosDB, RawType): a test library as it is (CR2 pairs), or its RAF copy"""
    library, raw_type = request.param
    if raw_type is RAF:
        library = raf_libraries(library)
    return osxphotos.PhotosDB(dbfile=str(library)), raw_type


@pytest.fixture
def raw_photosdb(raw_library):
    return raw_library[0]


@pytest.fixture
def raw_type(raw_library):
    return raw_library[1]


@pytest.fixture
def evicted_pair(raw_photosdb, monkeypatch):
    """Make IMG_1994 look evicted to iCloud: neither its JPEG nor its RAW is on disk

    Returns the paths of IMG_1994's JPEG and RAW in the library, read beforehand.
    """
    present = raw_photosdb.get_photo(UUID_RAW_PAIR)
    files = (present.path, present.path_raw)
    assert all(files)
    for attr in ("path", "path_raw"):
        prop = getattr(PhotoInfo, attr)

        def evicted_path(self, prop=prop):
            return None if self.uuid == UUID_RAW_PAIR else prop.fget(self)

        monkeypatch.setattr(PhotoInfo, attr, property(evicted_path))
    return files


def _export_raw_pair(photo, dest_dir, case_sensitive=False):
    """Export a RAW+JPEG pair with --update --download-missing"""
    return _export(
        photo,
        dest_dir,
        case_sensitive=case_sensitive,
        download_missing=True,
        raw_photo=True,
    )


class ExportedPair(NamedTuple):
    """An evicted RAW+JPEG pair exported once"""

    photo: PhotoInfo
    dest_dir: pathlib.Path
    stem: str
    raw_name: str  # the name of the RAW on the destination


def _lower(paths):
    """Paths as lower-case strings: the RAW's extension case comes from Photos"""
    return sorted(str(path).lower() for path in paths)


def _stage_pair(download, evicted_pair, stem, raw_type):
    """Have the download stage <stem>.JPG and the RAW (<stem>.CR2 or
    <stem>.raf), with IMG_1994's content; return the RAW's name"""
    jpeg, raw = evicted_pair
    raw_name = f"{stem}.{raw_type.staged_ext}"
    download.stage({"original": (jpeg, f"{stem}.JPG"), "raw": (raw, raw_name)})
    return raw_name


@pytest.fixture
def exported_pair(raw_photosdb, raw_type, evicted_pair, download, tmp_path, request):
    """Export an evicted RAW+JPEG pair once, downloading <stem>.JPG and the RAW"""
    uuid, stem = request.param
    photo = raw_photosdb.get_photo(uuid)
    assert photo.has_raw and not photo.path and not photo.path_raw

    dest_dir = tmp_path / "export"
    dest_dir.mkdir()
    raw_name = _stage_pair(download, evicted_pair, stem, raw_type)
    first = _export_raw_pair(photo, dest_dir)
    assert len(download.calls) == 1
    assert _lower(first.new) == _lower([dest_dir / f"{stem}.JPG", dest_dir / raw_name])
    # the RAW is written under the staged name, case included
    assert raw_name in [path.name for path in dest_dir.iterdir()]
    download.reset()
    return ExportedPair(photo, dest_dir, stem, raw_name)


@pytest.mark.parametrize("exported_pair", RAW_PAIRS, indirect=True)
def test_raw_pair_up_to_date_no_download(exported_pair, download):
    """An evicted RAW+JPEG pair already exported and unchanged is skipped
    without a download"""
    pair = exported_pair
    results = _export_raw_pair(pair.photo, pair.dest_dir)
    assert download.calls == []
    assert _lower(results.skipped) == _lower(
        [pair.dest_dir / f"{pair.stem}.JPG", pair.dest_dir / pair.raw_name]
    )
    assert results.new == results.updated == results.missing == []


@pytest.mark.parametrize("changed", ["JPG", "RAW"])
@pytest.mark.parametrize("exported_pair", RAW_PAIRS, indirect=True)
def test_raw_pair_changed_downloads(exported_pair, download, changed):
    """An evicted pair whose JPEG or RAW changed on the destination is
    downloaded again; one not yet exported is downloaded by exported_pair"""
    pair = exported_pair
    changed_name = f"{pair.stem}.JPG" if changed == "JPG" else pair.raw_name
    (pair.dest_dir / changed_name).write_bytes(b"changed")
    _export_raw_pair(pair.photo, pair.dest_dir)
    assert len(download.calls) == 1
    assert download.calls[0].raw_photo


@pytest.mark.parametrize("exported_pair", RAW_PAIRS, indirect=True)
def test_missing_raw_recorded_with_real_extension(exported_pair, raw_type, download):
    """A RAW that needs updating but doesn't download is reported missing
    under its real extension (.cr2 or .raf), not .raw"""
    pair = exported_pair
    (pair.dest_dir / pair.raw_name).write_bytes(b"changed")
    results = _export_raw_pair(pair.photo, pair.dest_dir)
    assert len(download.calls) == 1
    assert _lower(results.missing) == _lower(
        [
            pair.dest_dir / f"{pair.stem}.JPG",
            pair.dest_dir / f"{pair.stem}.{raw_type.name}",
        ]
    )


@pytest.mark.parametrize("uuid", [UUID_MISSING_PAIR, UUID_RAW_PAIR])
def test_uti_raw_without_raw_on_disk(raw_photosdb, raw_type, evicted_pair, uuid):
    """uti_raw comes from the Photos database when the RAW isn't on disk"""
    photo = raw_photosdb.get_photo(uuid)
    assert photo.path_raw is None
    assert photo.uti_raw == raw_type.uti


def test_uti_raw_with_raw_on_disk_unchanged(raw_photosdb, raw_type):
    """uti_raw still comes from the RAW file when it is on disk"""
    photo = raw_photosdb.get_photo(UUID_RAW_PAIR)
    assert pathlib.Path(photo.path_raw).suffix == f".{raw_type.name}"
    assert photo.uti_raw == raw_type.uti


def test_raf_pair_exported_and_checked_under_lower_case_raf(
    raf_libraries, monkeypatch, download, tmp_path
):
    """A RAF+JPEG pair with its RAF on disk is exported as <stem>.raf, lower
    case, and once it is evicted the check looks for that exact name, so it is
    skipped without a download even on a case-sensitive destination"""
    library = raf_libraries("./tests/Test-26.1.photoslibrary")
    photo = osxphotos.PhotosDB(dbfile=str(library)).get_photo(UUID_RAW_PAIR)
    assert photo.path and photo.path_raw.endswith("_4.raf")
    dest_dir = tmp_path / "export"
    dest_dir.mkdir()

    first = _export_raw_pair(photo, dest_dir, case_sensitive=True)
    assert download.calls == []
    names = sorted(path.name for path in dest_dir.iterdir())
    assert names == ["IMG_1994.JPG", "IMG_1994.raf"]
    assert sorted(first.new) == [str(dest_dir / name) for name in names]

    for attr in ("path", "path_raw"):
        monkeypatch.setattr(PhotoInfo, attr, None)
    results = _export_raw_pair(photo, dest_dir, case_sensitive=True)
    assert download.calls == []
    assert sorted(results.skipped) == [str(dest_dir / name) for name in names]


@pytest.mark.parametrize("library", RAW_PAIR_LIBRARIES)
def test_raf_only_original_checked_under_its_upper_case_name(
    raf_libraries, download, tmp_path, library
):
    """An evicted RAF-only original is exported under its original name,
    DSCF5273.RAF (upper case, unlike a pair's .raf), and once up to date the
    check finds that exact name and skips it without a download"""
    library = raf_libraries(library)
    photo = osxphotos.PhotosDB(dbfile=str(library)).get_photo(UUID_RAF_ONLY)
    assert photo.ismissing and photo.path is None
    assert not photo.has_raw
    assert photo.original_filename == RAF_ONLY_FILENAME
    assert photo.uti == photo.uti_original == RAF_UTI

    dest_dir = tmp_path / "export"
    dest_dir.mkdir()
    raf_bytes = tmp_path / "raf_bytes"
    raf_bytes.write_bytes(b"FUJIFILMCCD-RAW ")
    download.stage({"original": (raf_bytes, RAF_ONLY_FILENAME)})
    first = _export_raw_pair(photo, dest_dir, case_sensitive=True)
    assert len(download.calls) == 1
    assert [path.name for path in dest_dir.iterdir()] == [RAF_ONLY_FILENAME]
    assert first.new == [str(dest_dir / RAF_ONLY_FILENAME)]

    download.reset()
    results = _export_raw_pair(photo, dest_dir, case_sensitive=True)
    assert download.calls == []
    assert results.skipped == [str(dest_dir / RAF_ONLY_FILENAME)]
    assert results.new == results.updated == results.missing == []


@pytest.mark.parametrize(
    "compact_uti,uti",
    [
        ("1", "public.jpeg"),
        ("9", "com.adobe.raw-image"),
        ("10", "com.sony.arw-raw-image"),
        ("11", CR2_UTI),
        (11, CR2_UTI),
        ("21", RAF_UTI),
        ("36", "public.data"),
        ("37", "com.apple.photos.apple-adjustment-envelope"),
        ("39", "public.jpeg-xl"),
        ("_org.webmproject.webp", "org.webmproject.webp"),
        ("2", None),
        ("99", None),
        (None, None),
    ],
)
def test_uti_for_compact_uti(compact_uti, uti):
    """ZCOMPACTUTI is a code, or "_" and the UTI itself"""
    assert uti_for_compact_uti(compact_uti) == uti


def _photos_7_libraries():
    """The test libraries whose resources have a ZCOMPACTUTI (Photos 7+)"""
    libraries = []
    for library in sorted(pathlib.Path("./tests").glob("*.photoslibrary")):
        db = library / "database" / "Photos.sqlite"
        if not db.is_file():
            continue
        conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
        try:
            columns = [
                row[1] for row in conn.execute("PRAGMA table_info(ZINTERNALRESOURCE)")
            ]
        finally:
            conn.close()
        if "ZCOMPACTUTI" in columns:
            libraries.append(str(library))
    return libraries


PHOTOS_7_LIBRARIES = _photos_7_libraries()
# ZDATASTORESUBTYPE of a resource, and the PhotoInfo property for its file
RESOURCE_PATHS = {1: "path", 17: "path_raw", 18: "path_live_photo"}


# Libraries with a RAW+JPEG pair whose RAW is on disk
LIBRARIES_WITH_RAW_ON_DISK = [
    pathlib.Path(library).name
    for library in RAW_PAIR_LIBRARIES
    + [
        "./tests/Test-16.0.0-beta.photoslibrary",
        "./tests/Test-27.0_DevBeta.photoslibrary",
    ]
]


def test_photos_7_libraries_include_libraries_with_raw_on_disk():
    names = [pathlib.Path(library).name for library in PHOTOS_7_LIBRARIES]
    assert set(LIBRARIES_WITH_RAW_ON_DISK) <= set(names)


@pytest.mark.parametrize(
    "library", PHOTOS_7_LIBRARIES, ids=lambda library: pathlib.Path(library).stem
)
def test_library_compact_uti_codes_match_table(library, tmp_path):
    """The code of each original, RAW and Live Photo video whose file is on
    disk in the test library resolves to the UTI for the file's extension"""
    db = pathlib.Path(library) / "database" / "Photos.sqlite"
    # read a copy of the database, so the library's -shm files are left alone
    db_copy = tmp_path / "Photos.sqlite"
    for db_file in db.parent.glob("Photos.sqlite*"):
        shutil.copy(db_file, tmp_path / db_file.name)
    conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    try:
        rows = conn.execute(
            f""" SELECT ZASSET.ZUUID, ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
            ZINTERNALRESOURCE.ZCOMPACTUTI
            FROM ZINTERNALRESOURCE
            JOIN ZASSET ON ZASSET.Z_PK = ZINTERNALRESOURCE.ZASSET
            WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE IN
            ({", ".join(str(subtype) for subtype in RESOURCE_PATHS)})"""
        ).fetchall()
    finally:
        conn.close()
    photosdb = osxphotos.PhotosDB(
        dbfile=str(db_copy), library_path=library, _skip_searchinfo=True
    )
    checked = []
    for uuid, subtype, code in rows:
        photo = photosdb.get_photo(uuid)
        path = getattr(photo, RESOURCE_PATHS[subtype]) if photo else None
        if not path:
            continue
        uti = get_uti_for_extension(pathlib.Path(path).suffix)
        checked.append((uuid, subtype, code, uti_for_compact_uti(code), uti))
    assert [c for c in checked if c[3] != c[4]] == []
    if pathlib.Path(library).name in LIBRARIES_WITH_RAW_ON_DISK:
        assert any(subtype == 17 for _, subtype, *_ in checked)


# A RAW's compact UTI code that isn't in COMPACT_UTI_CODES, such as one a later
# Photos adds, is learned from the library's RAWs with that code whose file is
# on disk. ARW_COMPACT_UTI stands for a code the table doesn't have.
ARW_COMPACT_UTI = 99
ARW_UTI = "com.sony.arw-raw-image"
FALLBACK_LIBRARY = "./tests/Test-26.1.photoslibrary"


def _make_library_with_raw_code(dest, uuids, code, rename_raw_to=None):
    """Copy FALLBACK_LIBRARY and give the RAW resources of the pairs in uuids
    the compact UTI code; with rename_raw_to, rename IMG_1994's RAW in
    originals/ from _4.cr2 to that extension. Returns the copy's path."""
    copy = dest / pathlib.Path(FALLBACK_LIBRARY).name
    shutil.copytree(FALLBACK_LIBRARY, copy)
    conn = sqlite3.connect(copy / "database" / "Photos.sqlite")
    try:
        placeholders = ", ".join("?" for _ in uuids)
        cur = conn.execute(
            f""" UPDATE ZINTERNALRESOURCE SET ZCOMPACTUTI = ? WHERE Z_PK IN (
            SELECT ZINTERNALRESOURCE.Z_PK FROM ZINTERNALRESOURCE
            JOIN ZASSET ON ZASSET.Z_PK = ZINTERNALRESOURCE.ZASSET
            WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17
            AND ZASSET.ZUUID IN ({placeholders}))""",
            (code, *uuids),
        )
        assert cur.rowcount == len(uuids)
        conn.commit()
    finally:
        conn.close()
    if rename_raw_to:
        (raw_cr2,) = (copy / "originals").glob(f"*/{UUID_RAW_PAIR}_4.cr2")
        raw_cr2.rename(raw_cr2.with_suffix(f".{rename_raw_to}"))
    return copy


def test_unknown_raw_code_learned_from_raw_on_disk(tmp_path):
    """An evicted pair's RAW with a code not in the table gets the type of
    another pair's RAW on disk with the same code"""
    library = _make_library_with_raw_code(
        tmp_path, [UUID_MISSING_PAIR, UUID_RAW_PAIR], ARW_COMPACT_UTI, "arw"
    )
    photosdb = osxphotos.PhotosDB(dbfile=str(library))
    on_disk = photosdb.get_photo(UUID_RAW_PAIR)
    assert on_disk.path_raw.endswith("_4.arw")
    evicted = photosdb.get_photo(UUID_MISSING_PAIR)
    assert evicted.path_raw is None
    assert evicted.uti_raw == ARW_UTI


def test_unknown_raw_code_without_a_source_stays_unknown(tmp_path, download):
    """With no RAW on disk with the same code, an unknown code leaves
    uti_raw None, and the RAW is still recorded missing as .raw"""
    library = _make_library_with_raw_code(
        tmp_path, [UUID_MISSING_PAIR], ARW_COMPACT_UTI
    )
    photo = osxphotos.PhotosDB(dbfile=str(library)).get_photo(UUID_MISSING_PAIR)
    assert photo.path_raw is None
    assert photo.uti_raw is None

    dest_dir = tmp_path / "export"
    dest_dir.mkdir()
    results = _export_raw_pair(photo, dest_dir)
    assert len(download.calls) == 1
    assert _lower(results.missing) == _lower(
        [dest_dir / "IMG_2000.JPG", dest_dir / "IMG_2000.raw"]
    )


def test_known_raw_code_wins_over_raw_on_disk(tmp_path):
    """A code in the table keeps its UTI even when a RAW on disk with that
    code has another type's extension"""
    library = _make_library_with_raw_code(
        tmp_path, [UUID_MISSING_PAIR, UUID_RAW_PAIR], 11, "arw"
    )
    photosdb = osxphotos.PhotosDB(dbfile=str(library))
    assert photosdb.get_photo(UUID_RAW_PAIR).uti_raw == ARW_UTI  # from its file
    assert photosdb.get_photo(UUID_MISSING_PAIR).uti_raw == CR2_UTI


# --cleanup after an evicted RAW+JPEG pair. Cleanup lives in the CLI: it
# keeps the files listed as exported, skipped or missing and deletes the rest.
# While uti_raw was None the RAW was listed under a guessed <stem>.raw, so the
# real <stem>.raf or .CR2 on the destination was deleted. These run the CLI
# with --exportdb, as a scripted backup would. The CLI's stat cache matches
# names case-insensitively on macOS, where export runs, and exactly elsewhere,
# so cli_exported_pair sets the macOS behaviour, as _export does for
# PhotoExporter, for the .CR2 on the destination to match the check's .cr2.


def _cli_export_cleanup(photo, dest_dir):
    """Run export --update --download-missing --cleanup --exportdb <db> on one
    photo, as a separate run; return the --report records keyed by lower-case
    file name"""
    report = dest_dir.parent / "report.json"
    result = CliRunner().invoke(
        cli_export,
        [
            "--library",
            str(photo._db.library_path),
            "--uuid",
            photo.uuid,
            "--update",
            "--download-missing",
            "--cleanup",
            "--exportdb",
            str(dest_dir.parent / "export.db"),
            "--report",
            str(report),
            "-V",
            str(dest_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    return {
        pathlib.Path(record["filename"]).name.lower(): record
        for record in json.loads(report.read_text())
    }


@pytest.fixture
def cli_exported_pair(
    raw_photosdb, raw_type, evicted_pair, download, tmp_path, request, monkeypatch
):
    """Export an evicted RAW+JPEG pair once through the CLI, downloading
    <stem>.JPG and the RAW"""
    monkeypatch.setattr("osxphotos.stat_cache.is_macos", True)
    uuid, stem = request.param
    photo = raw_photosdb.get_photo(uuid)
    dest_dir = tmp_path / "export"
    dest_dir.mkdir()
    raw_name = _stage_pair(download, evicted_pair, stem, raw_type)
    _cli_export_cleanup(photo, dest_dir)
    assert len(download.calls) == 1
    assert sorted(path.name for path in dest_dir.iterdir()) == sorted(
        [f"{stem}.JPG", raw_name]
    )
    download.reset()
    return ExportedPair(photo, dest_dir, stem, raw_name)


@pytest.mark.parametrize("cli_exported_pair", RAW_PAIRS, indirect=True)
def test_cleanup_keeps_up_to_date_evicted_raw_pair(cli_exported_pair, download):
    """--cleanup keeps both files of an evicted RAW+JPEG pair that is up to
    date: the pair is skipped, with no download"""
    pair = cli_exported_pair
    before = {path.name: path.read_bytes() for path in pair.dest_dir.iterdir()}
    records = _cli_export_cleanup(pair.photo, pair.dest_dir)
    after = {path.name: path.read_bytes() for path in pair.dest_dir.iterdir()}
    assert after == before
    assert not any(r["cleanup_deleted_file"] for r in records.values())
    assert download.calls == []
    assert records[f"{pair.stem}.jpg".lower()]["skipped"]
    assert records[pair.raw_name.lower()]["skipped"]


@pytest.mark.parametrize("changed", ["JPG", "RAW"])
@pytest.mark.parametrize("cli_exported_pair", RAW_PAIRS, indirect=True)
def test_cleanup_keeps_raw_of_evicted_pair_recorded_missing(
    cli_exported_pair, raw_type, download, changed
):
    """--cleanup keeps the RAW of an evicted pair whose download returns
    nothing: the pair is recorded missing under the RAW's real extension
    (.cr2 or .raf), so the file already on the destination is kept"""
    pair = cli_exported_pair
    changed_name = f"{pair.stem}.JPG" if changed == "JPG" else pair.raw_name
    (pair.dest_dir / changed_name).write_bytes(b"changed")
    before = {path.name: path.read_bytes() for path in pair.dest_dir.iterdir()}
    records = _cli_export_cleanup(pair.photo, pair.dest_dir)
    after = {path.name: path.read_bytes() for path in pair.dest_dir.iterdir()}
    assert after == before
    assert not any(r["cleanup_deleted_file"] for r in records.values())
    assert len(download.calls) == 1
    missing = sorted(name for name, r in records.items() if r["missing"])
    assert missing == _lower([f"{pair.stem}.jpg", f"{pair.stem}.{raw_type.name}"])
