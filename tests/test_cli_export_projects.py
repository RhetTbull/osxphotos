"""Test that libraries containing projects are handled correctly, #999"""

import pytest
from click.testing import CliRunner

from osxphotos.cli import export

from .conftest import repo_path

PHOTOS_DB_PROJECTS = repo_path("./tests/Test-iPhoto-Projects-10.15.7.photoslibrary")


def test_export_projects(isolated_fs):
    """test basic export with library containing projects"""
    runner = CliRunner()

    result = runner.invoke(export, ["--library", PHOTOS_DB_PROJECTS, ".", "-V"])
    assert result.exit_code == 0
    assert "error: 0" in result.output
