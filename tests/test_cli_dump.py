"""Test osxphotos dump command."""

import json

import pytest
from click.testing import CliRunner

from osxphotos.cli import dump
from osxphotos.photosdb import PhotosDB

from .test_cli import CLI_PHOTOS_DB

@pytest.fixture
def photos():
    """Return photos from CLI_PHOTOS_DB"""
    return PhotosDB(CLI_PHOTOS_DB).photos(intrash=True)


def test_dump_basic(photos, isolated_fs):
    """Test osxphotos dump"""
    runner = CliRunner()
    result = runner.invoke(dump, ["--db", CLI_PHOTOS_DB, "--deleted"])
    assert result.exit_code == 0
    assert result.output.startswith("uuid,filename")
    for photo in photos:
        assert photo.uuid in result.output


def test_dump_json(photos, isolated_fs):
    """Test osxphotos dump --json"""
    runner = CliRunner()

    result = runner.invoke(dump, ["--db", CLI_PHOTOS_DB, "--deleted", "--json"])
    assert result.exit_code == 0
    json_data = {record["uuid"]: record for record in json.loads(result.output)}
    for photo in photos:
        assert photo.uuid in json_data


def test_dump_print(photos, isolated_fs):
    """Test osxphotos dump --print"""
    runner = CliRunner()

    result = runner.invoke(
        dump,
        [
            "--db",
            CLI_PHOTOS_DB,
            "--deleted",
            "--print",
            "{uuid}{tab}{photo.original_filename}",
        ],
    )
    assert result.exit_code == 0
    for photo in photos:
        assert f"{photo.uuid}\t{photo.original_filename}" in result.output


def test_dump_field(photos, isolated_fs):
    """Test osxphotos dump --field"""
    runner = CliRunner()

    result = runner.invoke(
        dump,
        [
            "--db",
            CLI_PHOTOS_DB,
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


def test_dump_field_json(photos, isolated_fs):
    """Test osxphotos dump --field --jso"""
    runner = CliRunner()
    result = runner.invoke(
        dump,
        [
            "--db",
            CLI_PHOTOS_DB,
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
