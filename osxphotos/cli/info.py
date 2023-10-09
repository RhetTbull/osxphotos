"""info command for osxphotos CLI"""

import json

import click
import yaml

from osxphotos import PhotosDB, iPhotoDB
from osxphotos._constants import _PHOTOS_4_VERSION
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
def info(ctx, cli_obj, db, json_, photos_library):
    """Print out descriptive info of the Photos library database."""

    # needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["info"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    click.echo(f"Loading library: {db}", err=True)

    photosdb = iPhotoDB(db) if is_iphoto_library(db) else PhotosDB(dbfile=db)
    info = {"database_path": photosdb.db_path, "database_version": photosdb.db_version}
    photos = photosdb.photos(movies=False)
    not_shared_photos = [p for p in photos if not p.shared]
    info["photo_count"] = len(not_shared_photos)

    hidden = [p for p in photos if p.hidden]
    info["hidden_photo_count"] = len(hidden)

    movies = photosdb.photos(images=False, movies=True)
    not_shared_movies = [p for p in movies if not p.shared]
    info["movie_count"] = len(not_shared_movies)

    if photosdb.db_version > _PHOTOS_4_VERSION:
        shared_photos = [p for p in photos if p.shared]
        info["shared_photo_count"] = len(shared_photos)

        shared_movies = [p for p in movies if p.shared]
        info["shared_movie_count"] = len(shared_movies)

    keywords = photosdb.keywords_as_dict
    info["keywords_count"] = len(keywords)
    info["keywords"] = keywords

    albums = photosdb.albums_as_dict
    info["albums_count"] = len(albums)
    info["albums"] = albums

    if photosdb.db_version > _PHOTOS_4_VERSION:
        albums_shared = photosdb.albums_shared_as_dict
        info["shared_albums_count"] = len(albums_shared)
        info["shared_albums"] = albums_shared

    persons = photosdb.persons_as_dict

    info["persons_count"] = len(persons)
    info["persons"] = persons

    if json_ or (cli_obj and cli_obj.json):
        click.echo(json.dumps(info, ensure_ascii=False))
    else:
        click.echo(yaml.dump(info, sort_keys=False, allow_unicode=True))
