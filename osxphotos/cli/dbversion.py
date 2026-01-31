"""Get version info for a Photos database CLI"""

import os
import sqlite3

import click

from osxphotos.photosdb.photosdb_utils import (
    get_db_path_for_library,
    get_db_version,
    get_model_version,
    get_photos_library_version,
)


def get_schema_sql(db_path: str | os.PathLike):
    """Retrieve CREATE statements for all objects."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT type, name, sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
    """
    )

    results = cursor.fetchall()
    conn.close()

    return {row[1]: {"type": row[0], "sql": row[2]} for row in results}


@click.command(name="dbversion")
@click.pass_obj
@click.pass_context
@click.argument("library_path")
@click.option(
    "--schema",
    is_flag=True,
    help="Print SQL schema for the database instead of printing version info.",
)
def dbversion(ctx, cli_obj, library_path, schema):
    """Print version info for a Photos library"""
    try:
        db_path = get_db_path_for_library(library_path)
        if db_path.suffix == ".db":
            # if user passed photos.db, verify if there's a Photos.sqlite which is the correct database for Photos 5+
            photos_db_path = db_path.parent / "Photos.sqlite"
            if photos_db_path.is_file():
                db_path = photos_db_path
        photos_version = get_photos_library_version(db_path)
        model_version = get_model_version(db_path)
    except Exception as e:
        click.echo(f"Error reading Photos version: {e}", err=True)
        raise click.Abort()

    if schema:
        sql_schema = get_schema_sql(db_path)
        for create_str in sql_schema.values():
            sql = create_str.get("sql", "")
            click.echo(f"{sql};")
    else:
        click.echo(f"Database path: {db_path}")
        click.echo(f"Photos version: {photos_version}")
        click.echo(f"DB version: {get_db_version(db_path)}")
        click.echo(f"Model version: {model_version}")
