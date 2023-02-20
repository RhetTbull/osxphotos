"""Test osxphotos exportdb cli command"""

import os

from click.testing import CliRunner

from osxphotos.cli.export import export
from osxphotos.cli.exportdb import exportdb

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
