import csv
import datetime
import json
import logging
import os
import os.path
import pathlib
import sys

import click
import yaml
from pathvalidate import (
    is_valid_filename,
    is_valid_filepath,
    sanitize_filepath,
    sanitize_filename,
)

import osxphotos

from ._constants import _EXIF_TOOL_URL, _PHOTOS_5_VERSION, _UNKNOWN_PLACE
from ._version import __version__
from .exiftool import get_exiftool_path
from .template import (
    render_filepath_template,
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
)
from .utils import _copy_file, create_path_by_date


def get_photos_db(*db_options):
    """ Return path to photos db, select first non-None db_options
        If no db_options are non-None, try to find library to use in
        the following order:
        - last library opened
        - system library
        - ~/Pictures/Photos Library.photoslibrary
        - failing above, returns None
    """
    if db_options:
        for db in db_options:
            if db is not None:
                return db

    # if get here, no valid database paths passed, so try to figure out which to use
    db = osxphotos.utils.get_last_library_path()
    if db is not None:
        click.echo(f"Using last opened Photos library: {db}", err=True)
        return db

    db = osxphotos.utils.get_system_library_path()
    if db is not None:
        click.echo(f"Using system Photos library: {db}", err=True)
        return db

    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    if os.path.isdir(db):
        click.echo(f"Using Photos library: {db}", err=True)
        return db
    else:
        return None


# Click CLI object & context settings
class CLI_Obj:
    def __init__(self, db=None, json=False, debug=False):
        if debug:
            osxphotos._set_debug(True)
        self.db = db
        self.json = json


class ExportCommand(click.Command):
    """ Custom click.Command that overrides get_help() to show additional help info for export """

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = click.HelpFormatter()

        formatter.write("\n\n")
        # passed to click.HelpFormatter.write_dl for formatting
        formatter.write_text("**Templating System**")
        formatter.write("\n")
        formatter.write_text(
            "With the --directory option, you may specify a template for the "
            + "export directory.  This directory will be appended to the export path specified "
            + "in the export DEST argument to export.  For example, if template is "
            + "'{created.year}/{created.month}', and export desitnation DEST is "
            + "'/Users/maria/Pictures/export', "
            + "the actual export directory for a photo would be '/Users/maria/Pictures/export/2020/March' "
            + "if the photo was created in March 2020. "
        )
        formatter.write("\n")
        formatter.write_text(
            "In the template, valid template substitutions will be replaced by "
            + "the corresponding value from the table below.  Invalid substitutions will result in a "
            + "an error and the script will abort."
        )
        formatter.write("\n")
        formatter.write_text(
            "If you want the actual text of the template substition to appear "
            + "in the rendered name, use double braces, e.g. '{{' or '}}', thus "
            + "using '{created.year}/{{name}}' for --directory "
            + "would result in output of 2020/{name}/photoname.jpg"
        )
        formatter.write("\n")
        formatter.write_text(
            "You may specify an optional default value to use if the substitution does not contain a value "
            + "(e.g. the value is null) "
            + "by specifying the default value after a ',' in the template string: "
            + "for example, if template is '{created.year}/{place.address,'NO_ADDRESS'}' "
            + "but there was no address associated with the photo, the resulting output would be: "
            + "'2020/NO_ADDRESS/photoname.jpg'. "
            + "If specified, the default value may not contain a brace symbol ('{' or '}')."
        )
        formatter.write("\n")
        formatter.write_text(
            "If you do not specify a default value and the template substitution "
            + "has no value, '_' (underscore) will be used as the default value. For example, in the "
            + "above example, this would result in '2020/_/photoname.jpg' if address was null"
        )
        formatter.write_text(
            "I plan to eventually extend the templating system "
            + "to the exported filename so you can specify the filename using a template."
        )

        formatter.write("\n")
        templ_tuples = [("Substitution", "Description")]
        templ_tuples.extend((k, v) for k, v in TEMPLATE_SUBSTITUTIONS.items())
        formatter.write_dl(templ_tuples)

        formatter.write("\n")
        formatter.write_text(
            "The following substitutions may result in multiple values. Thus "
            + "if specified for --directory these could result in multiple copies of a photo being "
            + "being exported, one to each directory.  For example: "
            + "--directory '{created.year}/{album}' could result in the same photo being exported "
            + "to each of the following directories if the photos were created in 2019 "
            + "and were in albums 'Vacation' and 'Family': "
            + "2019/Vacation, 2019/Family"
        )
        formatter.write("\n")
        templ_tuples = [("Substitution", "Description")]
        templ_tuples.extend(
            (k, v) for k, v in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items()
        )

        formatter.write_dl(templ_tuples)
        help_text += formatter.getvalue()
        return help_text


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])
DB_OPTION = click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help=(
        "Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument. "
        "If neither --db or PHOTOS_LIBRARY provided, will attempt to find the library "
        "to use in the following order: 1. last opened library, 2. system library, 3. ~/Pictures/Photos Library.photoslibrary"
    ),
    type=click.Path(exists=True),
)

