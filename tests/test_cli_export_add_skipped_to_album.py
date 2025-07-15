import os

from click.testing import CliRunner

from osxphotos.cli import export

TEST_DB = "tests/Test-15.4.1.photoslibrary"


def test_add_exported_to_album_option_hidden(monkeypatch):
    """Option should not appear in --help on non-macOS"""
    runner = CliRunner()

    monkeypatch.setattr("osxphotos.platform.is_macos", False)
    result = runner.invoke(export, ["--help"])
    assert result.exit_code == 0
    assert "--add-exported-to-album" not in result.output

    monkeypatch.setattr("osxphotos.platform.is_macos", True)
    result = runner.invoke(export, ["--help"])
    assert result.exit_code == 0
    assert "--add-exported-to-album" in result.output


def test_add_exported_to_album(monkeypatch):
    """Using option on non-macOS should error"""
    runner = CliRunner()
    cwd = os.getcwd()
    
    monkeypatch.setattr("osxphotos.platform.is_macos", False)
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_DB),
                "--add-exported-to-album",
                "SomeAlbum",
            ],
        )
        assert result.exit_code == 2
        assert "only works on macOS" in result.output

    monkeypatch.setattr("osxphotos.platform.is_macos", True)
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_DB),
                "--add-exported-to-album",
                "SomeAlbum",
            ],
        )
        assert result.exit_code == 0
