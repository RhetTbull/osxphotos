"""Read an osxphotos export database and print out list of photos which had metadata changes at time of last export

Run this with `osxphotos run metadata_change_report.py <exported_database_path>`
"""

import pathlib
import sys

import click

from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.cli.click_rich_echo import rich_echo_error as echo_error
from osxphotos.export_db import ExportDB


@click.command()
@click.argument(
    "export_path",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    required=True,
)
@click.argument("export_db_path", type=click.Path(exists=True), required=False)
def main(export_path, export_db_path):
    """Read an osxphotos export database and print out list of photos for which
    the metadata changed between the previous export and the most recent export.

    You must pass the path to the osxphotos export directory and optionally the
    export database as the arguments to this script.

    For example:
    osxphotos run metadata_change_report.py /path/to/export/ /path/to/.osxphotos_export.db
    """

    export_path = pathlib.Path(export_path)
    # assume it's the export folder
    export_db_path = pathlib.Path(export_db_path) or export_path / OSXPHOTOS_EXPORT_DB
    if not export_db_path.is_file():
        echo_error(
            f"[error]Error: could not find export database at {export_db_path}[/]"
        )
        sys.exit(1)

    exportdb = ExportDB(export_db_path, export_path)
    export_results = exportdb.get_export_results(0)
    if not export_results:
        echo_error(f"[error]No report results found[/]")
        sys.exit(1)

    echo(f"Export date: [date]{export_results.datetime}")
    for filename in export_results.metadata_changed:
        try:
            uuid = exportdb.get_file_record(filename).uuid
        except Exception as e:
            uuid = None
        echo(f"[filename]{filename}[/] ([uuid]{uuid}[/])")

    sys.exit(0)


if __name__ == "__main__":
    main()
