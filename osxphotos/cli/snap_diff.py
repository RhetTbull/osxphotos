"""snap/diff commands for osxphotos CLI"""

import datetime
import os
import pathlib
import shutil
import subprocess

import click
from rich.console import Console
from rich.syntax import Syntax

import osxphotos

from .cli_params import DB_OPTION, TIMESTAMP_OPTION, VERBOSE_OPTION
from .common import OSXPHOTOS_SNAPSHOT_DIR, get_photos_db
from .verbose import verbose_print


@click.command(name="snap")
@click.pass_obj
@click.pass_context
@DB_OPTION
def snap(ctx, cli_obj, db):
    """Create snapshot of Photos database to use with diff command

    Snapshots only the database files, not the entire library. If OSXPHOTOS_SNAPSHOT
    environment variable is defined, will use that as snapshot directory, otherwise
    uses '/private/tmp/osxphotos_snapshots'

    Works only on Photos library versions since Catalina (10.15) or newer.
    """

    db = get_photos_db(db, cli_obj.db if cli_obj else None)
    db_path = pathlib.Path(db)
    if db_path.is_file():
        # assume it's the sqlite file
        db_path = db_path.parent.parent
    db_path = db_path / "database"

    db_folder = os.environ.get("OSXPHOTOS_SNAPSHOT", OSXPHOTOS_SNAPSHOT_DIR)
    if not os.path.isdir(db_folder):
        click.echo(f"Creating snapshot folder: '{db_folder}'")
        os.mkdir(db_folder)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destination_path = pathlib.Path(db_folder) / timestamp

    # get all the sqlite files including the write ahead log if any
    files = db_path.glob("*.sqlite*")
    os.makedirs(destination_path)
    fu = osxphotos.fileutil.FileUtil()
    count = 0
    for file in files:
        if file.is_file():
            fu.copy(file, destination_path)
            count += 1

    print(f"Copied {count} files from {db_path} to {destination_path}")


@click.command(name="diff")
@click.pass_obj
@click.pass_context
@DB_OPTION
@click.option(
    "--raw-output",
    "-r",
    is_flag=True,
    default=False,
    help="Print raw output (don't use syntax highlighting).",
)
@click.option(
    "--style",
    "-s",
    metavar="STYLE",
    nargs=1,
    default="monokai",
    help="Specify style/theme for syntax highlighting. "
    "Theme may be any valid pygments style (https://pygments.org/styles/). "
    "Default is 'monokai'.",
)
@click.argument("db2", nargs=-1, type=click.Path(exists=True))
@VERBOSE_OPTION
@TIMESTAMP_OPTION
def diff(ctx, cli_obj, db, raw_output, style, db2, verbose_flag, timestamp):
    """Compare two Photos databases and print out differences

    To use the diff command, you'll need to install sqldiff via homebrew:

     - Install homebrew (https://brew.sh/) if not already installed

     - Install sqldiff: `brew install sqldiff`

    When run with no arguments, compares the current Photos library to the
    most recent snapshot in the the OSXPHOTOS_SNAPSHOT directory.

    If run with the --db option, compares the library specified by --db to the
    most recent snapshot in the the OSXPHOTOS_SNAPSHOT directory.

    If run with just the DB2 argument, compares the current Photos library to
    the database specified by the DB2 argument.

    If run with both the --db option and the DB2 argument, compares the
    library specified by --db to the database specified by DB2

    See also `osxphotos snap`

    If the OSXPHOTOS_SNAPSHOT environment variable is not set, will use
    '/private/tmp/osxphotos_snapshots'

    Works only on Photos library versions since Catalina (10.15) or newer.
    """

    verbose = verbose_print(verbose_flag, timestamp=timestamp)

    sqldiff = shutil.which("sqldiff")
    if not sqldiff:
        click.echo(
            "sqldiff not found; install via homebrew (https://brew.sh/): `brew install sqldiff`"
        )
        ctx.exit(2)
    verbose(f"sqldiff found at '{sqldiff}'")

    db = get_photos_db(db, cli_obj.db if cli_obj else None)
    db_path = pathlib.Path(db)
    if db_path.is_file():
        # assume it's the sqlite file
        db_path = db_path.parent.parent
    db_path = db_path / "database"
    db_1 = db_path / "photos.sqlite"

    if db2:
        db_2 = pathlib.Path(db2[0])
    else:
        # get most recent snapshot
        db_folder = os.environ.get("OSXPHOTOS_SNAPSHOT", OSXPHOTOS_SNAPSHOT_DIR)
        verbose(f"Using snapshot folder: '{db_folder}'")
        folders = sorted([f for f in pathlib.Path(db_folder).glob("*") if f.is_dir()])
        folder_2 = folders[-1]
        db_2 = folder_2 / "Photos.sqlite"

    if not db_1.exists():
        print(f"database file {db_1} missing")
    if not db_2.exists():
        print(f"database file {db_2} missing")

    verbose(f"Comparing databases {db_1} and {db_2}")

    diff_proc = subprocess.Popen([sqldiff, db_2, db_1], stdout=subprocess.PIPE)
    console = Console()
    for line in iter(diff_proc.stdout.readline, b""):
        line = line.decode("UTF-8").rstrip()
        if raw_output:
            print(line)
        else:
            syntax = Syntax(
                line, "sql", theme=style, line_numbers=False, code_width=1000
            )
            console.print(syntax)
