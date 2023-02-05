"""grep command for osxphotos CLI """

import pathlib

import click
from rich import print

from osxphotos.photosdb.photosdb_utils import get_photos_library_version
from osxphotos.sqlgrep import sqlgrep

from .cli_params import DB_OPTION, OSXPHOTOS_HIDDEN
from .common import get_photos_db


@click.command(name="grep", hidden=OSXPHOTOS_HIDDEN)
@DB_OPTION
@click.pass_obj
@click.pass_context
@click.option(
    "--ignore-case",
    "-i",
    required=False,
    is_flag=True,
    default=False,
    help="Ignore case when searching (default is case-sensitive).",
)
@click.option(
    "--print-filename",
    "-p",
    required=False,
    is_flag=True,
    default=False,
    help="Print name of database file when printing results.",
)
@click.argument("pattern", metavar="PATTERN", required=True)
def grep(ctx, cli_obj, db, ignore_case, print_filename, pattern):
    """Search for PATTERN in the Photos sqlite database file"""
    db = db or get_photos_db()
    db = pathlib.Path(db)
    if db.is_file():
        # if passed the actual database, really want the parent of the database directory
        db = db.parent.parent
    photos_ver = get_photos_library_version(str(db))
    if photos_ver < 5:
        db_file = db / "database" / "photos.db"
    else:
        db_file = db / "database" / "Photos.sqlite"

    if not db_file.is_file():
        click.secho(f"Could not find database file {db_file}", fg="red")
        ctx.exit(2)

    db_file = str(db_file)

    for table, column, row_id, value in sqlgrep(
        db_file, pattern, ignore_case, print_filename, rich_markup=True
    ):
        print(", ".join([table, column, row_id, value]))
