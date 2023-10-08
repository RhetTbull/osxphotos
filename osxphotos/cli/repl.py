"""repl command for osxphotos CLI"""
from __future__ import annotations

import os
import os.path
import pathlib
import re
import shlex
import subprocess
import sys
import time
from functools import partial
from typing import List

import click
from rich import pretty, print

import osxphotos
from osxphotos._constants import _PHOTOS_4_VERSION
from osxphotos.cli.click_rich_echo import rich_echo_error as echo_error
from osxphotos.iphoto import is_iphoto_library
from osxphotos.photoinfo import PhotoInfo
from osxphotos.photoquery import (
    IncompatibleQueryOptions,
    QueryOptions,
    query_options_from_kwargs,
)
from osxphotos.photosdb import PhotosDB
from osxphotos.platform import assert_macos, is_macos
from osxphotos.pyrepl import embed_repl

if is_macos:
    import photoscript
    from applescript import ScriptError
    from osxphotos.photos_selection import PhotosSelection

from .cli_params import DB_ARGUMENT, DB_OPTION, DELETED_OPTIONS, QUERY_OPTIONS
from .common import get_photos_db


@click.command(name="repl")
@DB_OPTION
@click.pass_obj
@click.pass_context
@click.option(
    "--emacs",
    required=False,
    is_flag=True,
    default=False,
    help="Launch REPL with Emacs keybindings (default is vi bindings)",
)
@click.option(
    "--beta",
    is_flag=True,
    default=False,
    hidden=True,
    help="Enable beta options.",
)
@QUERY_OPTIONS
@DELETED_OPTIONS
def repl(ctx, cli_obj, db, emacs, beta, **kwargs):
    """Run interactive osxphotos REPL shell (useful for debugging, prototyping, and inspecting your Photos library)"""
    import logging

    from objexplore import explore

    if is_macos:
        from photoscript import Album, Photo, PhotosLibrary
    from rich import inspect as _inspect

    from osxphotos import ExifTool, PhotoInfo, PhotosDB
    from osxphotos.albuminfo import AlbumInfo
    from osxphotos.exifwriter import ExifWriter
    from osxphotos.exportoptions import ExportOptions, ExportResults
    from osxphotos.momentinfo import MomentInfo
    from osxphotos.photoexporter import PhotoExporter
    from osxphotos.photoquery import QueryOptions
    from osxphotos.placeinfo import PlaceInfo
    from osxphotos.scoreinfo import ScoreInfo
    from osxphotos.searchinfo import SearchInfo
    from osxphotos.sidecars import SidecarWriter, exiftool_json_sidecar, xmp_sidecar

    logger = logging.getLogger()
    logger.disabled = True

    pretty.install()
    try:
        query_options = query_options_from_kwargs(**kwargs)
    except IncompatibleQueryOptions as e:
        echo_error(f"Incompatible query options: {e}")
        ctx.exit(1)
    print(f"python version: {sys.version}")
    print(f"osxphotos version: {osxphotos._version.__version__}")
    db = db or get_photos_db()
    photosdb = _load_photos_db(db)
    # enable beta features if requested
    if beta:
        photosdb._beta = beta
        print("Beta mode enabled")
    print("Getting photos")
    tic = time.perf_counter()
    photos = _query_photos(photosdb, query_options)
    all_photos = _get_all_photos(photosdb)
    toc = time.perf_counter()
    tictoc = toc - tic

    # shortcut for helper functions
    get_photo = photosdb.get_photo
    find = partial(_find_in_library, photosdb)

    if is_macos:
        show = _show_photo
        spotlight = _spotlight_photo
        selected = PhotosSelection(photosdb)

    def inspect(obj):
        """inspect object"""
        return _inspect(obj, methods=True)

    print(f"Found {len(photos)} photos in {tictoc:0.2f} seconds\n")
    print("The following classes have been imported from osxphotos:")
    print(
        "- AlbumInfo, ExifTool, PhotoInfo, PhotoExporter, ExportOptions, ExportResults, "
        "PhotosDB, PlaceInfo, QueryOptions, MomentInfo, ScoreInfo, SearchInfo, "
        "SidecarWriter, ExifWriter\n"
    )
    print("The following variables are defined:")
    print(f"- photosdb: PhotosDB() instance for '{photosdb.library_path}'")
    print(
        f"- photos: list of PhotoInfo objects for all photos filtered with any query options passed on command line (len={len(photos)})"
    )
    print(
        f"- all_photos: list of PhotoInfo objects for all photos in photosdb, including those in the trash (len={len(all_photos)})"
    )
    if is_macos:
        print(
            f"- selected: list of PhotoInfo objects for any photos selected in Photos (len={len(selected)}); "
            "will dynamically update as photos are selected in Photos"
        )
    print(f"\nThe following functions may be helpful:")
    print(
        "- get_photo(uuid): return a PhotoInfo object for photo with uuid; e.g. get_photo('B13F4485-94E0-41CD-AF71-913095D62E31')"
    )
    if is_macos:
        print(
            "- show(photo): open a photo object in the default viewer; e.g. show(selected[0])"
        )
        print(
            "- show(path): open a file at path in the default viewer; e.g. show('/path/to/photo.jpg')"
        )
        print("- spotlight(photo): open a photo and spotlight it in Photos")
    # print(
    #     f"- help(object): print help text including list of methods for object; for example, help(PhotosDB)"
    # )
    print(
        "- inspect(object): print information about an object; e.g. inspect(PhotoInfo)"
    )
    print(
        "- explore(object): interactively explore an object with objexplore; e.g. explore(PhotoInfo)"
    )
    print(
        "- find(text): search for files matching text in Photos library; e.g. find('B13F4485')"
    )
    print("- q, quit, quit(), exit, exit(): exit this interactive shell\n")

    embed_repl(
        globals=globals(),
        locals=locals(),
        history_filename=str(pathlib.Path.home() / ".osxphotos_repl_history"),
        quit_words=["q", "quit", "exit"],
        vi_mode=not emacs,
    )


