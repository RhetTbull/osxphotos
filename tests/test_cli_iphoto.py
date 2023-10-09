"""Test osxphotos CLI commands with iPhoto library; simple tests just to ensure commands run without error"""

import os

import pytest
from click.testing import CliRunner

from osxphotos.cli import albums, export, info, keywords, persons, query

from .test_cli import IPHOTO_LIBRARY

UUID = "RgISIEPbThGVoco5LyiLjQ"  # wedding.jpg

LIBRARY_PATH = os.path.join(os.getcwd(), IPHOTO_LIBRARY)


def test_query_iphoto():
    """Test query command with iPhoto library"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(query, ["--library", LIBRARY_PATH, "--uuid", UUID])
        assert result.exit_code == 0
        assert UUID in result.output


@pytest.mark.parametrize("command", [persons, albums, keywords, info])
def test_info_iphoto(command):
    """Test commands run with iPhoto library"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(command, ["--library", LIBRARY_PATH])
        assert result.exit_code == 0


def test_export_iphoto():
    """Test export command with iPhoto library"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [".", "--library", LIBRARY_PATH, "--verbose", "--uuid", UUID]
        )
        assert result.exit_code == 0
        assert "exported: 2" in result.output  # edited version + original
        files = os.listdir(os.getcwd())
        assert "wedding.jpg" in files
        assert "wedding_edited.jpeg" in files
