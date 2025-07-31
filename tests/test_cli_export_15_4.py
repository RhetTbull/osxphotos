"""Test basic export on macOS 15.4"""

import os

from click.testing import CliRunner

from osxphotos.cli import export

TEST_LIBRARY = "tests/Test-15.4.1.photoslibrary"


def test_export():
    """test basic export"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [".", "--library", os.path.join(cwd, TEST_LIBRARY), "-V"]
        )
        assert result.exit_code == 0
