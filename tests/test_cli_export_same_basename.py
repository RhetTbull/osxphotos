"""Test export of photos with same basename (see #2045, #2110)"""

import glob
import json
import os
import pathlib
from typing import Any

import pytest
from click.testing import CliRunner

from osxphotos.cli import export

TEST_LIBRARY = "tests/Test-Live-15.7.2.photoslibrary"

EXPORT_RESULTS = {
    "ACF2FC98-C2AA-429E-A3CF-257230F29188": ["IMG_1994 (2).cr2"],
    "B52DB84A-888E-4704-9249-1B042D99D8E9": ["IMG_1994.JPG", "IMG_1994.cr2"],
    "DE34ADE0-2795-4402-9A2C-32016EB868E1": ["IMG_1994 (1).JPG"],
    "CA36ACE0-896D-4AD2-A9E2-2CCD6D8ECE48": [
        "IMG_1994 (3).JPG",
        "IMG_1994_edited (3).jpeg",
    ],
    "A0002D0F-7D4E-40F5-BA53-8A11096B1E6B": ["IMG_4062.mov"],
    "C3090F66-942C-41D3-BEC7-4F2B4876A109": ["IMG_4062 (1).HEIC", "IMG_4062 (1).mov"],
    "33E8AB6B-1B8B-4911-9122-9583333DF028": ["IMG_8946 (1).JPG"],
    "139C21B9-4E28-486C-A168-A870459146C5": [
        "IMG_8946 (1) (1).JPG",
        "IMG_8946 (1)_edited (1).jpeg",
    ],
    "322B8A3F-9DD5-4738-92B4-D5FB3B53B727": ["IMG_8946 (1) (2).JPG"],
}

EXPORT_RESULTS_NEWEST_FIRST = {
    "CA36ACE0-896D-4AD2-A9E2-2CCD6D8ECE48": ["IMG_1994.JPG", "IMG_1994_edited.jpeg"],
    "ACF2FC98-C2AA-429E-A3CF-257230F29188": ["IMG_1994 (1).cr2"],
    "B52DB84A-888E-4704-9249-1B042D99D8E9": ["IMG_1994 (3).JPG", "IMG_1994 (3).cr2"],
    "DE34ADE0-2795-4402-9A2C-32016EB868E1": ["IMG_1994 (2).JPG"],
    "A0002D0F-7D4E-40F5-BA53-8A11096B1E6B": ["IMG_4062 (1).mov"],
    "C3090F66-942C-41D3-BEC7-4F2B4876A109": ["IMG_4062.HEIC", "IMG_4062.mov"],
    "33E8AB6B-1B8B-4911-9122-9583333DF028": ["IMG_8946 (1) (2).JPG"],
    "139C21B9-4E28-486C-A168-A870459146C5": [
        "IMG_8946 (1) (1).JPG",
        "IMG_8946 (1)_edited (1).jpeg",
    ],
    "322B8A3F-9DD5-4738-92B4-D5FB3B53B727": ["IMG_8946 (1).JPG"],
}

EXPORTED_TOTAL = 13


def get_results_for_uuid(results: list[dict[str, Any]], uuid: str) -> list[str]:
    """Get results for a given UUID from a export results dictionary"""
    values = []
    for result in results:
        if result.get("uuid") == uuid:
            values.append(result)
    return sorted([pathlib.Path(x.get("filename")).name for x in values])


def test_export_same_basename():
    """test export with photos with same basename (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: {EXPORTED_TOTAL}, missing: 0" in result.output


def test_export_same_basename_then_update():
    """test export with photos with same basename followed by --update (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: {EXPORTED_TOTAL}, missing: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output


def test_export_same_basename_update():
    """test export with photos with same basename and --update (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: {EXPORTED_TOTAL}, updated: 0, skipped: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output


def test_export_same_basename_then_update_newest_first():
    """test export with photos with same basename with --newest-first followed by --update (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--newest-first",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: {EXPORTED_TOTAL}, missing: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--newest-first",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output


def test_export_same_basename_oldest_then_newest():
    """test export with photos with same basename with different order (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: {EXPORTED_TOTAL}, missing: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--newest-first",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output


def test_export_same_basename_newest_then_oldest():
    """test export with photos with same basename with different order (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--newest-first",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: {EXPORTED_TOTAL}, updated: 0, skipped: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output


def test_export_same_basename_newest_then_oldest_then_newest():
    """test export with photos with same basename with different order (e.g. Live pair and a video with same basename) #2045, #2110"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--newest-first",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: {EXPORTED_TOTAL}, updated: 0, skipped: 0" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "-V",
                "--update",
                "--newest-first",
                "--report",
                "export.json",
            ],
        )
        assert result.exit_code == 0
        with open("export.json", "rb") as fd:
            results = json.load(fd)

        for uuid in EXPORT_RESULTS_NEWEST_FIRST:
            files = get_results_for_uuid(results, uuid)
            assert files == EXPORT_RESULTS_NEWEST_FIRST[uuid]

        assert f"exported: 0, updated: 0, skipped: {EXPORTED_TOTAL}" in result.output
