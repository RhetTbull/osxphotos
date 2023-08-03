"""Test export with --sidecar-template (#1123)"""

import csv
import json
import os
import pathlib
import sqlite3

import pytest
from click.testing import CliRunner

from osxphotos.cli import export

PHOTOS_DB = "./tests/Test-10.15.7.photoslibrary"

PHOTO_UUID = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
SIDECAR_FILENAME = "wedding.jpg.txt"
SIDECAR_FILENAME_2 = "wedding.jpg.sidecar"
SIDECAR_DATA = """


Sidecar: wedding.jpg.txt
    Photo: wedding.jpg
    UUID: E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51
    Rating: ★★★★★
"""
SIDECAR_DATA_2 = """


Sidecar: wedding.jpg.sidecar
    Photo: wedding.jpg
    UUID: E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51
    Rating: ★★★★★
"""

PHOTO_UUID_NO_KEYWORD = "4D521201-92AC-43E5-8F7C-59BC41C37A96"  # IMG_1997.CR2
SIDECAR_FILENAME_NO_KEYWORD = "IMG_1997.CR2.txt"


def test_export_sidecar_template_1():
    """test basic export with --sidecar-template"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        assert sidecar_data == SIDECAR_DATA


def test_export_sidecar_template_option_case():
    """test basic export with --sidecar-template and option case insensitivity"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "None",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        assert sidecar_data == SIDECAR_DATA


def test_export_sidecar_template_strip_whitespace():
    """test basic export with --sidecar-template and STRIP_WHITESPACE = True"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "strip_whitespace",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = (
            "\n".join(line.strip() for line in SIDECAR_DATA.splitlines()) + "\n"
        )
        assert sidecar_data == sidecar_expected


def test_export_sidecar_template_strip_lines():
    """test basic export with --sidecar-template and STRIP_LINES = True"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "strip_lines",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = "\n".join(
            line for line in SIDECAR_DATA.splitlines() if line.strip()
        )
        assert sidecar_data == sidecar_expected


def test_export_sidecar_template_strip_lines_strip_whitespace():
    """test basic export with --sidecar-template and STRIP_LINES = True and STRIP_WHITESPACE = True"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "strip_whitespace,strip_lines",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = "\n".join(
            line.strip() for line in SIDECAR_DATA.splitlines() if line.strip()
        )
        assert sidecar_data == sidecar_expected


def test_export_sidecar_template_strip_lines_strip_whitespace_option_space():
    """test basic export with --sidecar-template and STRIP_LINES = True and STRIP_WHITESPACE = True with space in option"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "strip_whitespace, strip_lines",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = "\n".join(
            line.strip() for line in SIDECAR_DATA.splitlines() if line.strip()
        )
        assert sidecar_data == sidecar_expected


def test_export_sidecar_template_update_no():
    """test basic export with --sidecar-template and WRITE_SKIPPED = False, also test --cleanup"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
            ],
        )

        # run export again, should not update sidecar
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
                "--update",
                "--cleanup",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = "\n".join(
            line.strip() for line in SIDECAR_DATA.splitlines() if line.strip()
        )
        assert sidecar_data == SIDECAR_DATA
        assert "Skipping existing sidecar file" in result.output
        assert "Deleted: 0 files, 0 directories" in result.output


def test_export_sidecar_template_update_ues():
    """test basic export with --sidecar-template and WRITE_SKIPPED = True, also test --cleanup"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
            ],
        )

        # run export again, should not update sidecar
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "write_skipped",
                "--update",
                "--cleanup",
            ],
        )
        assert result.exit_code == 0
        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        sidecar_expected = "\n".join(
            line.strip() for line in SIDECAR_DATA.splitlines() if line.strip()
        )
        assert sidecar_data == SIDECAR_DATA
        assert "Skipping existing sidecar file" not in result.output
        assert "Writing sidecar file" in result.output
        assert "Deleted: 0 files, 0 directories" in result.output


