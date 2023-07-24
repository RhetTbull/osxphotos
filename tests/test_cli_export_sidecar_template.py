"""Test export with --sidecar-template (#1123)"""

import os
import pathlib

import pytest
from click.testing import CliRunner

from osxphotos.cli import export

PHOTOS_DB = "./tests/Test-10.15.7.photoslibrary"

PHOTO_UUID = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg
SIDECAR_FILENAME = "wedding.jpg.txt"
SIDECAR_DATA = """


Sidecar: wedding.jpg.txt
    Photo: wedding.jpg
    UUID: E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51
    Rating: ★★★★★
"""



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
                "no",
                "no",
                "no",
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
                "no",
                "yes",
                "no",
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
                "no",
                "no",
                "yes",
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
                "no",
                "yes",
                "yes",
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
