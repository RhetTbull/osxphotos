"""Test the `template` command of the CLI.  """

import pytest
from click.testing import CliRunner

from osxphotos.cli.template_repl import template_repl

from .conftest import TEST_LIBRARY

TEST_UUID = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg


def test_template():
    """Test osxphotos template command"""

    runner = CliRunner()
    results = runner.invoke(
        template_repl,
        ["--db", TEST_LIBRARY, "--uuid", TEST_UUID, "--template", "{descr}"],
    )
    assert results.output == "Bride Wedding day\n"


def test_template_unknown_template():
    """Test osxphotos template command with unknown keyword in template"""

    runner = CliRunner()
    results = runner.invoke(
        template_repl,
        ["--db", TEST_LIBRARY, "--uuid", TEST_UUID, "--template", "{desc}"],
    )
    assert "Unknown template" in results.output


def test_template_repl(monkeypatch):
    """Test osxphotos template command"""

    commands = ["descr={descr}", ":quit"]

    def _input(_):
        # mock input() for REPL
        # can't use yield because REPL expects a string not a generator
        command = commands.pop(0)
        return f"{command}\n"

    monkeypatch.setattr("builtins.input", _input)
    monkeypatch.setattr("readline.read_history_file", lambda x: None)
    monkeypatch.setattr("readline.write_history_file", lambda x: None)
    runner = CliRunner()
    results = runner.invoke(
        template_repl,
        ["--db", TEST_LIBRARY, "--uuid", TEST_UUID],
    )
    assert "descr=Bride Wedding day" in results.output


def test_template_repl_unknown(monkeypatch):
    """Test osxphotos template command"""

    commands = ["descr={descr}", ":quit"]

    def _input(_):
        # mock input() for REPL
        # can't use yield because REPL expects a string not a generator
        command = commands.pop(0)
        return f"{command}\n"

    monkeypatch.setattr("builtins.input", _input)
    monkeypatch.setattr("readline.read_history_file", lambda x: None)
    monkeypatch.setattr("readline.write_history_file", lambda x: None)
    runner = CliRunner()
    results = runner.invoke(
        template_repl,
        ["--db", TEST_LIBRARY, "--uuid", TEST_UUID],
    )
    assert "descr=Bride Wedding day" in results.output
