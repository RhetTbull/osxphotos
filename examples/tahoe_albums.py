"""Test shared albusm on Tahoe"""

from __future__ import annotations

import json
import logging
from typing import Callable

import click
import yaml

import osxphotos
from osxphotos._constants import (
    _DB_TABLE_NAMES,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_SHARED_ALBUM_KIND,
)
from osxphotos._version import __version__
from osxphotos.cli.albums import album_dict, shared_album_dict
from osxphotos.cli.cli_params import DB_OPTION, JSON_OPTION
from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.cli.common import get_photos_db
from osxphotos.cli.list import _list_libraries
from osxphotos.unicode import normalize_unicode

logger = logging.getLogger("osxphotos")


def process_shared_albums(photosdb: osxphotos.PhotosDB, verbose: Callable[[str], None]):
    """Process shared album info on macOS Tahoe"""
    # get details about albums
    verbose("Processing albums.")
    _, c = photosdb.get_db_connection()

    asset_table = _DB_TABLE_NAMES[photosdb.photos_version]["ASSET"]
    album_share_table = "ZSHARE"
    c.execute(
        f""" SELECT
            {album_share_table}.ZUUID,
            {asset_table}.ZUUID
            FROM {asset_table}
            JOIN {album_share_table} ON {album_share_table}.Z_PK = {asset_table}.ZCOLLECTIONSHARE
        """
    )

    # 0     ZGENERICALBUM.ZUUID,
    # 1     ZGENERICASSET.ZUUID,
    # 2     Z_26ASSETS.Z_FOK_34ASSETS

    for album in c:
        # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
        album_uuid = album[0]
        photo_uuid = album[1]
        # sort_order = album[2] # TODO: figure out album sort order
        sort_order = 0
        try:
            photosdb._dbalbums_uuid[photo_uuid].append(album_uuid)
        except KeyError:
            photosdb._dbalbums_uuid[photo_uuid] = [album_uuid]

        try:
            photosdb._dbalbums_album[album_uuid].append((photo_uuid, sort_order))
        except KeyError:
            photosdb._dbalbums_album[album_uuid] = [(photo_uuid, sort_order)]

    # now get additional details about albums
    c.execute(
        "SELECT "
        "ZUUID, "  # 0
        "ZTITLE, "  # 1
        "ZCLOUDLOCALSTATE, "  # 2
        "Z_PK, "  # 3
        "ZTRASHEDSTATE, "  # 4
        "ZCREATIONDATE, "  # 5
        "ZSTARTDATE, "  # 6
        "ZENDDATE, "  # 7
        "ZCUSTOMSORTASCENDING, "  # 8
        "ZCUSTOMSORTKEY "  # 9
        "FROM ZSHARE "
    )
    for album in c:
        photosdb._dbalbum_details[album[0]] = {
            "_uuid": album[0],
            "title": normalize_unicode(album[1]),
            "cloudlocalstate": album[2],
            "cloudlibrarystate": None,  # Photos 4
            "cloudidentifier": None,  # Photos 4
            "cloudownerhashedpersonid": "foobar",
            "kind": _PHOTOS_5_SHARED_ALBUM_KIND,
            "pk": album[3],
            "intrash": False if album[4] == 0 else True,
            "creation_date": album[5] or 0,  # iPhone Photos.sqlite can have null value
            "start_date": album[6] or 0,
            "end_date": album[7] or 0,
            "customsortascending": album[8],
            "customsortkey": album[9],
        }

        # add cross-reference by pk to uuid
        # needed to extract folder hierarchy
        # in Photos >= 5, folders are special albums
        photosdb._dbalbums_pk[album[8]] = album[0]


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

    photosdb = osxphotos.PhotosDB(dbfile=db)
    process_shared_albums(photosdb, print)
    albums = {"albums": album_dict(photosdb, sort_size)}
    if photosdb.db_version > _PHOTOS_4_VERSION:
        albums["shared albums"] = shared_album_dict(photosdb, sort_size)

    # cli_obj will be None if called from pytest
    if json_ or (cli_obj and cli_obj.json):
        click.echo(json.dumps(albums, ensure_ascii=False))
    else:
        click.echo(yaml.dump(albums, sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    albums()
