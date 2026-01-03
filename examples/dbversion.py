"""Print DB / Photos version of a Photos database"""

import click

from osxphotos.photosdb.photosdb_utils import (
    get_db_path_for_library,
    get_db_version,
    get_model_version,
    get_photos_library_version,
)


@click.command
@click.argument("library_path")
def main(library_path):
    """Print version info for a Photos library"""
    try:
        db_path = get_db_path_for_library(library_path)
        photos_version = get_photos_library_version(db_path)
        model_version = get_model_version(db_path)

        click.echo(f"Database path: {db_path}")
        click.echo(f"Photos version: {photos_version}")
        click.echo(f"DB version: {get_db_version(db_path)}")
        click.echo(f"Model version: {model_version}")
    except Exception as e:
        click.echo(f"Error reading Photos version: {e}", err=True)


if __name__ == "__main__":
    main()
