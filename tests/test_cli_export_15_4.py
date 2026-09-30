"""Test basic export on macOS 15.4"""

import os

from click.testing import CliRunner

from osxphotos.cli import export

from .conftest import fixture_path

TEST_LIBRARY = fixture_path("tests/Test-15.4.1.photoslibrary")


def test_export(isolated_fs):
    """test basic export"""
    runner = CliRunner()

    result = runner.invoke(
        export, [".", "--library", TEST_LIBRARY, "-V"]
    )
    assert result.exit_code == 0
