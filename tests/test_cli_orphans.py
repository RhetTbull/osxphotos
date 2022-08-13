"""Test `osxphotos orphan` CLI"""

import os.path

from click.testing import CliRunner

from osxphotos.cli.orphans import orphans

from .test_cli import PHOTOS_DB_15_7


def test_orphans():
    """test basic orphans"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            orphans, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "-V"]
        )
        assert result.exit_code == 0
        assert "Found 1 orphan" in result.output


def test_orphans_export():
    """test export of orphans"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            orphans, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "--export", ".", "-V"]
        )
        assert result.exit_code == 0
        assert "Exported 1 file" in result.output
