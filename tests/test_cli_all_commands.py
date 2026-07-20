"""Test osxphotos cli commands to verify they run without error.

These tests simply run the commands to verify no errors are thrown.
They do not verify the output of the commands. More complex tests are
in test_cli.py and test_cli__xxx.py for specific commands.

Complex commands such as export are not tested here.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any, Callable

import pytest
from click.testing import CliRunner

import osxphotos.cli.common as cli_common

TEST_DB = "tests/Test-13.0.0.photoslibrary"
TEST_DB = os.path.join(os.getcwd(), TEST_DB)
TEST_RUN_SCRIPT = "examples/cli_example_1.py"


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


from osxphotos.cli import (
    about,
    albums,
    cli_main,
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


def test_cli_commands_install_crash_reporter():
    for command in cli_main.commands.values():
        if command.callback is not None:
            assert getattr(command.callback, "__osxphotos_crash_reporter__", False)


def test_cli_command_crash_reporter_handles_unexpected_errors(
    runner: CliRunner, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    crash_log = tmp_path / "osxphotos_crash.log"

    def crash(*args, **kwargs):
        raise RuntimeError("boom from test")

    monkeypatch.setattr(cli_common, "OSXPHOTOS_CRASH_LOG", str(crash_log))
    monkeypatch.setattr(about, "callback", crash)
    cli_common.install_crash_reporter(about)

    result = runner.invoke(cli_main, ["about"])

    assert result.exit_code == 1
    assert "Something went wrong and osxphotos encountered an error" in result.output
    assert "boom from test" in crash_log.read_text()


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