DB_ARGUMENT = click.argument("photos_library", nargs=-1, type=click.Path(exists=True))

JSON_OPTION = click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)


def query_options(f):
    o = click.option
    options = [
        o(
            "--keyword",
            metavar="KEYWORD",
            default=None,
            multiple=True,
            help="Search for keyword KEYWORD. "
            'If more than one keyword, treated as "OR", e.g. find photos match any keyword',
        ),
        o(
            "--person",
            metavar="PERSON",
            default=None,
            multiple=True,
            help="Search for person PERSON. "
            'If more than one person, treated as "OR", e.g. find photos match any person',
        ),
        o(
            "--album",
            metavar="ALBUM",
            default=None,
            multiple=True,
            help="Search for album ALBUM. "
            'If more than one album, treated as "OR", e.g. find photos match any album',
        ),
        o(
            "--uuid",
            metavar="UUID",
            default=None,
            multiple=True,
            help="Search for UUID(s).",
        ),
        o(
            "--title",
            metavar="TITLE",
            default=None,
            multiple=True,
            help="Search for TITLE in title of photo.",
        ),
        o("--no-title", is_flag=True, help="Search for photos with no title."),
        o(
            "--description",
            metavar="DESC",
            default=None,
            multiple=True,
            help="Search for DESC in description of photo.",
        ),
        o(
            "--no-description",
            is_flag=True,
            help="Search for photos with no description.",
        ),
        o(
            "--place",
            metavar="PLACE",
            default=None,
            multiple=True,
            help="Search for PLACE in photo's reverse geolocation info",
        ),
        o(
            "--no-place",
            is_flag=True,
            help="Search for photos with no associated place name info (no reverse geolocation info)",
        ),
        o(
            "--uti",
            metavar="UTI",
            default=None,
            multiple=False,
            help="Search for photos whose uniform type identifier (UTI) matches UTI",
        ),
        o(
            "-i",
            "--ignore-case",
            is_flag=True,
            help="Case insensitive search for title, description, or place. Does not apply to keyword, person, or album.",
        ),
        o("--edited", is_flag=True, help="Search for photos that have been edited."),
        o(
            "--external-edit",
            is_flag=True,
            help="Search for photos edited in external editor.",
        ),
        o("--favorite", is_flag=True, help="Search for photos marked favorite."),
        o(
            "--not-favorite",
            is_flag=True,
            help="Search for photos not marked favorite.",
        ),
        o("--hidden", is_flag=True, help="Search for photos marked hidden."),
        o("--not-hidden", is_flag=True, help="Search for photos not marked hidden."),
        o(
            "--shared",
            is_flag=True,
            help="Search for photos in shared iCloud album (Photos 5 only).",
        ),
        o(
            "--not-shared",
            is_flag=True,
            help="Search for photos not in shared iCloud album (Photos 5 only).",
        ),
        o(
            "--burst",
            is_flag=True,
            help="Search for photos that were taken in a burst.",
        ),
        o(
            "--not-burst",
            is_flag=True,
            help="Search for photos that are not part of a burst.",
        ),
        o("--live", is_flag=True, help="Search for Apple live photos"),
        o(
            "--not-live",
            is_flag=True,
            help="Search for photos that are not Apple live photos.",
        ),
        o("--portrait", is_flag=True, help="Search for Apple portrait mode photos."),
        o(
            "--not-portrait",
            is_flag=True,
            help="Search for photos that are not Apple portrait mode photos.",
        ),
        o("--screenshot", is_flag=True, help="Search for screenshot photos."),
        o(
            "--not-screenshot",
            is_flag=True,
            help="Search for photos that are not screenshot photos.",
        ),
        o("--slow-mo", is_flag=True, help="Search for slow motion videos."),
        o(
            "--not-slow-mo",
            is_flag=True,
            help="Search for photos that are not slow motion videos.",
        ),
        o("--time-lapse", is_flag=True, help="Search for time lapse videos."),
        o(
            "--not-time-lapse",
            is_flag=True,
            help="Search for photos that are not time lapse videos.",
        ),
        o("--hdr", is_flag=True, help="Search for high dynamic range (HDR) photos."),
        o("--not-hdr", is_flag=True, help="Search for photos that are not HDR photos."),
        o(
            "--selfie",
            is_flag=True,
            help="Search for selfies (photos taken with front-facing cameras).",
        ),
        o("--not-selfie", is_flag=True, help="Search for photos that are not selfies."),
        o("--panorama", is_flag=True, help="Search for panorama photos."),
        o(
            "--not-panorama",
            is_flag=True,
            help="Search for photos that are not panoramas.",
        ),
        o(
            "--only-movies",
            is_flag=True,
            help="Search only for movies (default searches both images and movies).",
        ),
        o(
            "--only-photos",
            is_flag=True,
            help="Search only for photos/images (default searches both images and movies).",
        ),
        o(
            "--from-date",
            help="Search by start item date, e.g. 2000-01-12T12:00:00 or 2000-12-31 (ISO 8601 w/o TZ).",
            type=click.DateTime(),
        ),
        o(
            "--to-date",
            help="Search by end item date, e.g. 2000-01-12T12:00:00 or 2000-12-31 (ISO 8601 w/o TZ).",
            type=click.DateTime(),
        ),
    ]
    for o in options[::-1]:
        f = o(f)
    return f


