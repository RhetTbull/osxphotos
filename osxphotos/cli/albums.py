"""albums command for osxphotos CLI"""

import json

import click
import yaml

import osxphotos

from .common import DB_ARGUMENT, DB_OPTION, JSON_OPTION, get_photos_db
from .list import _list_libraries

from osxphotos._constants import _PHOTOS_4_VERSION


@click.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def albums(ctx, cli_obj, db, json_, photos_library):
    """Print out albums found in the Photos library."""

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["albums"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    albums = {"albums": photosdb.albums_as_dict}
    if photosdb.db_version > _PHOTOS_4_VERSION:
        albums["shared albums"] = photosdb.albums_shared_as_dict

    if json_ or cli_obj.json:
        click.echo(json.dumps(albums, ensure_ascii=False))
    else:
        click.echo(yaml.dump(albums, sort_keys=False, allow_unicode=True))