def test_export_sidecar_template_report_csv():
    """test basic export with --sidecar-template --report to csv"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
                "--report",
                "report.csv",
            ],
        )
        assert result.exit_code == 0

        # verify report output
        report_file = pathlib.Path("report.csv")
        assert report_file.exists()
        csvreader = csv.DictReader(report_file.open())
        assert "sidecar_user" in csvreader.fieldnames

        found_sidecar = 0
        for row in csvreader:  # sourcery skip: no-loop-in-tests
            # sidecar ends with .txt so verify report has sidecar_user = 1
            if row["filename"].endswith(
                ".txt"
            ):  # sourcery skip: no-conditionals-in-tests
                assert str(row["sidecar_user"]) == "1"
                found_sidecar += 1
            else:
                assert str(row["sidecar_user"]) == "0"
        assert found_sidecar


def test_export_sidecar_template_report_json():
    """test basic export with --sidecar-template --report to json"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
                "--report",
                "report.json",
            ],
        )
        assert result.exit_code == 0

        # read the json report output and verify it is correct
        report_file = pathlib.Path("report.json")
        assert report_file.exists()
        report_data = json.loads(report_file.read_text())
        assert "sidecar_user" in report_data[0]
        found_sidecar = 0
        for row in report_data:  # sourcery skip: no-loop-in-tests
            # sidecar ends with .txt so verify report has sidecar_user = 1
            if row["filename"].endswith(
                ".txt"
            ):  # sourcery skip: no-conditionals-in-tests
                assert row["sidecar_user"]
                found_sidecar += 1
            else:
                assert not row["sidecar_user"]
        assert found_sidecar


def test_export_sidecar_template_report_db():
    """test basic export with --sidecar-template --report to sqlite db"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
                "--report",
                "report.db",
            ],
        )
        assert result.exit_code == 0

        # read the report sqlite db and verify it is correct
        report_file = pathlib.Path("report.db")
        assert report_file.exists()
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename, sidecar_user FROM report")
        rows = c.fetchall()
        found_sidecar = 0
        for row in rows:  # sourcery skip: no-loop-in-tests
            # sidecar ends with .txt so verify report has sidecar_user = 1
            if row[0].endswith(".txt"):  # sourcery skip: no-conditionals-in-tests
                assert row[1] == 1
                found_sidecar += 1
            else:
                assert row[1] == 0
        assert found_sidecar


def test_export_sidecar_template_multiple():
    """test export with multiple --sidecar-template options"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.sidecar",
                "none",
            ],
        )
        assert result.exit_code == 0

        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        assert sidecar_data == SIDECAR_DATA

        sidecar_file = pathlib.Path(SIDECAR_FILENAME_2)
        assert sidecar_file.exists()
        sidecar_data = sidecar_file.read_text()
        assert sidecar_data == SIDECAR_DATA_2


def test_export_sidecar_template_full_library():
    """test export with --sidecar-template option against full library (repeated calls to generate sidecar files))"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar.mako"),
                "{filepath}.txt",
                "none",
            ],
        )
        assert result.exit_code == 0


def test_export_sidecar_template_skip_zero():
    """test basic export with --sidecar-template with skip_zero option"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--uuid",
                PHOTO_UUID_NO_KEYWORD,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar_zero.mako"),
                "{filepath}.txt",
                "strip_whitespace,strip_lines,skip_zero",
            ],
        )
        assert result.exit_code == 0

        assert "Skipping empty sidecar file" in result.output

        sidecar_file = pathlib.Path(SIDECAR_FILENAME)
        assert sidecar_file.exists()

        sidecar_file = pathlib.Path(SIDECAR_FILENAME_NO_KEYWORD)
        assert not sidecar_file.exists()


def test_export_sidecar_template_error():
    """test basic export with --sidecar-template that generates an error"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar_bad.mako"),
                "{filepath}.txt",
                "none",
            ],
        )
        assert result.exit_code != 0


def test_export_sidecar_template_catch_error():
    """test basic export with --sidecar-template that catches an error"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                PHOTO_UUID,
                "--sidecar-template",
                os.path.join(cwd, "tests", "custom_sidecar_bad.mako"),
                "{filepath}.txt",
                "catch_errors",
            ],
        )
        assert result.exit_code == 0
