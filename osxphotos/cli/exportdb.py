"""exportdb command for osxphotos CLI"""

import json
import pathlib
import sys

import click
from rich import print

from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos._version import __version__
from osxphotos.export_db import (
    MAX_EXPORT_RESULTS_DATA_ROWS,
    OSXPHOTOS_EXPORTDB_VERSION,
    ExportDB,
)
from osxphotos.export_db_utils import (
    export_db_check_signatures,
    export_db_get_last_run,
    export_db_get_version,
    export_db_save_config_to_file,
    export_db_touch_files,
    export_db_update_signatures,
    export_db_vacuum,
)
from osxphotos.utils import pluralize

from .export import render_and_validate_report
from .param_types import TemplateString
from .report_writer import report_writer_factory
from .verbose import verbose_print


@click.command(name="exportdb")
@click.option("--version", is_flag=True, help="Print export database version and exit.")
@click.option("--vacuum", is_flag=True, help="Run VACUUM to defragment the database.")
@click.option(
    "--check-signatures",
    is_flag=True,
    help="Check signatures for all exported photos in the database to find signatures that don't match.",
)
@click.option(
    "--update-signatures",
    is_flag=True,
    help="Update signatures for all exported photos in the database to match on-disk signatures.",
)
@click.option(
    "--touch-file",
    is_flag=True,
    help="Touch files on disk to match created date in Photos library and update export database signatures",
)
@click.option(
    "--last-run",
    is_flag=True,
    help="Show last run osxphotos commands used with this database.",
)
@click.option(
    "--save-config",
    metavar="CONFIG_FILE",
    help="Save last run configuration to TOML file for use by --load-config.",
)
@click.option(
    "--info",
    metavar="FILE_PATH",
    nargs=1,
    help="Print information about FILE_PATH contained in the database.",
)
@click.option(
    "--uuid-files",
    metavar="UUID",
    nargs=1,
    help="List exported files associated with UUID.",
)
@click.option(
    "--uuid-info",
    metavar="UUID",
    nargs=1,
    help="Print information about UUID contained in the database.",
)
@click.option(
    "--delete-uuid",
    metavar="UUID",
    nargs=1,
    multiple=True,
    help="Delete all data associated with UUID from the database.",
)
@click.option(
    "--delete-file",
    metavar="FILE_PATH",
    nargs=1,
    multiple=True,
    help="Delete all data associated with FILE_PATH from the database; "
    "does not delete the actual exported file if it exists, only the data in the database.",
)
@click.option(
    "--report",
    metavar="REPORT_FILE RUN_ID",
    help="Generate an export report as `osxphotos export ... --report REPORT_FILE` would have done. "
    "This allows you to re-create an export report if you didn't use the --report option "
    "when running `osxphotos export`. "
    "The extension of the report file is used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    f"RUN_ID may be any integer from {-MAX_EXPORT_RESULTS_DATA_ROWS} to 0 specifying which run to use. "
    "For example, `--report report.csv 0` will generate a CSV report for the last run and "
    "`--report report.json -1` will generate a JSON report for the second-to-last run "
    "(one run prior to last run). "
    "REPORT_FILE may be a template string (see Templating System), for example, "
    "--report 'export_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=(TemplateString(), click.IntRange(-(MAX_EXPORT_RESULTS_DATA_ROWS - 1), 0)),
)
@click.option(
    "--migrate",
    is_flag=True,
    help="Migrate (if needed) export database to current version.",
)
@click.option(
    "--sql",
    metavar="SQL_STATEMENT",
    help="Execute SQL_STATEMENT against export database and print results.",
)
@click.option(
    "--export-dir",
    help="Optional path to export directory (if not parent of export database).",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--append",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@click.option("--verbose", "-V", is_flag=True, help="Print verbose output.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run in dry-run mode (don't actually update files), e.g. for use with --update-signatures.",
)
@click.argument("export_db", metavar="EXPORT_DATABASE", type=click.Path(exists=True))
def exportdb(
    append,
    check_signatures,
    dry_run,
    export_db,
    export_dir,
    info,
    last_run,
    migrate,
    report,
    save_config,
    sql,
    touch_file,
    update_signatures,
    uuid_files,
    uuid_info,
    delete_uuid,
    delete_file,
    vacuum,
    verbose,
    version,
):
    """Utilities for working with the osxphotos export database"""

    verbose_ = verbose_print(verbose, rich=True)

    # validate options and args
    if append and not report:
        print(
            "[red]Error: --append requires --report; ee --help for more information.[/]",
            file=sys.stderr,
        )
        sys.exit(1)

    export_db = pathlib.Path(export_db)
    if export_db.is_dir():
        # assume it's the export folder
        export_db = export_db / OSXPHOTOS_EXPORT_DB
        if not export_db.is_file():
            print(
                f"[red]Error: {OSXPHOTOS_EXPORT_DB} missing from {export_db.parent}[/red]"
            )
            sys.exit(1)

    export_dir = export_dir or export_db.parent

    sub_commands = [
        bool(cmd)
        for cmd in [
            check_signatures,
            info,
            last_run,
            migrate,
            report,
            save_config,
            sql,
            touch_file,
            update_signatures,
            uuid_files,
            uuid_info,
            vacuum,
            version,
        ]
    ]
    if sum(sub_commands) > 1:
        print("[red]Only a single sub-command may be specified at a time[/red]")
        sys.exit(1)

    # process sub-commands
    # TODO: each of these should be a function call
    if version:
        try:
            osxphotos_ver, export_db_ver = export_db_get_version(export_db)
        except Exception as e:
            print(f"[red]Error: could not read version from {export_db}: {e}[/red]")
            sys.exit(1)
        else:
            print(
                f"osxphotos version: {osxphotos_ver}, export database version: {export_db_ver}"
            )
        sys.exit(0)

    if vacuum:
        try:
            start_size = pathlib.Path(export_db).stat().st_size
            export_db_vacuum(export_db)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(
                f"Vacuumed {export_db}! {start_size} bytes -> {pathlib.Path(export_db).stat().st_size} bytes"
            )
            sys.exit(0)

    if update_signatures:
        try:
            updated, skipped = export_db_update_signatures(
                export_db, export_dir, verbose_, dry_run
            )
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(f"Done. Updated {updated} files, skipped {skipped} files.")
            sys.exit(0)

    if last_run:
        try:
            last_run_info = export_db_get_last_run(export_db)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(f"last run at {last_run_info[0]}:")
            print(f"osxphotos {last_run_info[1]}")
            sys.exit(0)

    if save_config:
        try:
            export_db_save_config_to_file(export_db, save_config)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(f"Saved configuration to {save_config}")
            sys.exit(0)

    if check_signatures:
        try:
            matched, notmatched, skipped = export_db_check_signatures(
                export_db, export_dir, verbose_=verbose_
            )
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(
                f"Done. Found {matched} matching signatures and {notmatched} signatures that don't match. Skipped {skipped} missing files."
            )
            sys.exit(0)

    if touch_file:
        try:
            touched, not_touched, skipped = export_db_touch_files(
                export_db, export_dir, verbose_=verbose_, dry_run=dry_run
            )
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            print(
                f"Done. Touched {touched} files, skipped {not_touched} up to date files, skipped {skipped} missing files."
            )
            sys.exit(0)

    if info:
        exportdb = ExportDB(export_db, export_dir)
        try:
            info_rec = exportdb.get_file_record(info)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            if info_rec:
                print(info_rec.json(indent=2))
            else:
                print(f"[red]File '{info}' not found in export database[/red]")
            sys.exit(0)

    if uuid_info:
        # get photoinfo record for a uuid
        exportdb = ExportDB(export_db, export_dir)
        try:
            info_rec = exportdb.get_photoinfo_for_uuid(uuid_info)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            if info_rec:
                print(json.dumps(json.loads(info_rec), sort_keys=True, indent=2))
            else:
                print(f"[red]UUID '{uuid_info}' not found in export database[/red]")
            sys.exit(0)

    if uuid_files:
        # list files associated with a uuid
        exportdb = ExportDB(export_db, export_dir)
        try:
            file_list = exportdb.get_files_for_uuid(uuid_files)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            if file_list:
                for f in file_list:
                    print(f)
            else:
                print(f"[red]UUID '{uuid_files}' not found in export database[/red]")
            sys.exit(0)

    if delete_uuid:
        # delete a uuid from the export database
        exportdb = ExportDB(export_db, export_dir)
        for uuid in delete_uuid:
            print(f"Deleting uuid {uuid} from database.")
            count = exportdb.delete_data_for_uuid(uuid)
            print(f"Deleted {count} {pluralize(count, 'record', 'records')}.")
        sys.exit(0)

    if delete_file:
        # delete information associated with a file from the export database
        exportdb = ExportDB(export_db, export_dir)
        for filepath in delete_file:
            print(f"Deleting file {filepath} from database.")
            count = exportdb.delete_data_for_filepath(filepath)
            print(f"Deleted {count} {pluralize(count, 'record', 'records')}.")
            sys.exit(0)

    if report:
        exportdb = ExportDB(export_db, export_dir)
        report_template, run_id = report
        report_filename = render_and_validate_report(report_template, "", export_dir)
        export_results = exportdb.get_export_results(run_id)
        if not export_results:
            print(f"[red]No report results found for run ID {run_id}[/red]")
            sys.exit(1)
        try:
            report_writer = report_writer_factory(report_filename, append=append)
        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        report_writer.write(export_results)
        report_writer.close()
        print(f"Wrote report to {report_filename}")
        sys.exit(0)

    if migrate:
        exportdb = ExportDB(export_db, export_dir)
        if upgraded := exportdb.was_upgraded:
            print(
                f"Migrated export database {export_db} from version {upgraded[0]} to {upgraded[1]}"
            )
        else:
            print(
                f"Export database {export_db} is already at latest version {OSXPHOTOS_EXPORTDB_VERSION}"
            )
        sys.exit(0)

    if sql:
        exportdb = ExportDB(export_db, export_dir)
        try:
            c = exportdb._conn.cursor()
            results = c.execute(sql)
        except Exception as e:
            print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        else:
            for row in results:
                print(row)
            sys.exit(0)
