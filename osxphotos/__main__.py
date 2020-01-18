import csv
import datetime
import json
import os
import os.path
import pathlib
import sys

import click
import yaml

import osxphotos

from ._constants import _EXIF_TOOL_URL, _PHOTOS_5_VERSION
from ._version import __version__
from .utils import create_path_by_date, _copy_file

# TODO: add "--any" to search any field (e.g. keyword, description, title contains "wedding") (add case insensitive option)
# TODO: add search for filename


def get_photos_db(*db_options):
    """ Return path to photos db, select first non-None arg 
    """
    if db_options:
        for db in db_options:
            if db is not None:
                return db

    # _list_libraries()
    return None

    # if get here, no valid database paths passed, so ask user

    # _, major, _ = osxphotos.utils._get_os_version()

    # last_lib = osxphotos.utils.get_last_library_path()
    # if last_lib is not None:
    #     db = last_lib
    #     return db

    # sys_lib = None
    # if int(major) >= 15:
    #     sys_lib = osxphotos.utils.get_system_library_path()

    # if sys_lib is not None:
    #     db = sys_lib
    #     return db

    # db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    # if os.path.isdir(db):
    #     return db
    # else:
    #     return None  ### TODO: put list here


# Click CLI object & context settings
class CLI_Obj:
    def __init__(self, db=None, json=False, debug=False):
        if debug:
            osxphotos._set_debug(True)
        self.db = db
        self.json = json


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.option("--debug", required=False, is_flag=True, default=False, hidden=True)
@click.version_option(__version__, "--version", "-v")
@click.pass_context
def cli(ctx, db, json, debug):
    ctx.obj = CLI_Obj(db=db, json=json, debug=debug)


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def keywords(ctx, cli_obj, db, json_, photos_library):
    """ Print out keywords found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["keywords"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    keywords = {"keywords": photosdb.keywords_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(keywords))
    else:
        click.echo(yaml.dump(keywords, sort_keys=False))


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def albums(ctx, cli_obj, db, json_, photos_library):
    """ Print out albums found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["albums"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    albums = {"albums": photosdb.albums_as_dict}
    if photosdb.db_version >= _PHOTOS_5_VERSION:
        albums["shared albums"] = photosdb.albums_shared_as_dict

    if json_ or cli_obj.json:
        click.echo(json.dumps(albums))
    else:
        click.echo(yaml.dump(albums, sort_keys=False))


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def persons(ctx, cli_obj, db, json_, photos_library):
    """ Print out persons (faces) found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["persons"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    persons = {"persons": photosdb.persons_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(persons))
    else:
        click.echo(yaml.dump(persons, sort_keys=False))


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def info(ctx, cli_obj, db, json_, photos_library):
    """ Print out descriptive info of the Photos library database. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["info"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    pdb = osxphotos.PhotosDB(dbfile=db)
    info = {}
    info["database_path"] = pdb.db_path
    info["database_version"] = pdb.db_version

    photos = pdb.photos()
    not_shared_photos = [p for p in photos if not p.shared]
    info["photo_count"] = len(not_shared_photos)

    hidden = [p for p in photos if p.hidden]
    info["hidden_photo_count"] = len(hidden)

    movies = pdb.photos(images=False, movies=True)
    not_shared_movies = [p for p in movies if not p.shared]
    info["movie_count"] = len(not_shared_movies)

    if pdb.db_version >= _PHOTOS_5_VERSION:
        shared_photos = [p for p in photos if p.shared]
        info["shared_photo_count"] = len(shared_photos)

        shared_movies = [p for p in movies if p.shared]
        info["shared_movie_count"] = len(shared_movies)

    keywords = pdb.keywords_as_dict
    info["keywords_count"] = len(keywords)
    info["keywords"] = keywords

    albums = pdb.albums_as_dict
    info["albums_count"] = len(albums)
    info["albums"] = albums

    if pdb.db_version >= _PHOTOS_5_VERSION:
        albums_shared = pdb.albums_shared_as_dict
        info["shared_albums_count"] = len(albums_shared)
        info["shared_albums"] = albums_shared

    persons = pdb.persons_as_dict

    # handle empty person names (added by Photos 5.0+ when face detected but not identified)
    # TODO: remove this
    # noperson = "UNKNOWN"
    # if "" in persons:
    #     if noperson in persons:
    #         persons[noperson].append(persons[""])
    #     else:
    #         persons[noperson] = persons[""]
    #     persons.pop("", None)

    info["persons_count"] = len(persons)
    info["persons"] = persons

    if cli_obj.json or json_:
        click.echo(json.dumps(info))
    else:
        click.echo(yaml.dump(info, sort_keys=False))


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def dump(ctx, cli_obj, db, json_, photos_library):
    """ Print list of all photos & associated info from the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["dump"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    pdb = osxphotos.PhotosDB(dbfile=db)
    photos = pdb.photos(movies=True)
    print_photo_info(photos, json_ or cli_obj.json)


@cli.command(name="list")
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.pass_obj
@click.pass_context
def list_libraries(ctx, cli_obj, json_):
    """ Print list of Photos libraries found on the system. """
    _list_libraries(json_=json_ or cli_obj.json)


def _list_libraries(json_=False):
    """ Print list of Photos libraries found on the system. 
        If json_ == True, print output as JSON (default = False) """

    photo_libs = osxphotos.utils.list_photo_libraries()
    sys_lib = osxphotos.utils.get_system_library_path()
    last_lib = osxphotos.utils.get_last_library_path()

    if json_:
        libs = {
            "photo_libraries": photo_libs,
            "system_library": sys_lib,
            "last_library": last_lib,
        }
        click.echo(json.dumps(libs))
    else:
        last_lib_flag = sys_lib_flag = False

        for lib in photo_libs:
            if lib == sys_lib:
                click.echo(f"(*)\t{lib}")
                sys_lib_flag = True
            elif lib == last_lib:
                click.echo(f"(#)\t{lib}")
                last_lib_flag = True
            else:
                click.echo(f"\t{lib}")

        if sys_lib_flag or last_lib_flag:
            click.echo("\n")
        if sys_lib_flag:
            click.echo("(*)\tSystem Photos Library")
        if last_lib_flag:
            click.echo("(#)\tLast opened Photos Library")


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.option("--keyword", default=None, multiple=True, help="Search for keyword(s).")
@click.option("--person", default=None, multiple=True, help="Search for person(s).")
@click.option("--album", default=None, multiple=True, help="Search for album(s).")
@click.option("--uuid", default=None, multiple=True, help="Search for UUID(s).")
@click.option(
    "--title", default=None, multiple=True, help="Search for TEXT in title of photo."
)
@click.option("--no-title", is_flag=True, help="Search for photos with no title.")
@click.option(
    "--description",
    default=None,
    multiple=True,
    help="Search for TEXT in description of photo.",
)
@click.option(
    "--no-description", is_flag=True, help="Search for photos with no description."
)
@click.option(
    "--uti",
    default=None,
    multiple=False,
    help="Search for photos whose uniform type identifier (UTI) matches TEXT",
)
@click.option(
    "-i",
    "--ignore-case",
    is_flag=True,
    help="Case insensitive search for title or description. Does not apply to keyword, person, or album.",
)
@click.option("--edited", is_flag=True, help="Search for photos that have been edited.")
@click.option(
    "--external-edit", is_flag=True, help="Search for photos edited in external editor."
)
@click.option("--favorite", is_flag=True, help="Search for photos marked favorite.")
@click.option(
    "--not-favorite", is_flag=True, help="Search for photos not marked favorite."
)
@click.option("--hidden", is_flag=True, help="Search for photos marked hidden.")
@click.option("--not-hidden", is_flag=True, help="Search for photos not marked hidden.")
@click.option("--missing", is_flag=True, help="Search for photos missing from disk.")
@click.option(
    "--not-missing",
    is_flag=True,
    help="Search for photos present on disk (e.g. not missing).",
)
@click.option(
    "--shared",
    is_flag=True,
    help="Search for photos in shared iCloud album (Photos 5 only).",
)
@click.option(
    "--not-shared",
    is_flag=True,
    help="Search for photos not in shared iCloud album (Photos 5 only).",
)
@click.option(
    "--burst", is_flag=True, help="Search for photos that were taken in a burst."
)
@click.option(
    "--not-burst", is_flag=True, help="Search for photos that are not part of a burst."
)
@click.option("--live", is_flag=True, help="Search for Apple live photos")
@click.option(
    "--not-live", is_flag=True, help="Search for photos that are not Apple live photos"
)
@click.option(
    "--cloudasset",
    is_flag=True,
    help="Search for photos that are part of an iCloud library",
)
@click.option(
    "--not-cloudasset",
    is_flag=True,
    help="Search for photos that are not part of an iCloud library",
)
@click.option(
    "--incloud",
    is_flag=True,
    help="Search for photos that are in iCloud (have been synched)",
)
@click.option(
    "--not-incloud",
    is_flag=True,
    help="Search for photos that are not in iCloud (have not been synched)",
)
@click.option(
    "--only-movies",
    is_flag=True,
    help="Search only for movies (default searches both images and movies).",
)
@click.option(
    "--only-photos",
    is_flag=True,
    help="Search only for photos/images (default searches both images and movies).",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def query(
    ctx,
    cli_obj,
    db,
    photos_library,
    keyword,
    person,
    album,
    uuid,
    title,
    no_title,
    description,
    no_description,
    ignore_case,
    json_,
    edited,
    external_edit,
    favorite,
    not_favorite,
    hidden,
    not_hidden,
    missing,
    not_missing,
    shared,
    not_shared,
    only_movies,
    only_photos,
    uti,
    burst,
    not_burst,
    live,
    not_live,
    cloudasset,
    not_cloudasset,
    incloud,
    not_incloud,
):
    """ Query the Photos database using 1 or more search options; 
        if more than one option is provided, they are treated as "AND" 
        (e.g. search for photos matching all options).
    """

    # if no query terms, show help and return
    if not any(
        [
            keyword,
            person,
            album,
            uuid,
            title,
            no_title,
            description,
            no_description,
            edited,
            external_edit,
            favorite,
            not_favorite,
            hidden,
            not_hidden,
            missing,
            not_missing,
            shared,
            not_shared,
            only_movies,
            only_photos,
            uti,
            burst,
            not_burst,
            live,
            not_live,
            cloudasset,
            not_cloudasset,
            incloud,
            not_incloud,
        ]
    ):
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif favorite and not_favorite:
        # can't search for both favorite and notfavorite
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif hidden and not_hidden:
        # can't search for both hidden and nothidden
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif missing and not_missing:
        # can't search for both missing and notmissing
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif title and no_title:
        # can't search for both title and no_title
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif description and no_description:
        # can't search for both description and no_description
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif only_photos and only_movies:
        # can't have only photos and only movies
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif burst and not_burst:
        # can't search for both burst and not_burst
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif live and not_live:
        # can't search for both live and not_live
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif cloudasset and not_cloudasset:
        # can't search for both live and not_live
        click.echo(cli.commands["query"].get_help(ctx))
        return
    elif incloud and not_incloud:
        # can't search for both live and not_live
        click.echo(cli.commands["query"].get_help(ctx))
        return

    # actually have something to query
    isphoto = ismovie = True  # default searches for everything
    if only_movies:
        isphoto = False
    if only_photos:
        ismovie = False

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["query"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    photos = _query(
        db,
        keyword,
        person,
        album,
        uuid,
        title,
        no_title,
        description,
        no_description,
        ignore_case,
        edited,
        external_edit,
        favorite,
        not_favorite,
        hidden,
        not_hidden,
        missing,
        not_missing,
        shared,
        not_shared,
        isphoto,
        ismovie,
        uti,
        burst,
        not_burst,
        live,
        not_live,
        cloudasset,
        not_cloudasset,
        incloud,
        not_incloud,
    )
    print_photo_info(photos, cli_obj.json or json_)


@cli.command()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument.",
    type=click.Path(exists=True),
)
@click.option("--keyword", default=None, multiple=True, help="Search for keyword(s).")
@click.option("--person", default=None, multiple=True, help="Search for person(s).")
@click.option("--album", default=None, multiple=True, help="Search for album(s).")
@click.option("--uuid", default=None, multiple=True, help="Search for UUID(s).")
@click.option(
    "--title", default=None, multiple=True, help="Search for TEXT in title of photo."
)
@click.option("--no-title", is_flag=True, help="Search for photos with no title.")
@click.option(
    "--description",
    default=None,
    multiple=True,
    help="Search for TEXT in description of photo.",
)
@click.option(
    "--no-description", is_flag=True, help="Search for photos with no description."
)
@click.option(
    "--uti",
    default=None,
    multiple=False,
    help="Search for photos whose uniform type identifier (UTI) matches TEXT",
)
@click.option(
    "-i",
    "--ignore-case",
    is_flag=True,
    help="Case insensitive search for title or description. Does not apply to keyword, person, or album.",
)
@click.option("--edited", is_flag=True, help="Search for photos that have been edited.")
@click.option(
    "--external-edit", is_flag=True, help="Search for photos edited in external editor."
)
@click.option("--favorite", is_flag=True, help="Search for photos marked favorite.")
@click.option(
    "--not-favorite", is_flag=True, help="Search for photos not marked favorite."
)
@click.option("--hidden", is_flag=True, help="Search for photos marked hidden.")
@click.option("--not-hidden", is_flag=True, help="Search for photos not marked hidden.")
@click.option(
    "--burst", is_flag=True, help="Search for photos that were taken in a burst."
)
@click.option(
    "--not-burst", is_flag=True, help="Search for photos that are not part of a burst."
)
@click.option("--live", is_flag=True, help="Search for Apple live photos")
@click.option(
    "--not-live", is_flag=True, help="Search for photos that are not Apple live photos"
)
@click.option(
    "--shared",
    is_flag=True,
    help="Search for photos in shared iCloud album (Photos 5 only).",
)
@click.option(
    "--not-shared",
    is_flag=True,
    help="Search for photos not in shared iCloud album (Photos 5 only).",
)
@click.option("--verbose", "-V", is_flag=True, help="Print verbose output.")
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing files. "
    "Default behavior is to add (1), (2), etc to filename if file already exists. "
    "Use this with caution as it may create name collisions on export. "
    "(e.g. if two files happen to have the same name)",
)
@click.option(
    "--export-by-date",
    is_flag=True,
    help="Automatically create output folders to organize photos by date created "
    "(e.g. DEST/2019/12/20/photoname.jpg).",
)
@click.option(
    "--export-edited",
    is_flag=True,
    help="Also export edited version of photo if an edited version exists.  "
    'Edited photo will be named in form of "photoname_edited.ext"',
)
@click.option(
    "--export-bursts",
    is_flag=True,
    help="If a photo is a burst photo export all associated burst images in the library.",
)
@click.option(
    "--export-live",
    is_flag=True,
    help="If a photo is a live photo export the associated live video component."
    "  Live video will have same name as photo but with .mov extension. ",
)
@click.option(
    "--original-name",
    is_flag=True,
    help="Use photo's original filename instead of current filename for export.",
)
@click.option(
    "--sidecar",
    is_flag=True,
    help="Create JSON sidecar for each photo exported "
    f"in format useable by exiftool ({_EXIF_TOOL_URL}) "
    "The sidecar file can be used to apply metadata to the file with exiftool, for example: "
    '"exiftool -j=photoname.jpg.json photoname.jpg" '
    "The sidecar file is named in format photoname.ext.json where ext is extension of the photo (e.g. jpg). "
    "Note: this does not create an XMP sidecar as used by Lightroom, etc.",
)
@click.option(
    "--only-movies",
    is_flag=True,
    help="Search only for movies (default searches both images and movies).",
)
@click.option(
    "--only-photos",
    is_flag=True,
    help="Search only for photos/images (default searches both images and movies).",
)
@click.option(
    "--download-missing",
    is_flag=True,
    help="Attempt to download missing photos from iCloud. The current implementation uses Applescript "
    "to interact with Photos to export the photo which will force Photos to download from iCloud if "
    "the photo does not exist on disk.  This will be slow and will require internet connection. "
    "This obviously only works if the Photos library is synched to iCloud.",
)
@click.argument("photos_library", nargs=-1, type=click.Path(exists=True))
@click.argument("dest", nargs=1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def export(
    ctx,
    cli_obj,
    db,
    photos_library,
    keyword,
    person,
    album,
    uuid,
    title,
    no_title,
    description,
    no_description,
    uti,
    ignore_case,
    edited,
    external_edit,
    favorite,
    not_favorite,
    hidden,
    not_hidden,
    shared,
    not_shared,
    verbose,
    overwrite,
    export_by_date,
    export_edited,
    export_bursts,
    export_live,
    original_name,
    sidecar,
    only_photos,
    only_movies,
    burst,
    not_burst,
    live,
    not_live,
    download_missing,
    dest,
):
    """ Export photos from the Photos database.
        Export path DEST is required.
        Optionally, query the Photos database using 1 or more search options; 
        if more than one option is provided, they are treated as "AND" 
        (e.g. search for photos matching all options).
        If no query options are provided, all photos will be exported.
    """

    if not os.path.isdir(dest):
        sys.exit("DEST must be valid path")

    # sanity check input args
    if favorite and not_favorite:
        # can't search for both favorite and notfavorite
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif hidden and not_hidden:
        # can't search for both hidden and nothidden
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif title and no_title:
        # can't search for both title and no_title
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif description and no_description:
        # can't search for both description and no_description
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif only_photos and only_movies:
        # can't have only photos and only movies
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif burst and not_burst:
        # can't search for both burst and not_burst
        click.echo(cli.commands["export"].get_help(ctx))
        return
    elif live and not_live:
        # can't search for both live and not_live
        click.echo(cli.commands["export"].get_help(ctx))
        return

    isphoto = ismovie = True  # default searches for everything
    if only_movies:
        isphoto = False
    if only_photos:
        ismovie = False

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["export"].get_help(ctx))
        click.echo("\n\nLocated the following Photos library databases: ")
        _list_libraries()
        return

    photos = _query(
        db,
        keyword,
        person,
        album,
        uuid,
        title,
        no_title,
        description,
        no_description,
        ignore_case,
        edited,
        external_edit,
        favorite,
        not_favorite,
        hidden,
        not_hidden,
        None,  # missing -- won't export these but will warn user
        None,  # not-missing
        shared,
        not_shared,
        isphoto,
        ismovie,
        uti,
        burst,
        not_burst,
        live,
        not_live,
        False,  # cloudasset
        False,  # not_cloudasset
        False,  # incloud
        False,  # not_incloud
    )

    if photos:
        if export_bursts:
            # add the burst_photos to the export set
            photos_burst = [p for p in photos if p.burst]
            for burst in photos_burst:
                burst_set = [p for p in burst.burst_photos if not p.ismissing]
                photos.extend(burst_set)

        num_photos = len(photos)
        photo_str = "photos" if num_photos > 1 else "photo"
        click.echo(f"Exporting {num_photos} {photo_str} to {dest}...")
        if not verbose:
            # show progress bar
            with click.progressbar(photos) as bar:
                for p in bar:
                    export_photo(
                        p,
                        dest,
                        verbose,
                        export_by_date,
                        sidecar,
                        overwrite,
                        export_edited,
                        original_name,
                        export_live,
                        download_missing,
                    )
        else:
            for p in photos:
                export_path = export_photo(
                    p,
                    dest,
                    verbose,
                    export_by_date,
                    sidecar,
                    overwrite,
                    export_edited,
                    original_name,
                    export_live,
                    download_missing,
                )
                if export_path:
                    click.echo(f"Exported {p.filename} to {export_path}")
                else:
                    click.echo(f"Did not export missing file {p.filename}")
    else:
        click.echo("Did not find any photos to export")


@cli.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx, topic, **kw):
    """ Print help; for help on commands: help <command>. """
    if topic is None:
        click.echo(ctx.parent.get_help())
    else:
        ctx.info_name = topic 
        click.echo(cli.commands[topic].get_help(ctx))


def print_photo_info(photos, json=False):
    if json:
        dump = []
        for p in photos:
            dump.append(p.json())
        click.echo(f"[{', '.join(dump)}]")
    else:
        # dump as CSV
        csv_writer = csv.writer(
            sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        dump = []
        # add headers
        dump.append(
            [
                "uuid",
                "filename",
                "original_filename",
                "date",
                "description",
                "title",
                "keywords",
                "albums",
                "persons",
                "path",
                "ismissing",
                "hasadjustments",
                "external_edit",
                "favorite",
                "hidden",
                "shared",
                "latitude",
                "longitude",
                "path_edited",
                "isphoto",
                "ismovie",
                "uti",
                "burst",
                "live_photo",
                "path_live_photo",
                "iscloudasset",
                "incloud",
            ]
        )
        for p in photos:
            dump.append(
                [
                    p.uuid,
                    p.filename,
                    p.original_filename,
                    p.date.isoformat(),
                    p.description,
                    p.title,
                    ", ".join(p.keywords),
                    ", ".join(p.albums),
                    ", ".join(p.persons),
                    p.path,
                    p.ismissing,
                    p.hasadjustments,
                    p.external_edit,
                    p.favorite,
                    p.hidden,
                    p.shared,
                    p._latitude,
                    p._longitude,
                    p.path_edited,
                    p.isphoto,
                    p.ismovie,
                    p.uti,
                    p.burst,
                    p.live_photo,
                    p.path_live_photo,
                    p.iscloudasset,
                    p.incloud,
                ]
            )
        for row in dump:
            csv_writer.writerow(row)


def _query(
    db,
    keyword,
    person,
    album,
    uuid,
    title,
    no_title,
    description,
    no_description,
    ignore_case,
    edited,
    external_edit,
    favorite,
    not_favorite,
    hidden,
    not_hidden,
    missing,
    not_missing,
    shared,
    not_shared,
    isphoto,
    ismovie,
    uti,
    burst,
    not_burst,
    live,
    not_live,
    cloudasset,
    not_cloudasset,
    incloud,
    not_incloud,
):
    """ run a query against PhotosDB to extract the photos based on user supply criteria """
    """ used by query and export commands """
    """ arguments must be passed in same order as query and export """
    """ if either is modified, need to ensure all three functions are updated """

    # TODO: this is getting too hairy -- need to change to named args

    photosdb = osxphotos.PhotosDB(dbfile=db)
    photos = photosdb.photos(
        keywords=keyword,
        persons=person,
        albums=album,
        uuid=uuid,
        images=isphoto,
        movies=ismovie,
    )

    if title:
        # search title field for text
        # if more than one, find photos with all title values in title
        if ignore_case:
            # case-insensitive
            for t in title:
                t = t.lower()
                photos = [p for p in photos if p.title and t in p.title.lower()]
        else:
            for t in title:
                photos = [p for p in photos if p.title and t in p.title]
    elif no_title:
        photos = [p for p in photos if not p.title]

    if description:
        # search description field for text
        # if more than one, find photos with all name values in description
        if ignore_case:
            # case-insensitive
            for d in description:
                d = d.lower()
                photos = [
                    p for p in photos if p.description and d in p.description.lower()
                ]
        else:
            for d in description:
                photos = [p for p in photos if p.description and d in p.description]
    elif no_description:
        photos = [p for p in photos if not p.description]

    if edited:
        photos = [p for p in photos if p.hasadjustments]

    if external_edit:
        photos = [p for p in photos if p.external_edit]

    if favorite:
        photos = [p for p in photos if p.favorite]
    elif not_favorite:
        photos = [p for p in photos if not p.favorite]

    if hidden:
        photos = [p for p in photos if p.hidden]
    elif not_hidden:
        photos = [p for p in photos if not p.hidden]

    if missing:
        photos = [p for p in photos if p.ismissing]
    elif not_missing:
        photos = [p for p in photos if not p.ismissing]

    if shared:
        photos = [p for p in photos if p.shared]
    elif not_shared:
        photos = [p for p in photos if not p.shared]

    if shared:
        photos = [p for p in photos if p.shared]
    elif not_shared:
        photos = [p for p in photos if not p.shared]

    if uti:
        photos = [p for p in photos if uti in p.uti]

    if burst:
        photos = [p for p in photos if p.burst]
    elif not_burst:
        photos = [p for p in photos if not p.burst]

    if live:
        photos = [p for p in photos if p.live_photo]
    elif not_live:
        photos = [p for p in photos if not p.live_photo]

    if cloudasset:
        photos = [p for p in photos if p.iscloudasset]
    elif not_cloudasset:
        photos = [p for p in photos if not p.iscloudasset]

    if incloud:
        photos = [p for p in photos if p.incloud]
    elif not_incloud:
        photos = [p for p in photos if not p.incloud]

    return photos


def export_photo(
    photo,
    dest,
    verbose,
    export_by_date,
    sidecar,
    overwrite,
    export_edited,
    original_name,
    export_live,
    download_missing,
):
    """ Helper function for export that does the actual export
        photo: PhotoInfo object
        dest: destination path as string
        verbose: boolean; print verbose output
        export_by_date: boolean; create export folder in form dest/YYYY/MM/DD
        sidecar: boolean; create json sidecar file with export
        overwrite: boolean; overwrite dest file if it already exists
        original_name: boolean; use original filename instead of current filename
        export_live: boolean; also export live video component if photo is a live photo
                     live video will have same name as photo but with .mov extension
        download_missing: attempt download of missing iCloud photos
        returns destination path of exported photo or None if photo was missing 
    """

    if not download_missing:
        if photo.ismissing:
            space = " " if not verbose else ""
            click.echo(f"{space}Skipping missing photo {photo.filename}")
            return None
        elif not os.path.exists(photo.path):
            space = " " if not verbose else ""
            click.echo(
                f"{space}WARNING: file {photo.path} is missing but ismissing=False, "
                f"skipping {photo.filename}"
            )
            return None
    elif photo.ismissing and not photo.iscloudasset or not photo.incloud:
        click.echo(
            f"Skipping missing {photo.filename}: not iCloud asset or missing from cloud"
        )
        return None

    filename = None
    if original_name:
        filename = photo.original_filename
    else:
        filename = photo.filename

    if verbose:
        click.echo(f"Exporting {photo.filename} as {filename}")

    if export_by_date:
        date_created = photo.date.timetuple()
        dest = create_path_by_date(dest, date_created)

    photo_path = photo.export(
        dest,
        filename,
        sidecar=sidecar,
        overwrite=overwrite,
        use_photos_export=download_missing,
    )

    # if export-edited, also export the edited version
    # verify the photo has adjustments and valid path to avoid raising an exception
    if export_edited and photo.hasadjustments:
        if download_missing or photo.path_edited is not None:
            edited_name = pathlib.Path(filename)
            edited_name = f"{edited_name.stem}_edited{edited_name.suffix}"
            if verbose:
                click.echo(f"Exporting edited version of {filename} as {edited_name}")
            photo.export(
                dest,
                edited_name,
                sidecar=sidecar,
                overwrite=overwrite,
                edited=True,
                use_photos_export=download_missing,
            )
        else:
            click.echo(f"Skipping missing edited photo for {filename}")

    if export_live and photo.live_photo and photo.path_live_photo is not None:
        # if destination exists, will be overwritten regardless of overwrite
        # so that name matches name of live photo
        live_name = pathlib.Path(photo_path)
        live_name = f"{live_name.stem}.mov"

        src_live = photo.path_live_photo
        dest_live = pathlib.Path(photo_path).parent / pathlib.Path(live_name)

        if src_live is not None:
            if verbose:
                click.echo(f"Exporting live photo video of {filename} as {live_name}")

            _copy_file(src_live, str(dest_live))
        else:
            click.echo(f"Skipping missing live movie for {filename}")

    return photo_path


if __name__ == "__main__":
    cli()