@click.group(context_settings=CTX_SETTINGS)
@DB_OPTION
@JSON_OPTION
@click.option("--debug", required=False, is_flag=True, default=False, hidden=True)
@click.version_option(__version__, "--version", "-v")
@click.pass_context
def cli(ctx, db, json_, debug):
    ctx.obj = CLI_Obj(db=db, json=json_, debug=debug)


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def keywords(ctx, cli_obj, db, json_, photos_library):
    """ Print out keywords found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["keywords"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    keywords = {"keywords": photosdb.keywords_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(keywords))
    else:
        click.echo(yaml.dump(keywords, sort_keys=False))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def albums(ctx, cli_obj, db, json_, photos_library):
    """ Print out albums found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["albums"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
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
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def persons(ctx, cli_obj, db, json_, photos_library):
    """ Print out persons (faces) found in the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["persons"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    persons = {"persons": photosdb.persons_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(persons))
    else:
        click.echo(yaml.dump(persons, sort_keys=False))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def info(ctx, cli_obj, db, json_, photos_library):
    """ Print out descriptive info of the Photos library database. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["info"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
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

    info["persons_count"] = len(persons)
    info["persons"] = persons

    if cli_obj.json or json_:
        click.echo(json.dumps(info))
    else:
        click.echo(yaml.dump(info, sort_keys=False))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def places(ctx, cli_obj, db, json_, photos_library):
    """ Print out places found in the Photos library. """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["places"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    place_names = {}
    for photo in photosdb.photos(movies=True):
        if photo.place:
            try:
                place_names[photo.place.name] += 1
            except:
                place_names[photo.place.name] = 1
        else:
            try:
                place_names[_UNKNOWN_PLACE] += 1
            except:
                place_names[_UNKNOWN_PLACE] = 1

    # sort by place count
    places = {
        "places": {
            name: place_names[name]
            for name in sorted(
                place_names.keys(), key=lambda key: place_names[key], reverse=True
            )
        }
    }

    # below needed for to make CliRunner work for testing
    cli_json = cli_obj.json if cli_obj is not None else None
    if json_ or cli_json:
        click.echo(json.dumps(places))
    else:
        click.echo(yaml.dump(places, sort_keys=False))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def dump(ctx, cli_obj, db, json_, photos_library):
    """ Print list of all photos & associated info from the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["dump"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    pdb = osxphotos.PhotosDB(dbfile=db)
    photos = pdb.photos(movies=True)
    print_photo_info(photos, json_ or cli_obj.json)


@cli.command(name="list")
@JSON_OPTION
@click.pass_obj
@click.pass_context
def list_libraries(ctx, cli_obj, json_):
    """ Print list of Photos libraries found on the system. """

    # implemented in _list_libraries so it can be called by other CLI functions
    # without errors due to passing ctx and cli_obj
    _list_libraries(json_=json_ or cli_obj.json, error=False)


def _list_libraries(json_=False, error=True):
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
                click.echo(f"(*)\t{lib}", err=error)
                sys_lib_flag = True
            elif lib == last_lib:
                click.echo(f"(#)\t{lib}", err=error)
                last_lib_flag = True
            else:
                click.echo(f"\t{lib}", err=error)

        if sys_lib_flag or last_lib_flag:
            click.echo("\n", err=error)
        if sys_lib_flag:
            click.echo("(*)\tSystem Photos Library", err=error)
        if last_lib_flag:
            click.echo("(#)\tLast opened Photos Library", err=error)


@cli.command()
@DB_OPTION
@JSON_OPTION
@query_options
@click.option("--missing", is_flag=True, help="Search for photos missing from disk.")
@click.option(
    "--not-missing",
    is_flag=True,
    help="Search for photos present on disk (e.g. not missing).",
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
@DB_ARGUMENT
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
    from_date,
    to_date,
    portrait,
    not_portrait,
    screenshot,
    not_screenshot,
    slow_mo,
    not_slow_mo,
    time_lapse,
    not_time_lapse,
    hdr,
    not_hdr,
    selfie,
    not_selfie,
    panorama,
    not_panorama,
    place,
    no_place,
):
    """ Query the Photos database using 1 or more search options; 
        if more than one option is provided, they are treated as "AND" 
        (e.g. search for photos matching all options).
    """

    # if no query terms, show help and return
    # sanity check input args
    nonexclusive = [
        keyword,
        person,
        album,
        uuid,
        edited,
        external_edit,
        uti,
        from_date,
        to_date,
    ]
    exclusive = [
        (favorite, not_favorite),
        (hidden, not_hidden),
        (missing, not_missing),
        (any(title), no_title),
        (any(description), no_description),
        (only_photos, only_movies),
        (burst, not_burst),
        (live, not_live),
        (cloudasset, not_cloudasset),
        (incloud, not_incloud),
        (portrait, not_portrait),
        (screenshot, not_screenshot),
        (slow_mo, not_slow_mo),
        (time_lapse, not_time_lapse),
        (hdr, not_hdr),
        (selfie, not_selfie),
        (panorama, not_panorama),
        (any(place), no_place),
    ]
    # print help if no non-exclusive term or a double exclusive term is given
    if not any(nonexclusive + [b ^ n for b, n in exclusive]):
        click.echo(cli.commands["query"].get_help(ctx), err=True)
        return

    # actually have something to query
    isphoto = ismovie = True  # default searches for everything
    if only_movies:
        isphoto = False
    if only_photos:
        ismovie = False

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["query"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photos = _query(
        db=db,
        keyword=keyword,
        person=person,
        album=album,
        uuid=uuid,
        title=title,
        no_title=no_title,
        description=description,
        no_description=no_description,
        ignore_case=ignore_case,
        edited=edited,
        external_edit=external_edit,
        favorite=favorite,
        not_favorite=not_favorite,
        hidden=hidden,
        not_hidden=not_hidden,
        missing=missing,
        not_missing=not_missing,
        shared=shared,
        not_shared=not_shared,
        isphoto=isphoto,
        ismovie=ismovie,
        uti=uti,
        burst=burst,
        not_burst=not_burst,
        live=live,
        not_live=not_live,
        cloudasset=cloudasset,
        not_cloudasset=not_cloudasset,
        incloud=incloud,
        not_incloud=not_incloud,
        from_date=from_date,
        to_date=to_date,
        portrait=portrait,
        not_portrait=not_portrait,
        screenshot=screenshot,
        not_screenshot=not_screenshot,
        slow_mo=slow_mo,
        not_slow_mo=not_slow_mo,
        time_lapse=time_lapse,
        not_time_lapse=not_time_lapse,
        hdr=hdr,
        not_hdr=not_hdr,
        selfie=selfie,
        not_selfie=not_selfie,
        panorama=panorama,
        not_panorama=not_panorama,
        place=place,
        no_place=no_place,
    )

    # below needed for to make CliRunner work for testing
    cli_json = cli_obj.json if cli_obj is not None else None
    print_photo_info(photos, cli_json or json_)


@cli.command(cls=ExportCommand)
@DB_OPTION
@query_options
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
    help="If a photo is a burst photo export all associated burst images in the library.  "
    "Not currently compatible with --download-misssing; see note on --download-missing.",
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
    default=None,
    multiple=True,
    metavar="FORMAT",
    type=click.Choice(["xmp", "json"], case_sensitive=False),
    help="Create sidecar for each photo exported; valid FORMAT values: xmp, json; "
    f"--sidecar json: create JSON sidecar useable by exiftool ({_EXIF_TOOL_URL}) "
    "The sidecar file can be used to apply metadata to the file with exiftool, for example: "
    '"exiftool -j=photoname.json photoname.jpg" '
    "The sidecar file is named in format photoname.json  "
    "--sidecar xmp: create XMP sidecar used by Adobe Lightroom, etc."
    "The sidecar file is named in format photoname.xmp",
)
@click.option(
    "--download-missing",
    is_flag=True,
    help="Attempt to download missing photos from iCloud. The current implementation uses Applescript "
    "to interact with Photos to export the photo which will force Photos to download from iCloud if "
    "the photo does not exist on disk.  This will be slow and will require internet connection. "
    "This obviously only works if the Photos library is synched to iCloud.  "
    "Note: --download-missing is not currently compatabile with --export-bursts; "
    "only the primary photo will be exported--associated burst images will be skipped.",
)
@click.option(
    "--exiftool",
    is_flag=True,
    help="Use exiftool to write metadata directly to exported photos. "
    "To use this option, exiftool must be installed and in the path.  "
    "exiftool may be installed from https://exiftool.org/",
)
@click.option(
    "--directory",
    metavar="DIRECTORY",
    default=None,
    help="Optional template for specifying name of output directory in the form '{name,DEFAULT}'. "
    "See below for additional details on templating system.",
)
@click.option(
    "--no-extended-attributes",
    is_flag=True,
    default=False,
    help="Don't copy extended attributes when exporting.  You only need this if exporting "
    "to a filesystem that doesn't support Mac OS extended attributes.  Only use this if you get "
    "an error while exporting.",
)
@DB_ARGUMENT
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
    from_date,
    to_date,
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
    exiftool,
    portrait,
    not_portrait,
    screenshot,
    not_screenshot,
    slow_mo,
    not_slow_mo,
    time_lapse,
    not_time_lapse,
    hdr,
    not_hdr,
    selfie,
    not_selfie,
    panorama,
    not_panorama,
    directory,
    place,
    no_place,
    no_extended_attributes,
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
    exclusive = [
        (favorite, not_favorite),
        (hidden, not_hidden),
        (any(title), no_title),
        (any(description), no_description),
        (only_photos, only_movies),
        (burst, not_burst),
        (live, not_live),
        (portrait, not_portrait),
        (screenshot, not_screenshot),
        (slow_mo, not_slow_mo),
        (time_lapse, not_time_lapse),
        (hdr, not_hdr),
        (selfie, not_selfie),
        (panorama, not_panorama),
        (export_by_date, directory),
        (any(place), no_place),
    ]
    if any([all(bb) for bb in exclusive]):
        click.echo(cli.commands["export"].get_help(ctx), err=True)
        return

    # verify exiftool installed an in path
    if exiftool:
        try:
            _ = get_exiftool_path()
        except FileNotFoundError:
            click.echo(
                "Could not find exiftool. Please download and install"
                " from https://exiftool.org/",
                err=True,
            )
            ctx.exit(2)

    isphoto = ismovie = True  # default searches for everything
    if only_movies:
        isphoto = False
    if only_photos:
        ismovie = False

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["export"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photos = _query(
        db=db,
        keyword=keyword,
        person=person,
        album=album,
        uuid=uuid,
        title=title,
        no_title=no_title,
        description=description,
        no_description=no_description,
        ignore_case=ignore_case,
        edited=edited,
        external_edit=external_edit,
        favorite=favorite,
        not_favorite=not_favorite,
        hidden=hidden,
        not_hidden=not_hidden,
        missing=None,  # missing -- won't export these but will warn user
        not_missing=None,
        shared=shared,
        not_shared=not_shared,
        isphoto=isphoto,
        ismovie=ismovie,
        uti=uti,
        burst=burst,
        not_burst=not_burst,
        live=live,
        not_live=not_live,
        cloudasset=False,
        not_cloudasset=False,
        incloud=False,
        not_incloud=False,
        from_date=from_date,
        to_date=to_date,
        portrait=portrait,
        not_portrait=not_portrait,
        screenshot=screenshot,
        not_screenshot=not_screenshot,
        slow_mo=slow_mo,
        not_slow_mo=not_slow_mo,
        time_lapse=time_lapse,
        not_time_lapse=not_time_lapse,
        hdr=hdr,
        not_hdr=not_hdr,
        selfie=selfie,
        not_selfie=not_selfie,
        panorama=panorama,
        not_panorama=not_panorama,
        place=place,
        no_place=no_place,
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
                        exiftool,
                        directory,
                        no_extended_attributes,
                    )
        else:
            for p in photos:
                export_paths = export_photo(
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
                    exiftool,
                    directory,
                    no_extended_attributes,
                )
                if export_paths:
                    click.echo(f"Exported {p.filename} to {export_paths}")
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
    elif topic in cli.commands:
        ctx.info_name = topic
        click.echo_via_pager(cli.commands[topic].get_help(ctx))
    else:
        click.echo(f"Invalid command: {topic}", err=True)
        click.echo(ctx.parent.get_help())


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
                "date_modified",
                "portrait",
                "screenshot",
                "slow_mo",
                "time_lapse",
                "hdr",
                "selfie",
                "panorama",
            ]
        )
        for p in photos:
            date_modified_iso = p.date_modified.isoformat() if p.date_modified else None
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
                    date_modified_iso,
                    p.portrait,
                    p.screenshot,
                    p.slow_mo,
                    p.time_lapse,
                    p.hdr,
                    p.selfie,
                    p.panorama,
                ]
            )
        for row in dump:
            csv_writer.writerow(row)


def _query(
    db=None,
    keyword=None,
    person=None,
    album=None,
    uuid=None,
    title=None,
    no_title=None,
    description=None,
    no_description=None,
    ignore_case=None,
    edited=None,
    external_edit=None,
    favorite=None,
    not_favorite=None,
    hidden=None,
    not_hidden=None,
    missing=None,
    not_missing=None,
    shared=None,
    not_shared=None,
    isphoto=None,
    ismovie=None,
    uti=None,
    burst=None,
    not_burst=None,
    live=None,
    not_live=None,
    cloudasset=None,
    not_cloudasset=None,
    incloud=None,
    not_incloud=None,
    from_date=None,
    to_date=None,
    portrait=None,
    not_portrait=None,
    screenshot=None,
    not_screenshot=None,
    slow_mo=None,
    not_slow_mo=None,
    time_lapse=None,
    not_time_lapse=None,
    hdr=None,
    not_hdr=None,
    selfie=None,
    not_selfie=None,
    panorama=None,
    not_panorama=None,
    place=None,
    no_place=None,
):
    """ run a query against PhotosDB to extract the photos based on user supply criteria """
    """ used by query and export commands """
    """ arguments must be passed in same order as query and export """
    """ if either is modified, need to ensure all three functions are updated """

    photosdb = osxphotos.PhotosDB(dbfile=db)
    photos = photosdb.photos(
        keywords=keyword,
        persons=person,
        albums=album,
        uuid=uuid,
        images=isphoto,
        movies=ismovie,
        from_date=from_date,
        to_date=to_date,
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
        # if more than one, find photos with all description values in description
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

    if place:
        # search place.names for text matching place
        # if more than one place, find photos with all place values in description
        if ignore_case:
            # case-insensitive
            for place_name in place:
                place_name = place_name.lower()
                photos = [
                    p
                    for p in photos
                    if p.place
                    and any(
                        pname
                        for pname in p.place.names
                        if any(
                            pvalue for pvalue in pname if place_name in pvalue.lower()
                        )
                    )
                ]
        else:
            for place_name in place:
                photos = [
                    p
                    for p in photos
                    if p.place
                    and any(
                        pname
                        for pname in p.place.names
                        if any(pvalue for pvalue in pname if place_name in pvalue)
                    )
                ]
    elif no_place:
        photos = [p for p in photos if not p.place]

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

    if portrait:
        photos = [p for p in photos if p.portrait]
    elif not_portrait:
        photos = [p for p in photos if not p.portrait]

    if screenshot:
        photos = [p for p in photos if p.screenshot]
    elif not_screenshot:
        photos = [p for p in photos if not p.screenshot]

    if slow_mo:
        photos = [p for p in photos if p.slow_mo]
    elif not_slow_mo:
        photos = [p for p in photos if not p.slow_mo]

    if time_lapse:
        photos = [p for p in photos if p.time_lapse]
    elif not_time_lapse:
        photos = [p for p in photos if not p.time_lapse]

    if hdr:
        photos = [p for p in photos if p.hdr]
    elif not_hdr:
        photos = [p for p in photos if not p.hdr]

    if selfie:
        photos = [p for p in photos if p.selfie]
    elif not_selfie:
        photos = [p for p in photos if not p.selfie]

    if panorama:
        photos = [p for p in photos if p.panorama]
    elif not_panorama:
        photos = [p for p in photos if not p.panorama]

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
    exiftool,
    directory,
    no_extended_attributes,
):
    """ Helper function for export that does the actual export
        photo: PhotoInfo object
        dest: destination path as string
        verbose: boolean; print verbose output
        export_by_date: boolean; create export folder in form dest/YYYY/MM/DD
        sidecar: list zero, 1 or 2 of ["json","xmp"] of sidecar variety to export
        overwrite: boolean; overwrite dest file if it already exists
        original_name: boolean; use original filename instead of current filename
        export_live: boolean; also export live video component if photo is a live photo
                     live video will have same name as photo but with .mov extension
        download_missing: attempt download of missing iCloud photos
        exiftool: use exiftool to write EXIF metadata directly to exported photo
        directory: template used to determine output directory
        no_extended_attributes: boolean; if True, exports photo without preserving extended attributes
        returns list of path(s) of exported photo or None if photo was missing 
    """

    # Can export to multiple paths
    # Start with single path [dest] but direcotry and export_by_date will modify dest_paths
    dest_paths = [dest]

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
        dest_path = create_path_by_date(dest, date_created)
        dest_paths = [dest_path]
    elif directory:
        # got a directory template, render it and check results are valid
        dirnames, unmatched = render_filepath_template(directory, photo)
        if unmatched:
            raise click.BadOptionUsage(
                "directory",
                f"Invalid substitution in template '{directory}': {unmatched}",
            )
        dest_paths = []
        for dirname in dirnames:
            dirname = sanitize_filepath(dirname, platform="auto")
            if not is_valid_filepath(dirname, platform="auto"):
                raise ValueError(f"Invalid file path: {dirname}")
            dest_path = os.path.join(dest, dirname)
            if not os.path.isdir(dest_path):
                os.makedirs(dest_path)
            dest_paths.append(dest_path)

    sidecar = [s.lower() for s in sidecar]
    sidecar_json = sidecar_xmp = False
    if "json" in sidecar:
        sidecar_json = True
    if "xmp" in sidecar:
        sidecar_xmp = True

    # if download_missing and the photo is missing or path doesn't exist,
    # try to download with Photos
    use_photos_export = download_missing and (
        photo.ismissing or not os.path.exists(photo.path)
    )

    # export the photo to each path in dest_paths
    photo_paths = []
    for dest_path in dest_paths:
        photo_path = photo.export(
            dest_path,
            filename,
            sidecar_json=sidecar_json,
            sidecar_xmp=sidecar_xmp,
            live_photo=export_live,
            overwrite=overwrite,
            use_photos_export=use_photos_export,
            exiftool=exiftool,
            no_xattr=no_extended_attributes,
        )[0]
        photo_paths.append(photo_path)

        # if export-edited, also export the edited version
        # verify the photo has adjustments and valid path to avoid raising an exception
        if export_edited and photo.hasadjustments:
            # if download_missing and the photo is missing or path doesn't exist,
            # try to download with Photos
            use_photos_export = download_missing and photo.path_edited is None
            if not download_missing and photo.path_edited is None:
                click.echo(f"Skipping missing edited photo for {filename}")
            else:
                edited_name = pathlib.Path(filename)
                # check for correct edited suffix
                if photo.path_edited is not None:
                    edited_suffix = pathlib.Path(photo.path_edited).suffix
                else:
                    # use filename suffix which might be wrong,
                    # will be corrected by use_photos_export
                    edited_suffix = pathlib.Path(photo.filename).suffix
                edited_name = f"{edited_name.stem}_edited{edited_suffix}"
                if verbose:
                    click.echo(
                        f"Exporting edited version of {filename} as {edited_name}"
                    )
                photo.export(
                    dest_path,
                    edited_name,
                    sidecar_json=sidecar_json,
                    sidecar_xmp=sidecar_xmp,
                    overwrite=overwrite,
                    edited=True,
                    use_photos_export=use_photos_export,
                    exiftool=exiftool,
                    no_xattr=no_extended_attributes,
                )

    return photo_paths


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
