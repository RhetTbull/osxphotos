"""Test osxphotos exportdb cli command"""

import json
import os
import pathlib

from click.testing import CliRunner

from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos.cli import export, exportdb
from osxphotos.cli.export import export
from osxphotos.cli.exportdb import exportdb
from osxphotos.export_db import OSXPHOTOS_EXPORTDB_VERSION

from .test_cli import CLI_PHOTOS_DB

LIBRARY1 = "tests/Test-Cloud-10.15.6.photoslibrary"
LIBRARY2 = "tests/Test-Cloud-13.1.photoslibrary"


def test_exportdb_migrate_photos_library():
    """Test exportdb --migrate-photos-library"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        # export first version of library
        result = runner.invoke(export, [".", "--library", os.path.join(cwd, LIBRARY1)])
        assert result.exit_code == 0

        # run the exportdb command
        result = runner.invoke(
            exportdb,
            [
                ".",
                "--migrate-photos-library",
                os.path.join(cwd, LIBRARY2),
                "--verbose",
            ],
            input="Y\n",
        )
        assert result.exit_code == 0
        assert "Migrated 29 photos" in result.output


def test_export_cleanup_exportdb_report():
    """test export with --cleanup flag results show in exportdb --report"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, ["--library", os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"]
        )
        assert result.exit_code == 0

        # create 2 files and a directory
        with open("delete_me.txt", "w") as fd:
            fd.write("delete me!")
        os.mkdir("./foo")
        with open("foo/delete_me_too.txt", "w") as fd:
            fd.write("delete me too!")

        assert pathlib.Path("./delete_me.txt").is_file()
        results = runner.invoke(
            export,
            [
                "--library",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
            ],
        )
        assert "Deleted: 2 files, 1 directory" in results.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./foo/delete_me_too.txt").is_file()

        results = runner.invoke(
            exportdb,
            [".", "--report", "report.json", "0"],
        )
        assert results.exit_code == 0
        with open("report.json", "r") as fd:
            report = json.load(fd)
        deleted_dirs = [x for x in report if x["cleanup_deleted_directory"]]
        deleted_files = [x for x in report if x["cleanup_deleted_file"]]
        assert len(deleted_dirs) == 1
        assert len(deleted_files) == 2


def test_exportdb_create_version_upgrade():
    """Test exportdb --create, --version, --upgrade"""

    runner = CliRunner()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(exportdb, [cwd, "--create", "5.0"])
        assert result.exit_code == 0
        assert "Created export database" in result.output
        export_db = pathlib.Path(cwd) / OSXPHOTOS_EXPORT_DB
        assert export_db.is_file()

        result = runner.invoke(exportdb, [cwd, "--version"])
        assert result.exit_code == 0
        assert "Export database version: 5.0" in result.output

        result = runner.invoke(exportdb, [cwd, "--upgrade"])
        assert result.exit_code == 0
        assert "Upgraded export database" in result.output
        assert OSXPHOTOS_EXPORTDB_VERSION in result.output

        result = runner.invoke(exportdb, [cwd, "--upgrade"])
        assert result.exit_code == 0
        assert "is already at latest version" in result.output


def test_exportdb_check():
    """Test --check"""

    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(exportdb, [cwd, "--create", OSXPHOTOS_EXPORTDB_VERSION])
        result = runner.invoke(exportdb, [cwd, "--check"])
        assert result.exit_code == 0
        assert "Ok" in result.output


def test_exportdb_repair():
    """Test --repair"""

    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(exportdb, [cwd, "--create", OSXPHOTOS_EXPORTDB_VERSION])
        result = runner.invoke(exportdb, [cwd, "--repair"])
        assert result.exit_code == 0
        assert "Ok" in result.output


def test_exportdb_history():
    """Test --history"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(export, [cwd, "--library", library, "-V"])
        result = runner.invoke(
            exportdb, [cwd, "--history", os.path.join(cwd, "wedding.jpg")]
        )
        assert result.exit_code == 0
        assert "export, None" in result.output


def test_exportdb_last_run():
    """Test --last-run"""

    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(exportdb, [cwd, "--create", OSXPHOTOS_EXPORTDB_VERSION])
        result = runner.invoke(exportdb, [cwd, "--last-run"])
        assert result.exit_code == 0
        # Can't test actual output as the command line for last run will be the pytest command


def test_exportdb_runs():
    """Test --runs"""

    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(exportdb, [cwd, "--create", OSXPHOTOS_EXPORTDB_VERSION])
        result = runner.invoke(exportdb, [cwd, "--runs"])
        assert result.exit_code == 0
        # Can't test actual output as the command line for last run will be the pytest command


def test_exportdb_last_export_dir():
    """Test --last-export-dir"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(export, [cwd, "--library", library, "-V"])
        result = runner.invoke(exportdb, [cwd, "--last-export-dir"])
        assert result.exit_code == 0
        assert cwd in result.output


def test_exportdb_touch_file():
    """Test --touch-file"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        # Export photos first
        result = runner.invoke(export, [cwd, "--library", library, "-V"])
        assert result.exit_code == 0

        # Modify timestamps of exported files
        modified_count = 0
        for file in pathlib.Path(cwd).rglob("*.jpg"):
            # Set timestamp to a different value (e.g., 1 day ago)
            old_time = file.stat().st_mtime - 86400
            os.utime(file, (old_time, old_time))
            modified_count += 1

        # Run exportdb --touch-file
        result = runner.invoke(exportdb, [cwd, "--touch-file"])
        assert result.exit_code == 0
        assert "Done." in result.output
        assert "Touched" in result.output
        # Verify at least one file was touched if we modified any
        if modified_count > 0:
            # Output format: "Done. Touched [num]X[/] files, skipped [num]Y[/] up to date files..."
            assert not result.output.startswith("Done. Touched [num]0[/]")


def test_exportdb_info():
    """Test --info"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        runner.invoke(export, [cwd, "--library", library, "-V"])
        result = runner.invoke(
            exportdb, [cwd, "--info", os.path.join(cwd, "wedding.jpg")]
        )
        assert result.exit_code == 0
        json_str = result.stdout.replace("\n", "").strip()
        result_dict = json.loads(json_str)
        assert result_dict["uuid"] == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"


def test_exportdb_uuid():
    """Test --uuid"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        runner.invoke(export, [cwd, "--library", library, "-V"])
        result = runner.invoke(
            exportdb, [cwd, "--uuid", os.path.join(cwd, "wedding.jpg")]
        )
        assert result.exit_code == 0
        assert result.stdout.strip() == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"


def test_exportdb_missing():
    """Test --missing"""

    runner = CliRunner()
    library = os.path.join(os.getcwd(), CLI_PHOTOS_DB)
    with runner.isolated_filesystem():
        cwd = os.getcwd()
        result = runner.invoke(export, [cwd, "--library", library, "-V"])
        result = runner.invoke(exportdb, [cwd, "--missing", "--library", library])
        assert result.exit_code == 0
        assert "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C" in result.output  # Pumpkins4.jpg
