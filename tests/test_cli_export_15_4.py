"""Test basic export on macOS 15.4"""

import os

from click.testing import CliRunner

from osxphotos.cli import export

from .conftest import test_repo_path

TEST_LIBRARY = test_repo_path("tests/Test-15.4.1.photoslibrary")


def test_export(isolated_fs):
    """test basic export"""
    runner = CliRunner()

    result = runner.invoke(export, [".", "--library", TEST_LIBRARY, "-V"])
    assert result.exit_code == 0
