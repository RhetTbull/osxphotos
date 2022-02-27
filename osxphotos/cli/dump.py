"""dump command for osxphotos CLI """

import click

import osxphotos
from osxphotos.queryoptions import QueryOptions

from .common import DB_ARGUMENT, DB_OPTION, DELETED_OPTIONS, JSON_OPTION, get_photos_db
from .list import _list_libraries
from .print_photo_info import print_photo_info


@click.command()
@DB_OPTION
@JSON_OPTION
@DELETED_OPTIONS
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def dump(ctx, cli_obj, db, json_, deleted, deleted_only, photos_library):
    """Print list of all photos & associated info from the Photos library."""

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(ctx.obj.group.commands["dump"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    # check exclusive options
    if deleted and deleted_only:
        click.echo("Incompatible dump options", err=True)
        click.echo(ctx.obj.group.commands["dump"].get_help(ctx), err=True)
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    if deleted or deleted_only:
        photos = photosdb.photos(movies=True, intrash=True)
    else:
        photos = []
    if not deleted_only:
        photos += photosdb.photos(movies=True)

    print_photo_info(photos, json_ or cli_obj.json)
