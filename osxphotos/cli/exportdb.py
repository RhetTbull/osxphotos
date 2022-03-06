"""exportdb command for osxphotos CLI"""

import pathlib
import sys

import click
from rich import print

from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos._version import __version__
from osxphotos.export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDB
from osxphotos.export_db_utils import (
    export_db_check_signatures,
    export_db_get_last_run,
    export_db_get_version,
    export_db_save_config_to_file,
    export_db_touch_files,
    export_db_update_signatures,
    export_db_vacuum,
)

from .common import OSXPHOTOS_HIDDEN
from .verbose import verbose_print


@click.command(name="exportdb", hidden=OSXPHOTOS_HIDDEN)
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
@click.option("--verbose", "-V", is_flag=True, help="Print verbose output.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run in dry-run mode (don't actually update files), e.g. for use with --update-signatures.",
)
@click.argument("export_db", metavar="EXPORT_DATABASE", type=click.Path(exists=True))
def exportdb(
    version,
    vacuum,
    check_signatures,
    update_signatures,
    touch_file,
    last_run,
    save_config,
    info,
    migrate,
    sql,
    export_dir,
    verbose,
    dry_run,
    export_db,
):
    """Utilities for working with the osxphotos export database"""

    verbose_ = verbose_print(verbose, rich=True)

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
        version,
        check_signatures,
        update_signatures,
        touch_file,
        last_run,
        bool(save_config),
        bool(info),
        migrate,
        bool(sql),
    ]
    if sum(sub_commands) > 1:
        print("[red]Only a single sub-command may be specified at a time[/red]")
        sys.exit(1)

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
                print(info_rec.asdict())
            else:
                print(f"[red]File '{info}' not found in export database[/red]")
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
