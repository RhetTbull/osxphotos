"""Test that `osxphotos export --ramdb` does not leak its crash callback.

The export command registers a global crash callback (to flush the in-memory
database if a crash occurs). It must be unregistered on every exit path -- on
success, when no photos match, and when the export crashes -- otherwise the
stale callback lingers in the global registry and fires (with stale state) on a
later, unrelated crash in the same process.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

import osxphotos.crash_reporter as crash_reporter_module
from osxphotos.cli import export

from tests.conftest import fixture_path

# The test library is a copy of the Photos library from macOS 10.15.7.

CLI_PHOTOS_DB = fixture_path("tests/Test-10.15.7.photoslibrary")
# a syntactically valid UUID that does not exist in the test library
NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def clear_callbacks():
    """Ensure the global crash callback registry is clean around each test."""
    crash_reporter_module._global_callbacks.clear()
    yield
    crash_reporter_module._global_callbacks.clear()


def test_export_ramdb_no_leak_on_success(isolated_fs):
    """A successful --ramdb export leaves no crash callback registered."""
    runner = CliRunner()

    result = runner.invoke(
        export,
        [".", "--library", CLI_PHOTOS_DB, "-V", "--ramdb"],
    )
    assert result.exit_code == 0
    assert crash_reporter_module._global_callbacks == {}


def test_export_ramdb_no_leak_on_no_photos(isolated_fs):
    """A --ramdb export that matches no photos leaves no crash callback registered.

    No crash occurs here, so the crash reporter is never involved -- this
    isolates export_cli's own success-path cleanup, which previously lived
    inside the `if photos:` block and was skipped when nothing matched.
    """
    runner = CliRunner()
    result = runner.invoke(
        export,
        [
            ".",
            "--library",
            CLI_PHOTOS_DB,
            "-V",
            "--ramdb",
            "--uuid",
            NONEXISTENT_UUID,
        ],
    )
    assert result.exit_code == 0
    assert "Did not find any photos to export" in result.output
    assert crash_reporter_module._global_callbacks == {}


def test_export_ramdb_no_leak_on_crash(isolated_fs):
    """A crashed --ramdb export flushes the database and leaves no callback registered."""
    runner = CliRunner()

    result = runner.invoke(
        export,
        [
            ".",
            "--library",
            CLI_PHOTOS_DB,
            "-V",
            "--ramdb",
            "--crash-after",
            1,
        ],
    )
    assert result.exit_code != 0
    assert "Writing export database" in result.output
    assert crash_reporter_module._global_callbacks == {}
