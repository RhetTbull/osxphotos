"""albums command for osxphotos CLI"""

import json

import click
import yaml

import osxphotos
from osxphotos._constants import _PHOTOS_4_VERSION
from osxphotos.iphoto import is_iphoto_library

from .cli_params import DB_ARGUMENT, DB_OPTION, JSON_OPTION
from .common import get_photos_db
from .list import _list_libraries


@click.command()
@DB_OPTION
@JSON_OPTION
@click.option(
    "--size",
    "-s",
    "sort_size",
    is_flag=True,
    help="Sort albums by size instead of alphabetically",
)
@click.pass_obj
@click.pass_context
def albums(ctx, cli_obj, db, json_, sort_size):
    """Print out albums found in the Photos library."""

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["albums"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = (
        osxphotos.iPhotoDB(db)
        if is_iphoto_library(db)
        else osxphotos.PhotosDB(dbfile=db)
    )
    albums = {"albums": album_dict(photosdb, sort_size)}
    if photosdb.db_version > _PHOTOS_4_VERSION:
        albums["shared albums"] = shared_album_dict(photosdb, sort_size)

    # cli_obj will be None if called from pytest
    if json_ or (cli_obj and cli_obj.json):
        click.echo(json.dumps(albums, ensure_ascii=False))
    else:
        click.echo(yaml.dump(albums, sort_keys=False, allow_unicode=True))


def album_dict(photosdb: osxphotos.PhotosDB, sort_size: bool) -> dict[str, int]:
    """Return albums with folder hierarchy and count of items"""
    album_dict = dict()
    for album in photosdb.album_info:
        album_path = "/".join(album.folder_names)
        if album_path:
            album_path += f"/{album.title}"
        else:
            album_path = album.title
        album_count = len(album)
        album_dict[album_path] = album_count

    if sort_size:
        return dict(sorted(album_dict.items(), key=lambda item: item[1], reverse=True))
    else:
        return dict(sorted(album_dict.items(), key=lambda item: item[0]))


def shared_album_dict(photosdb: osxphotos.PhotosDB, sort_size: bool) -> dict[str, int]:
    """Return shared albums with folder hierarchy and count of items"""
    album_dict = photosdb.albums_shared_as_dict

    if sort_size:
        # already sorted in size from albums_shared_as_dict
        return album_dict
    else:
        return dict(sorted(album_dict.items(), key=lambda item: item[0]))
