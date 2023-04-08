"""Test that libraries containing projects are handled correctly, #999"""

import os

import pytest
from click.testing import CliRunner

from osxphotos.cli import export

PHOTOS_DB_PROJECTS = "./tests/Test-iPhoto-Projects-10.15.7.photoslibrary"


def test_export_projects():
    """test basic export with library containing projects"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, ["--library", os.path.join(cwd, PHOTOS_DB_PROJECTS), ".", "-V"]
        )
        assert result.exit_code == 0
        assert "error: 0" in result.output
