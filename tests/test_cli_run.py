"""Tests for `osxphotos run` script validation and GitHub URL handling (#2230)"""

from __future__ import annotations

import pathlib
import sys

import pytest
from click.testing import CliRunner

import osxphotos.cli.param_types
from osxphotos.cli.install_uninstall_run import run, validate_python_file
from osxphotos.utils import github_url_to_raw_url

VALID_SCRIPT = """
import pathlib
import sys

pathlib.Path(sys.argv[1]).write_text("ran")
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><title>osxphotos/examples/count_photos.py at main</title></head>
<body></body>
</html>
"""


@pytest.fixture
def valid_script(tmp_path: pathlib.Path) -> pathlib.Path:
    """A python script that writes 'ran' to the file passed as its first argument"""
    script = tmp_path / "script.py"
    script.write_text(VALID_SCRIPT)
    return script


@pytest.fixture(autouse=True)
def reset_argv(monkeypatch: pytest.MonkeyPatch):
    """run modifies sys.argv and scripts read it; don't expose pytest's argv"""
    monkeypatch.setattr(sys, "argv", ["osxphotos"])


def run_cli(*args: str):
    """Invoke `osxphotos run` with sys.argv set as it would be from the command line"""
    sys.argv = ["osxphotos", "run", *args]
    return CliRunner().invoke(run, list(args))


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://github.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py",
        ),
        (
            "https://github.com/RhetTbull/osxphotos/raw/main/examples/count_photos.py",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py",
        ),
        (
            "http://www.github.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py",
        ),
        (
            "https://github.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py?plain=1#L10-L20",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py",
        ),
        (
            "https://github.com/RhetTbull/osxphotos/blob/feature/branch/examples/script.py",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/feature/branch/examples/script.py",
        ),
        (
            "https://github.com/RhetTbull/osxphotos/blob/2be2970f/examples/count_photos.py",
            "https://raw.githubusercontent.com/RhetTbull/osxphotos/2be2970f/examples/count_photos.py",
        ),
        (
            "https://gist.github.com/RhetTbull/0123456789abcdef",
            "https://gist.githubusercontent.com/RhetTbull/0123456789abcdef/raw",
        ),
    ],
)
def test_github_url_to_raw_url(url: str, expected: str):
    assert github_url_to_raw_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py",
        "https://gist.githubusercontent.com/RhetTbull/0123456789abcdef/raw",
        "https://github.com/RhetTbull/osxphotos",
        "https://github.com/RhetTbull/osxphotos/tree/main/examples",
        "https://example.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py",
        "/path/to/script.py",
    ],
)
def test_github_url_to_raw_url_unchanged(url: str):
    assert github_url_to_raw_url(url) == url


def test_validate_python_file_valid(valid_script: pathlib.Path):
    assert validate_python_file(str(valid_script)) is None


@pytest.mark.parametrize(
    "content,expected",
    [
        (HTML_PAGE, "HTML web page"),
        ("def foo(:\n    pass\n", "does not appear to be a valid Python file"),
        (b"\x00\x01\x02\xff\xfe binary", "does not appear to be a valid Python file"),
    ],
)
def test_validate_python_file_invalid(
    tmp_path: pathlib.Path, content: str | bytes, expected: str
):
    script = tmp_path / "script.py"
    if isinstance(content, bytes):
        script.write_bytes(content)
    else:
        script.write_text(content)
    error = validate_python_file(str(script))
    assert error
    assert expected in error


def test_run_valid_script(valid_script: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / "output.txt"
    result = run_cli(str(valid_script), str(output))
    assert result.exit_code == 0, result.output
    assert output.read_text() == "ran"


def test_run_html_file(tmp_path: pathlib.Path):
    script = tmp_path / "count_photos.py"
    script.write_text(HTML_PAGE)
    result = run_cli(str(script))
    assert result.exit_code == 2
    assert "HTML web page" in result.output


def test_run_github_url(
    monkeypatch: pytest.MonkeyPatch, valid_script: pathlib.Path, tmp_path: pathlib.Path
):
    """GitHub page URL is converted to raw URL before download"""
    downloaded = []

    def mock_download(url: str) -> str:
        downloaded.append(url)
        return str(valid_script)

    monkeypatch.setattr(
        osxphotos.cli.param_types, "download_url_to_temp_dir", mock_download
    )
    output = tmp_path / "output.txt"
    result = run_cli(
        "https://github.com/RhetTbull/osxphotos/blob/main/examples/count_photos.py",
        str(output),
    )
    assert result.exit_code == 0, result.output
    assert downloaded == [
        "https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py"
    ]
    assert output.read_text() == "ran"


def test_run_url_html_download(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path):
    """A URL that downloads an HTML page fails validation instead of running"""
    html_file = tmp_path / "script.py"
    html_file.write_text(HTML_PAGE)
    monkeypatch.setattr(
        osxphotos.cli.param_types,
        "download_url_to_temp_dir",
        lambda url: str(html_file),
    )
    result = run_cli("https://example.com/script.py")
    assert result.exit_code == 2
    assert "HTML web page" in result.output
