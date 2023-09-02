"""Test osxphotos push-exif command"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import shutil
import sqlite3

import pytest
from click.testing import CliRunner

from osxphotos import PhotoInfo, PhotosDB
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("Skipping macos-only tests", allow_module_level=True)

from osxphotos.cli.push_exif import push_exif

try:
    exiftool = get_exiftool_path()
except Exception:
    exiftool = None

if exiftool is None:
    pytest.skip("could not find exiftool in path", allow_module_level=True)


PHOTOS_DB = "tests/Test-13.0.0.photoslibrary/"
CWD = os.getcwd()

UUID_MISSING = "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"  # Pumpkins4.jpg
UUID_KEYWORDS_PERSONS = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
UUID_FAVORITE = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
UUID_NOT_FAVORITE = UUID_KEYWORDS_PERSONS
UUID_DATE_MODIFIED = UUID_FAVORITE


def copy_photos_library(dest):
    """Make a copy of the Photos library for testing"""
    return shutil.copytree(os.path.join(CWD, PHOTOS_DB), dest)


def get_exiftool_keywords(photo: PhotoInfo) -> list[str]:
    """Get IPTC keywords from a photo's original file"""
    exif = ExifTool(photo.path).asdict()
    if "IPTC:Keywords" not in exif:
        return []
    if isinstance(exif["IPTC:Keywords"], str):
        return sorted([exif["IPTC:Keywords"]])
    return sorted(exif["IPTC:Keywords"])


def get_exiftool_persons(photo: PhotoInfo) -> list[str]:
    """Get XMP persons from a photo's original file"""
    exif = ExifTool(photo.path).asdict()
    if "XMP:PersonInImage" not in exif:
        return []
    if isinstance(exif["XMP:PersonInImage"], str):
        return sorted([exif["XMP:PersonInImage"]])
    return sorted(exif["XMP:PersonInImage"])


def get_exiftool_description(photo: PhotoInfo) -> str:
    """Get EXIF description from a photo's original file"""
    exif = ExifTool(photo.path).asdict()
    return exif.get("EXIF:ImageDescription", "")


def set_exiftool_keywords(photo: PhotoInfo, keywords: list[str]):
    """Set IPTC keywords in a photo's original file"""
    with ExifTool(photo.path) as exiftool:
        for keyword in keywords:
            exiftool.setvalue("IPTC:Keywords", keyword)


def set_exiftool_persons(photo: PhotoInfo, persons: list[str]):
    """Set XMP persons in a photo's original file"""
    with ExifTool(photo.path) as exiftool:
        for person in persons:
            exiftool.setvalue("XMP:PersonInImage", person)


def test_cli_push_exif_basic(monkeypatch):
    """Test push-exif command"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(push_exif, ["-V", "--force", "--library", test_library])
        assert result.exit_code == 0
        assert (
            "Summary: 14 written, 0 updated, 0 skipped, 3 missing, 0 warning, 0 error"
            in result.output
        )

        # verify keywords and persons were pushed
        photosdb = PhotosDB(test_library)
        photo = photosdb.get_photo(UUID_KEYWORDS_PERSONS)
        assert sorted(photo.keywords) == get_exiftool_keywords(photo)
        assert sorted(photo.persons) == get_exiftool_persons(photo)


def test_cli_push_exif_exiftool_option(monkeypatch):
    """Test push-exif command with --exiftool-option"""
    # NOTE: Currently no photos that generate warnings in exiftool so can't test that
    # the -m option is actually working, just that it's passed to exiftool and doesn't generate error
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--exiftool-option", "-m"],
        )
        assert result.exit_code == 0
        assert (
            "Summary: 14 written, 0 updated, 0 skipped, 3 missing, 0 warning, 0 error"
            in result.output
        )


def test_cli_push_exif_exiftool_merge_keywords(monkeypatch):
    """Test push-exif command with --exiftool-merge-keywords"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))

        photosdb = PhotosDB(test_library)
        photo = photosdb.get_photo(UUID_KEYWORDS_PERSONS)

        set_exiftool_keywords(photo, ["Foo", "Bar"])
        set_exiftool_persons(photo, ["JaneDoe"])

        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--exiftool-merge-keywords"],
        )
        assert result.exit_code == 0
        assert (
            "Summary: 14 written, 0 updated, 0 skipped, 3 missing, 0 warning, 0 error"
            in result.output
        )

        # verify keywords and persons were pushed and merged appropriately
        assert sorted(photo.keywords + ["Foo", "Bar"]) == get_exiftool_keywords(photo)
        assert sorted(photo.persons) == get_exiftool_persons(photo)


