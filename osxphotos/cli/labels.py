"""labels command for osxphotos CLI"""

import json

import click
import yaml

import osxphotos

from .cli_params import DB_ARGUMENT, DB_OPTION, JSON_OPTION
from .common import get_photos_db
from .list import _list_libraries


@click.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def labels(ctx, cli_obj, db, json_, photos_library):
    """Print out image classification labels found in the Photos library."""

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["labels"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    labels = {"labels": photosdb.labels_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(labels, ensure_ascii=False))
    else:
        click.echo(yaml.dump(labels, sort_keys=False, allow_unicode=True))
