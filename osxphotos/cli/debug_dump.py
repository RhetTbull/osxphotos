"""debug-dump command for osxphotos CLI"""

import pprint
import time

import click
from rich import print

import osxphotos
from osxphotos._constants import _PHOTOS_4_VERSION, _UNKNOWN_PLACE
from osxphotos.queryoptions import query_options_from_kwargs

from .cli_params import (
    DB_ARGUMENT,
    DB_OPTION,
    JSON_OPTION,
    QUERY_OPTIONS,
    TIMESTAMP_OPTION,
    VERBOSE_OPTION,
)
from .common import OSXPHOTOS_HIDDEN, get_photos_db
from .list import _list_libraries
from .verbose import verbose_print


@click.command(hidden=OSXPHOTOS_HIDDEN)
@DB_OPTION
@DB_ARGUMENT
@click.option(
    "--dump",
    metavar="ATTR",
    help="Name of PhotosDB attribute to print; "
    + "can also use albums, persons, keywords, photos to dump related attributes.",
    multiple=True,
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@QUERY_OPTIONS
@click.pass_obj
@click.pass_context
def debug_dump(
    ctx, cli_obj, db, photos_library, dump, verbose_flag, timestamp, **kwargs
):
    """Print out debug info.

    When run with --dump photos, any of the query options can be used to limit the
    photos printed.  For example, to print info on currently selected photos:

    osxphotos debug-dump --dump photos --selected
    """

    verbose = verbose_print(verbose_flag, timestamp)
    db = get_photos_db(*photos_library, db, cli_obj.db if cli_obj else None)
    if db is None:
        click.echo(ctx.obj.group.commands["debug-dump"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    start_t = time.perf_counter()
    print(f"Opening database: {db}")
    photosdb = osxphotos.PhotosDB(dbfile=db, verbose=verbose)
    stop_t = time.perf_counter()
    print(f"Done; took {(stop_t-start_t):.2f} seconds")

    for attr in dump:
        if attr == "albums":
            print("_dbalbums_album:")
            pprint.pprint(photosdb._dbalbums_album)
            print("_dbalbums_uuid:")
            pprint.pprint(photosdb._dbalbums_uuid)
            print("_dbalbum_details:")
            pprint.pprint(photosdb._dbalbum_details)
            print("_dbalbum_folders:")
            pprint.pprint(photosdb._dbalbum_folders)
            print("_dbfolder_details:")
            pprint.pprint(photosdb._dbfolder_details)
        elif attr == "keywords":
            print("_dbkeywords_keyword:")
            pprint.pprint(photosdb._dbkeywords_keyword)
            print("_dbkeywords_uuid:")
            pprint.pprint(photosdb._dbkeywords_uuid)
        elif attr == "persons":
            print("_dbfaces_uuid:")
            pprint.pprint(photosdb._dbfaces_uuid)
            print("_dbfaces_pk:")
            pprint.pprint(photosdb._dbfaces_pk)
            print("_dbpersons_pk:")
            pprint.pprint(photosdb._dbpersons_pk)
            print("_dbpersons_fullname:")
            pprint.pprint(photosdb._dbpersons_fullname)
        elif attr == "photos":
            query_options = query_options_from_kwargs(**kwargs)
            photos = photosdb.query(options=query_options)
            uuid = [photo.uuid for photo in photos]
            for uuid_ in uuid:
                print(f"_dbphotos['{uuid_}']:")
                try:
                    pprint.pprint(photosdb._dbphotos[uuid_])
                except KeyError:
                    print(f"Did not find uuid {uuid_} in _dbphotos")
        else:
            try:
                val = getattr(photosdb, attr)
                print(f"{attr}:")
                pprint.pprint(val)
            except Exception:
                print(f"Did not find attribute {attr} in PhotosDB")
