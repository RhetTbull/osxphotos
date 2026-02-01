"""Test dbversion command"""

import pytest
from click.testing import CliRunner

from osxphotos.cli import dbversion
from osxphotos.photosdb import PhotosDB

from .test_cli import CLI_PHOTOS_DB


def test_dbversion():
    runner = CliRunner()
    result = runner.invoke(dbversion, [CLI_PHOTOS_DB])
    assert result.exit_code == 0
    assert "Database path: " in result.output
    assert "Photos version: 5" in result.output
    assert "DB version: 5001" in result.output
    assert "Model version: 13703" in result.output


def test_dbversion_schema():
    runner = CliRunner()
    result = runner.invoke(dbversion, [CLI_PHOTOS_DB, "--schema"])
    assert result.exit_code == 0
    assert "CREATE TABLE" in result.output
