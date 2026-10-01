"""Test that the export command requires macOS."""

from importlib import import_module

from click.testing import CliRunner

from .conftest import fixture_path

export_module = import_module("osxphotos.cli.export")

TEST_LIBRARY = fixture_path("./tests/Test-10.14.5.photoslibrary")


def test_add_exported_to_album(monkeypatch, isolated_fs):
    """Using option on non-macOS should error"""
    monkeypatch.setattr("osxphotos.platform.is_macos", False)
    monkeypatch.setattr("osxphotos.cli.common.is_macos", False)

    export = export_module.export
    runner = CliRunner()

    result = runner.invoke(
        export,
        [
            ".",
            "--library",
            TEST_LIBRARY,
            "--add-exported-to-album",
            "SomeAlbum",
        ],
    )
    assert result.exit_code == 2
    assert "only works on macOS" in result.output