def test_cli_push_exif_exiftool_merge_persons(monkeypatch):
    """Test push-exif command with --exiftool-merge-persons"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))

        photosdb = PhotosDB(test_library)
        photo = photosdb.get_photo(UUID_KEYWORDS_PERSONS)

        set_exiftool_keywords(photo, ["Foo", "Bar"])
        set_exiftool_persons(photo, ["JaneDoe"])

        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--exiftool-merge-persons"],
        )
        assert result.exit_code == 0
        assert (
            "Summary: 14 written, 0 updated, 0 skipped, 3 missing, 0 warning, 0 error"
            in result.output
        )

        # verify keywords and persons were pushed and merged appropriately
        assert sorted(photo.keywords) == get_exiftool_keywords(photo)
        assert sorted(photo.persons + ["JaneDoe"]) == get_exiftool_persons(photo)


def test_cli_push_exif_report_csv(monkeypatch):
    """Test push-exif command with --report csv"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--report", "report.csv"],
        )
        assert result.exit_code == 0
        report_data = list(csv.DictReader(open("report.csv")))
        assert len(report_data) == 17
        missing = [row for row in report_data if row["uuid"] == UUID_MISSING][0]
        assert missing["missing"] == "original"


def test_cli_push_exif_report_json(monkeypatch):
    """Test push-exif command with --report json"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--report", "report.json"],
        )
        assert result.exit_code == 0
        with open("report.json", "r") as fp:
            report_data = json.load(fp)
        assert len(report_data) == 14
        missing = [row for row in report_data if row["uuid"] == UUID_MISSING][0]
        assert missing["missing"] == ["original"]


def test_cli_push_exif_report_sqlite(monkeypatch):
    """Test push-exif command with --report sqlite"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            ["-V", "--force", "--library", test_library, "--report", "report.db"],
        )
        assert result.exit_code == 0
        conn = sqlite3.connect("report.db")
        conn.row_factory = sqlite3.Row
        report_data = list(conn.execute("SELECT * FROM report").fetchall())
        assert len(report_data) == 17
        missing = [row for row in report_data if row["uuid"] == UUID_MISSING][0]
        assert missing["missing"] == "original"


def test_cli_push_exif_favorite_rating(monkeypatch):
    """Test push-exif command with --favorite-rating"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            [
                "-V",
                "--force",
                "--library",
                test_library,
                "--uuid",
                UUID_FAVORITE,
                "--uuid",
                UUID_NOT_FAVORITE,
                "--favorite-rating",
            ],
        )
        assert result.exit_code == 0

        # verify XMP:Rating was set to 5 or 0
        photosdb = PhotosDB(test_library)
        photo = photosdb.get_photo(UUID_FAVORITE)
        assert photo.exiftool.asdict()["XMP:Rating"] == 5

        photo = photosdb.get_photo(UUID_NOT_FAVORITE)
        assert photo.exiftool.asdict()["XMP:Rating"] == 0


def test_cli_push_exif_ignore_date_modified(monkeypatch):
    """Test push-exif command with --ignore-date-modified"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            [
                "-V",
                "--force",
                "--library",
                test_library,
                "--uuid",
                UUID_DATE_MODIFIED,
                "--ignore-date-modified",
            ],
        )
        assert result.exit_code == 0

        photo = PhotosDB(test_library).get_photo(UUID_DATE_MODIFIED)
        date_modified = photo.exiftool.asdict()["EXIF:ModifyDate"]
        assert date_modified == photo.date.strftime("%Y:%m:%d %H:%M:%S")


def test_cli_push_exif_person_keyword_album_keyword(monkeypatch):
    """Test push-exif command with --person-keyword and --album-keyword"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            [
                "-V",
                "--force",
                "--library",
                test_library,
                "--uuid",
                UUID_KEYWORDS_PERSONS,
                "--person-keyword",
                "--album-keyword",
            ],
        )
        assert result.exit_code == 0

        photo = PhotosDB(test_library).get_photo(UUID_KEYWORDS_PERSONS)
        keywords = get_exiftool_keywords(photo)
        assert keywords == sorted(photo.keywords + photo.persons + photo.albums)


def test_cli_push_exif_keyword_description_template(monkeypatch):
    """Test push-exif command with --keyword-template and --description-template"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            [
                "-V",
                "--force",
                "--library",
                test_library,
                "--uuid",
                UUID_KEYWORDS_PERSONS,
                "--keyword-template",
                "{title}",
                "--keyword-template",
                "FOO",
                "--description-template",
                "{descr} - {title}",
            ],
        )
        assert result.exit_code == 0

        photo = PhotosDB(test_library).get_photo(UUID_KEYWORDS_PERSONS)
        keywords = get_exiftool_keywords(photo)
        assert keywords == sorted(photo.keywords + [photo.title] + ["FOO"])
        assert get_exiftool_description(photo) == f"{photo.description} - {photo.title}"


def test_cli_push_exif_replace_keywords(monkeypatch):
    """Test push-exif command with --replace-keywords"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = pathlib.Path(os.getcwd())
        monkeypatch.setattr("xdg.xdg_data_home", lambda: cwd)
        test_library = copy_photos_library(os.path.join(cwd, "Test.photoslibrary"))
        result = runner.invoke(
            push_exif,
            [
                "-V",
                "--force",
                "--library",
                test_library,
                "--uuid",
                UUID_KEYWORDS_PERSONS,
                "--keyword-template",
                "{title}",
                "--keyword-template",
                "FOO",
                "--replace-keywords",
            ],
        )
        assert result.exit_code == 0

        photo = PhotosDB(test_library).get_photo(UUID_KEYWORDS_PERSONS)
        keywords = get_exiftool_keywords(photo)
        assert keywords == sorted([photo.title] + ["FOO"])
