"""Tests for `osxphotos exiftool` command."""

import glob
import json
import os

import pytest
from click.testing import CliRunner

from osxphotos.cli.exiftool_cli import exiftool
from osxphotos.cli.export import export
from osxphotos.exiftool import ExifTool, get_exiftool_path

from .test_cli import CLI_EXIFTOOL, PHOTOS_DB_15_7

# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_export_exiftool():
    """Test osxphotos exiftool"""
    runner = CliRunner()
    cwd = os.getcwd()

    with runner.isolated_filesystem() as temp_dir:
        uuid_option = []
        for uuid in CLI_EXIFTOOL:
            uuid_option.extend(("--uuid", uuid))

        # first, export without --exiftool
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(
            [CLI_EXIFTOOL[uuid]["File:FileName"] for uuid in CLI_EXIFTOOL]
        )

        # now, run exiftool command to update exiftool metadata
        result = runner.invoke(
            exiftool,
            ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "-V", "--db-config", temp_dir],
        )
        assert result.exit_code == 0

        exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
        for key in CLI_EXIFTOOL[uuid]:
            if type(exif[key]) == list:
                assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
            else:
                assert exif[key] == CLI_EXIFTOOL[uuid][key]

        # now, export with --exiftool --update, no files should be updated
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--exiftool",
                "--update",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0
        assert f"exported: 0, updated: 0, skipped: {len(CLI_EXIFTOOL)}" in result.output


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_export_exiftool_album_keyword():
    """Test osxphotos exiftool with --album-template."""
    runner = CliRunner()
    cwd = os.getcwd()

    with runner.isolated_filesystem() as temp_dir:
        # first, export without --exiftool
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--album",
                "Pumpkin Farm",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == 3

        # now, run exiftool command to update exiftool metadata
        result = runner.invoke(
            exiftool,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "-V",
                "--db-config",
                "--report",
                "exiftool.json",
                "--album-keyword",
                temp_dir,
            ],
        )
        assert result.exit_code == 0
        report = json.load(open("exiftool.json", "r"))
        assert len(report) == 3

        # verify exiftool metadata was updated
        for file in report:
            exif = ExifTool(file["filename"]).asdict()
            assert "Pumpkin Farm" in exif["IPTC:Keywords"]

        # now, export with --exiftool --update, no files should be updated
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--exiftool",
                "--update",
                "--album",
                "Pumpkin Farm",
                "--album-keyword",
            ],
        )
        assert result.exit_code == 0
        assert f"exported: 0, updated: 0, skipped: 3" in result.output


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_export_exiftool_keyword_template():
    """Test osxphotos exiftool with --keyword-template."""
    runner = CliRunner()
    cwd = os.getcwd()

    with runner.isolated_filesystem() as temp_dir:
        uuid_option = []
        for uuid in CLI_EXIFTOOL:
            uuid_option.extend(("--uuid", uuid))

        # first, export without --exiftool
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0

        # now, run exiftool command to update exiftool metadata
        result = runner.invoke(
            exiftool,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "-V",
                "--db-config",
                "--keyword-template",
                "FOO",
                temp_dir,
                "--report",
                "exiftool.json",
            ],
        )
        assert result.exit_code == 0

        report = json.load(open("exiftool.json", "r"))
        for file in report:
            exif = ExifTool(file["filename"]).asdict()
            assert "FOO" in exif["IPTC:Keywords"]

        # now, export with --exiftool --update, no files should be updated
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--exiftool",
                "--keyword-template",
                "FOO",
                "--update",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0
        assert f"exported: 0, updated: 0, skipped: {len(CLI_EXIFTOOL)}" in result.output


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_export_exiftool_load_config():
    """Test osxphotos exiftool with --load-config"""
    runner = CliRunner()
    cwd = os.getcwd()

    with runner.isolated_filesystem() as temp_dir:
        uuid_option = []
        for uuid in CLI_EXIFTOOL:
            uuid_option.extend(("--uuid", uuid))

        # first, export without --exiftool
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--save-config",
                "config.toml",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0

        # now, run exiftool command to update exiftool metadata
        result = runner.invoke(
            exiftool,
            ["-V", "--load-config", "config.toml", temp_dir],
        )
        assert result.exit_code == 0

        exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
        for key in CLI_EXIFTOOL[uuid]:
            if type(exif[key]) == list:
                assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
            else:
                assert exif[key] == CLI_EXIFTOOL[uuid][key]

        # now, export with --exiftool --update, no files should be updated
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                temp_dir,
                "-V",
                "--exiftool",
                "--update",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0
        assert f"exported: 0, updated: 0, skipped: {len(CLI_EXIFTOOL)}" in result.output
