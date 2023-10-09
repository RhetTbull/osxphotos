"""persons command for osxphotos CLI"""
import json

import click
import yaml

import osxphotos
from osxphotos.iphoto import is_iphoto_library

from .cli_params import DB_ARGUMENT, DB_OPTION, JSON_OPTION
from .common import get_photos_db
from .list import _list_libraries


@click.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def persons(ctx, cli_obj, db, json_, photos_library):
    """Print out persons (faces) found in the Photos library."""

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["persons"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = (
        osxphotos.iPhotoDB(db)
        if is_iphoto_library(db)
        else osxphotos.PhotosDB(dbfile=db)
    )
    persons = {"persons": photosdb.persons_as_dict}
    if json_ or (cli_obj and cli_obj.json):
        click.echo(json.dumps(persons, ensure_ascii=False))
    else:
        click.echo(yaml.dump(persons, sort_keys=False, allow_unicode=True))
