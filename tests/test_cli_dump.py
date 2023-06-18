"""Test osxphotos dump command."""

import json
import os
import os.path

import pytest
from click.testing import CliRunner

from osxphotos.cli import dump
from osxphotos.photosdb import PhotosDB

from .test_cli import CLI_PHOTOS_DB


@pytest.fixture
def photos():
    """Return photos from CLI_PHOTOS_DB"""
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    return PhotosDB(db_path).photos(intrash=True)


def test_dump_basic(photos):
    """Test osxphotos dump"""
    runner = CliRunner()
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(dump, ["--db", db_path, "--deleted"])
        assert result.exit_code == 0
        assert result.output.startswith("uuid,filename")
        for photo in photos:
            assert photo.uuid in result.output


def test_dump_json(photos):
    """Test osxphotos dump --json"""
    runner = CliRunner()
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(dump, ["--db", db_path, "--deleted", "--json"])
        assert result.exit_code == 0
        json_data = {record["uuid"]: record for record in json.loads(result.output)}
        for photo in photos:
            assert photo.uuid in json_data


def test_dump_print(photos):
    """Test osxphotos dump --print"""
    runner = CliRunner()
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            dump,
            [
                "--db",
                db_path,
                "--deleted",
                "--print",
                "{uuid}{tab}{photo.original_filename}",
            ],
        )
        assert result.exit_code == 0
        for photo in photos:
            assert f"{photo.uuid}\t{photo.original_filename}" in result.output


def test_dump_field(photos):
    """Test osxphotos dump --field"""
    runner = CliRunner()
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            dump,
            [
                "--db",
                db_path,
                "--deleted",
                "--field",
                "uuid",
                "{uuid}",
                "--field",
                "name",
                "{photo.original_filename}",
            ],
        )
        assert result.exit_code == 0
        for photo in photos:
            assert f"{photo.uuid},{photo.original_filename}" in result.output


def test_dump_field_json(photos):
    """Test osxphotos dump --field --jso"""
    runner = CliRunner()
    cwd = os.getcwd()
    db_path = os.path.join(cwd, CLI_PHOTOS_DB)
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            dump,
            [
                "--db",
                db_path,
                "--deleted",
                "--field",
                "uuid",
                "{uuid}",
                "--field",
                "name",
                "{photo.original_filename}",
                "--json",
            ],
        )
        assert result.exit_code == 0
        json_data = {record["uuid"]: record for record in json.loads(result.output)}
        for photo in photos:
            assert photo.uuid in json_data
            assert json_data[photo.uuid]["name"] == photo.original_filename
