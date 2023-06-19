""" Test osxphotos cli commands to verify they run without error.

These tests simply run the commands to verify no errors are thrown. 
They do not verify the output of the commands. More complex tests are
in test_cli.py and test_cli__xxx.py for specific commands.

Complex commands such as export are not tested here.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import pytest
from click.testing import CliRunner

TEST_DB = "tests/Test-13.0.0.photoslibrary"
TEST_DB = os.path.join(os.getcwd(), TEST_DB)
TEST_RUN_SCRIPT = "examples/cli_example_1.py"


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


from osxphotos.cli import (
    about,
    albums,
    debug_dump,
    docs_command,
    dump,
    grep,
    help,
    info,
    keywords,
    labels,
    list_libraries,
    orphans,
    persons,
    places,
    theme,
    tutorial,
    version,
)
from osxphotos.platform import is_macos

if is_macos:
    from osxphotos.cli import uuid


def test_about(runner: CliRunner):
    with runner.isolated_filesystem():
        result = runner.invoke(about)
        assert result.exit_code == 0


@pytest.mark.parametrize(
    "command",
    [
        albums,
        docs_command,
        dump,
        help,
        info,
        keywords,
        labels,
        list_libraries,
        orphans,
        persons,
        places,
        tutorial,
        version,
    ]
    + ([uuid] if is_macos else []),
)
def test_cli_comands(runner: CliRunner, command: Callable[..., Any]):
    with runner.isolated_filesystem():
        result = runner.invoke(albums, ["--db", TEST_DB])
        assert result.exit_code == 0


def test_grep(runner: CliRunner):
    with runner.isolated_filesystem():
        result = runner.invoke(grep, ["--db", TEST_DB, "test"])
        assert result.exit_code == 0


def test_debug_dump(runner: CliRunner):
    with runner.isolated_filesystem():
        result = runner.invoke(debug_dump, ["--db", TEST_DB, "--dump", "persons"])
        assert result.exit_code == 0


def test_theme(runner: CliRunner):
    with runner.isolated_filesystem():
        result = runner.invoke(theme, ["--list"])
        assert result.exit_code == 0
