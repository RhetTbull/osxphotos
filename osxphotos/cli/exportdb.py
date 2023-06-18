"""exportdb command for osxphotos CLI"""

import json
import pathlib
import sys
from textwrap import dedent

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
    export_db_backup,
    export_db_check_signatures,
    export_db_get_errors,
    export_db_get_last_library,
    export_db_get_last_run,
    export_db_get_version,
    export_db_migrate_photos_library,
    export_db_save_config_to_file,
    export_db_touch_files,
    export_db_update_signatures,
    export_db_vacuum,
)
from osxphotos.utils import pluralize

from .cli_params import THEME_OPTION, TIMESTAMP_OPTION, VERBOSE_OPTION
from .click_rich_echo import (
    rich_click_echo,
    rich_echo,
    rich_echo_error,
    set_rich_console,
    set_rich_theme,
)
from .color_themes import get_theme
from .export import render_and_validate_report
from .param_types import TemplateString
from .report_writer import export_report_writer_factory
from .verbose import get_verbose_console, verbose_print


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
    "--errors",
    is_flag=True,
    help="Print list of files that had warnings/errors on export (from all runs).",
)
@click.option(
    "--last-errors",
    is_flag=True,
    help="Print list of files that had warnings/errors on last export run.",
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
    "--migrate-photos-library",
    metavar="PHOTOS_LIBRARY",
    help="Migrate the export database to use the specified Photos library. "
    "Use this if you have moved your Photos library to a new location or computer and "
    "want to keep using the same export database. "
    "This will update the UUIDs in the export database to match the new Photos library.",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
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
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@THEME_OPTION
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run in dry-run mode (don't actually update files); for example, use with --update-signatures or --migrate-photos-library.",
)
@click.argument("export_db", metavar="EXPORT_DATABASE", type=click.Path(exists=True))
def exportdb(
    append,
    check_signatures,
    dry_run,
    export_db,
    export_dir,
    info,
    errors,
    last_errors,
    last_run,
    migrate,
    migrate_photos_library,
    report,
    save_config,
    sql,
    theme,
    timestamp,
    touch_file,
    update_signatures,
    uuid_files,
    uuid_info,
    delete_uuid,
    delete_file,
    vacuum,
    verbose_flag,
    version,
):
    """Utilities for working with the osxphotos export database"""
    verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)

    # validate options and args
    if append and not report:
        rich_echo_error(
            "[error]Error: --append requires --report; see --help for more information.[/]",
            file=sys.stderr,
        )
        sys.exit(1)

    export_db = pathlib.Path(export_db)
    if export_db.is_dir():
        # assume it's the export folder
        export_db = export_db / OSXPHOTOS_EXPORT_DB
        if not export_db.is_file():
            rich_echo_error(
                f"[error]Error: {OSXPHOTOS_EXPORT_DB} missing from {export_db.parent}[/error]"
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
        rich_echo_error(
            "[error]Only a single sub-command may be specified at a time[/error]"
        )
        sys.exit(1)

    # process sub-commands
    # TODO: each of these should be a function call
    if version:
        try:
            osxphotos_ver, export_db_ver = export_db_get_version(export_db)
        except Exception as e:
            rich_echo_error(
                f"[error]Error: could not read version from {export_db}: {e}[/error]"
            )
            sys.exit(1)
        else:
            rich_echo(
                f"osxphotos version: [num]{osxphotos_ver}[/], export database version: [num]{export_db_ver}[/]"
            )
        sys.exit(0)

    if vacuum:
        try:
            start_size = pathlib.Path(export_db).stat().st_size
            export_db_vacuum(export_db)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(
                f"Vacuumed {export_db}! [num]{start_size}[/] bytes -> [num]{pathlib.Path(export_db).stat().st_size}[/] bytes"
            )
            sys.exit(0)

    if update_signatures:
        try:
            updated, skipped = export_db_update_signatures(
                export_db, export_dir, verbose, dry_run
            )
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(
                f"Done. Updated [num]{updated}[/] files, skipped [num]{skipped}[/] files."
            )
            sys.exit(0)

    if last_run:
        try:
            last_run_info = export_db_get_last_run(export_db)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(f"last run at [time]{last_run_info[0]}:")
            rich_echo(f"osxphotos {last_run_info[1]}")
            sys.exit(0)

    if save_config:
        try:
            export_db_save_config_to_file(export_db, save_config)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(f"Saved configuration to [filepath]{save_config}")
            sys.exit(0)

    if check_signatures:
        try:
            matched, notmatched, skipped = export_db_check_signatures(
                export_db, export_dir, verbose_=verbose
            )
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(
                f"Done. Found [num]{matched}[/] matching signatures and [num]{notmatched}[/] signatures that don't match. "
                f"Skipped [num]{skipped}[/] missing files."
            )
            sys.exit(0)

    if touch_file:
        try:
            touched, not_touched, skipped = export_db_touch_files(
                export_db, export_dir, verbose_=verbose, dry_run=dry_run
            )
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            rich_echo(
                f"Done. Touched [num]{touched}[/] files, skipped [num]{not_touched}[/] up to date files, "
                f"skipped [num]{skipped}[/] missing files."
            )
            sys.exit(0)

    if info:
        exportdb = ExportDB(export_db, export_dir)
        try:
            info_rec = exportdb.get_file_record(info)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            if info_rec:
                # use rich print as rich_echo doesn't highlight json
                print(info_rec.json(indent=2))
            else:
                rich_echo(f"[error]File '{info}' not found in export database[/error]")
            sys.exit(0)

    if errors:
        # list errors
        try:
            error_list = export_db_get_errors(export_db)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            if error_list:
                for error in error_list:
                    rich_echo(error)
            else:
                rich_echo("No errors found")
            sys.exit(0)

    if last_errors:
        exportdb = ExportDB(export_db, export_dir)
        if export_results := exportdb.get_export_results(0):
            for error in [
                *export_results.error,
                *export_results.exiftool_error,
                *export_results.exiftool_warning,
            ]:
                rich_click_echo(
                    f"[filepath]{error[0]}[/], [time]{export_results.datetime}[/], [error]{error[1]}[/]"
                )
            sys.exit(0)
        else:
            rich_echo_error("[error]Results from last run not found in database[/]")
            sys.exit(1)

    if uuid_info:
        # get photoinfo record for a uuid
        exportdb = ExportDB(export_db, export_dir)
        try:
            info_rec = exportdb.get_photoinfo_for_uuid(uuid_info)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            if info_rec:
                # use rich print as rich_echo doesn't highlight json
                print(json.dumps(json.loads(info_rec), sort_keys=True, indent=2))
            else:
                rich_echo(
                    f"[error]UUID '{uuid_info}' not found in export database[/error]"
                )
            sys.exit(0)

    if uuid_files:
        # list files associated with a uuid
        exportdb = ExportDB(export_db, export_dir)
        try:
            file_list = exportdb.get_files_for_uuid(uuid_files)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            if file_list:
                for f in file_list:
                    rich_echo(f"[filepath]{f}[/]")
            else:
                rich_echo(
                    f"[error]UUID '{uuid_files}' not found in export database[/error]"
                )
            sys.exit(0)

    if delete_uuid:
        # delete a uuid from the export database
        exportdb = ExportDB(export_db, export_dir)
        for uuid in delete_uuid:
            rich_echo(f"Deleting uuid [uuid]{uuid}[/] from database.")
            count = exportdb.delete_data_for_uuid(uuid)
            rich_echo(
                f"Deleted [num]{count}[/] {pluralize(count, 'record', 'records')}."
            )
        sys.exit(0)

    if delete_file:
        # delete information associated with a file from the export database
        exportdb = ExportDB(export_db, export_dir)
        for filepath in delete_file:
            rich_echo(f"Deleting file [filepath]{filepath}[/] from database.")
            count = exportdb.delete_data_for_filepath(filepath)
            rich_echo(
                f"Deleted [num]{count}[/] {pluralize(count, 'record', 'records')}."
            )
            sys.exit(0)

    if report:
        exportdb = ExportDB(export_db, export_dir)
        report_template, run_id = report
        report_filename = render_and_validate_report(report_template, "", export_dir)
        export_results = exportdb.get_export_results(run_id)
        if not export_results:
            rich_echo_error(
                f"[error]No report results found for run ID {run_id}[/error]"
            )
            sys.exit(1)
        try:
            report_writer = export_report_writer_factory(report_filename, append=append)
        except ValueError as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        report_writer.write(export_results)
        report_writer.close()
        rich_echo(f"Wrote report to [filepath]{report_filename}[/]")
        sys.exit(0)

    if migrate:
        exportdb = ExportDB(export_db, export_dir)
        if upgraded := exportdb.was_upgraded:
            rich_echo(
                f"Migrated export database [filepath]{export_db}[/] from version [num]{upgraded[0]}[/] to [num]{upgraded[1]}[/]"
            )
        else:
            rich_echo(
                f"Export database [filepath]{export_db}[/] is already at latest version [num]{OSXPHOTOS_EXPORTDB_VERSION}[/]"
            )
        sys.exit(0)

    if sql:
        exportdb = ExportDB(export_db, export_dir)
        try:
            c = exportdb._conn.cursor()
            results = c.execute(sql)
        except Exception as e:
            rich_echo_error(f"[error]Error: {e}[/error]")
            sys.exit(1)
        else:
            for row in results:
                print(row)
            sys.exit(0)

    if migrate_photos_library:
        # migrate Photos library to new library and update UUIDs in export database
        last_library = export_db_get_last_library(export_db)
        rich_echo(
            dedent(
                f"""
        [warning]:warning-emoji:  This command will update your export database ([filepath]{export_db}[/]) 
        to use [filepath]{migrate_photos_library}[/] as the new source library.
        The last library used was [filepath]{last_library}[/].
        This will allow you to use the export database with the new library but it will
        no longer work correctly with the old library unless you run the `--migrate-photos-library`
        command again to update the export database to use the previous library.

        A backup of the export database will be created in the same directory as the export database.
        """
            )
        )
        if not click.confirm("Do you want to continue?"):
            sys.exit(0)
        if not dry_run:
            backup_file = export_db_backup(export_db)
            verbose(f"Backed up export database to [filepath]{backup_file}[/]")
        migrated, notmigrated = export_db_migrate_photos_library(
            export_db, migrate_photos_library, verbose, dry_run
        )
        rich_echo(
            f"Migrated [num]{migrated}[/] {pluralize(migrated, 'photo', 'photos')}, "
            f"[num]{notmigrated}[/] not migrated."
        )