def _show_photo(photo: PhotoInfo):
    """open image with default image viewer

    Note: This is for debugging only -- it will actually open any filetype which could
    be very, very bad.

    Args:
        photo: PhotoInfo object or a path to a photo on disk
    """
    photopath = photo.path if isinstance(photo, osxphotos.PhotoInfo) else photo

    if not os.path.isfile(photopath):
        return f"'{photopath}' does not appear to be a valid photo path"

    os.system(f"open '{photopath}'")


def _load_photos_db(dbpath):
    print("Loading database")
    tic = time.perf_counter()
    photosdb = (
        osxphotos.iPhotoDB(dbpath, verbose=print)
        if is_iphoto_library(dbpath)
        else osxphotos.PhotosDB(dbfile=dbpath, verbose=print)
    )
    toc = time.perf_counter()
    tictoc = toc - tic
    print(f"Done: took {tictoc:0.2f} seconds")
    return photosdb


def _get_all_photos(photosdb):
    """get list of all photos in photosdb"""
    photos = photosdb.photos(images=True, movies=True)
    photos.extend(photosdb.photos(images=True, movies=True, intrash=True))
    return photos


def _spotlight_photo(photo: PhotoInfo):
    assert_macos()
    photo_ = photoscript.Photo(photo.uuid)
    photo_.spotlight()


def _query_photos(photosdb: PhotosDB, query_options: QueryOptions) -> List:
    """Query photos given a QueryOptions instance"""
    try:
        photos = photosdb.query(query_options)
    except ValueError as e:
        if "Invalid query_eval CRITERIA:" not in str(e):
            raise ValueError(e) from e
        msg = str(e).split(":")[1]
        raise click.BadOptionUsage(
            "query_eval", f"Invalid query-eval CRITERIA: {msg}"
        ) from e

    return photos


def _find_in_library(photosdb: PhotosDB, search_str: str) -> list[str]:
    """Find files in Photos library matching search_str using find command"""
    # this is a quick and dirty way to find files in the Photos library
    # e.g. those matching a UUID or a filename
    library_path = photosdb.library_path
    if not library_path:
        raise ValueError("Could not find Photos library")

    search_str = shlex.quote(search_str)
    library_path = shlex.quote(library_path)
    cmd = f"find {library_path} | grep {search_str}"
    output = subprocess.check_output(cmd, shell=True, universal_newlines=True)

    # Split the output into lines and return as a list
    return output.strip().split("\n")
