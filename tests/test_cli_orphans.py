"""Test `osxphotos orphan` CLI"""

import os.path

from click.testing import CliRunner

from osxphotos.cli.orphans import orphans

from .test_cli import PHOTOS_DB_15_7


def test_orphans(isolated_fs):
    """test basic orphans"""
    runner = CliRunner()

    result = runner.invoke(orphans, ["--db", PHOTOS_DB_15_7, "-V"])
    assert result.exit_code == 0
    assert "Found 1 orphan" in result.output


def test_orphans_export(isolated_fs):
    """test export of orphans"""
    runner = CliRunner()

    result = runner.invoke(orphans, ["--db", PHOTOS_DB_15_7, "--export", ".", "-V"])
    assert result.exit_code == 0
    assert "Exported 1 file" in result.output
