""" command line interface for osxphotos """
import csv
import datetime
import json
import os
import os.path
import pathlib
import pprint
import sys
import time
import unicodedata

import click
import yaml

import osxphotos

from ._constants import (
    _EXIF_TOOL_URL,
    _PHOTOS_4_VERSION,
    _UNKNOWN_PLACE,
    UNICODE_FORMAT,
)
from ._version import __version__
from .datetime_formatter import DateTimeFormatter
from .exiftool import get_exiftool_path
from .export_db import ExportDB, ExportDBInMemory
from .fileutil import FileUtil, FileUtilNoOp
from .path_utils import is_valid_filepath, sanitize_filename, sanitize_filepath
from .photoinfo import ExportResults
from .phototemplate import TEMPLATE_SUBSTITUTIONS, TEMPLATE_SUBSTITUTIONS_MULTI_VALUED

# global variable to control verbose output
# set via --verbose/-V
VERBOSE = False

# name of export DB
OSXPHOTOS_EXPORT_DB = ".osxphotos_export.db"


def verbose(*args, **kwargs):
    """ print output if verbose flag set """
    if VERBOSE:
        click.echo(*args, **kwargs)


def normalize_unicode(value):
    """ normalize unicode data """
    if value is not None:
        if isinstance(value, tuple):
            return tuple(unicodedata.normalize(UNICODE_FORMAT, v) for v in value)
        elif isinstance(value, str):
            return unicodedata.normalize(UNICODE_FORMAT, value)
        else:
            return value
    else:
        return None


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


class DateTimeISO8601(click.ParamType):

    name = "DATETIME"

    def convert(self, value, param, ctx):
        try:
            return datetime.datetime.fromisoformat(value)
        except:
            self.fail(
                f"Invalid value for --{param.name}: invalid datetime format {value}. "
                "Valid format: YYYY-MM-DD[*HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]]"
            )


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

        # passed to click.HelpFormatter.write_dl for formatting

        formatter.write("\n\n")
        formatter.write_text("** Export **")
        formatter.write_text(
            "When exporting photos, osxphotos creates a database in the top-level "
            + f"export folder called '{OSXPHOTOS_EXPORT_DB}'.  This database preserves state information "
            + "used for determining which files need to be updated when run with --update.  It is recommended "
            + "that if you later move the export folder tree you also move the database file."
        )
        formatter.write("\n")
        formatter.write_text(
            "The --update option will only copy new or updated files from the library "
            + "to the export folder.  If a file is changed in the export folder (for example, you edited the "
            + "exported image), osxphotos will detect this as a difference and re-export the original image "
            + "from the library thus overwriting the changes.  If using --update, the exported library "
            + "should be treated as a backup, not a working copy where you intend to make changes. "
        )
        formatter.write("\n")
        formatter.write_text(
            "Note: The number of files reported for export and the number actually exported "
            + "may differ due to live photos, associated raw images, and edited photos which are reported "
            + "in the total photos exported."
        )
        formatter.write("\n")
        formatter.write_text(
            "Implementation note: To determine which files need to be updated, "
            + f"osxphotos stores file signature information in the '{OSXPHOTOS_EXPORT_DB}' database. "
            + "The signature includes size, modification time, and filename.  In order to minimize "
            + "run time, --update does not do a full comparison (diff) of the files nor does it compare "
            + "hashes of the files.  In normal usage, this is sufficient for updating the library. "
            + "You can always run export without the --update option to re-export the entire library thus "
            + f"rebuilding the '{OSXPHOTOS_EXPORT_DB}' database."
        )

        formatter.write("\n\n")
        formatter.write_text("** Templating System **")
        formatter.write("\n")
        formatter.write_text(
            """
Several options, such as --directory, allow you to specify a template 
which will be rendered to substitute template fields with values from the photo. 
For example, '{created.month}' would be replaced with the month name of the photo creation date. 
e.g. 'November'. 
\n
The general format for a template is '{TEMPLATE_FIELD[,[DEFAULT]]}'. 
Some templates have optional modifiers in form 
'{[[DELIM]+]TEMPLATE_FIELD[(PATH_SEP)][?VALUE_IF_TRUE][,[DEFAULT]]}'
\n
The ',' and DEFAULT value are optional. 
If TEMPLATE_FIELD results in a null (empty) value, the default is '_'.  
You may specify an alternate default value by appending ',DEFAULT' after template_field. 
e.g. '{title,no_title}' would result in 'no_title' if the photo had no title. 
You may include other text in the template string outside the {} and use more than 
one template field, e.g. '{created.year} - {created.month}' (e.g. '2020 - November'). 
\n
Some template fields such as 'hdr' are boolean and resolve to True or False. 
These take the form: '{TEMPLATE_FIELD?VALUE_IF_TRUE,VALUE_IF_FALSE}', e.g. 
{hdr?is_hdr,not_hdr} which would result in 'is_hdr' if photo is an HDR 
image and 'not_hdr' otherwise.
\n
Some template fields such as 'folder_template' are "path-like" in that they join 
multiple elements into a single path-like string.  For example, if photo is in 
album Album1 in folder Folder1, '{folder_album}` results in 'Folder1/Album1'. 
This is so these template fields may be used as paths in --directory. 
If you intend to use such a field as a string, e.g. in the filename, you may specify 
a different path separator using the form: '{TEMPLATE_FIELD(PATH_SEP)}'. 
For example, using the example above, '{folder_album(-)}' would result in 
'Folder1-Album1' and '{folder_album()}' would result in 
'Folder1Album1'.
\n
Some templates may resolve to more than one value.  For example, a photo can have 
multiple keywords so '{keyword}' can result in multiple values.  If used in a filename 
or directory, these templates may result in more than one copy of the photo being exported. 
For example, if photo has keywords "foo" and "bar", --directory '{keyword}' will result in 
copies of the photo being exported to 'foo/image_name.jpeg' and 'bar/image_name.jpeg'.  
\n
Multi-value template fields such as '{keyword}' may be expanded 'in place' with an optional
delimiter using the template form '{DELIM+TEMPLATE_FIELD}'.  For example, a photo with 
keywords 'foo' and 'bar':
\n
'{keyword}' renders to 'foo' and 'bar'
\n
'{,+keyword}' renders to: 'foo,bar'
\n
'{; +keyword}' renders to: 'foo; bar'
\n
'{+keyword}' renders to 'foobar'
\n
Some template fields such as '{media_type}' use the 'DEFAULT' value to allow customization 
of the output. For example, '{media_type}' resolves to the special media type of the 
photo such as 'panorama' or 'selfie'.  You may use the 'DEFAULT' value to override 
these in form: '{media_type,video=vidéo;time_lapse=vidéo_accélérée}'. 
In this example, if photo is a time_lapse photo, 'media_type' would resolve to 
'vidéo_accélérée' instead of 'time_lapse' and video would resolve to 'vidéo' if photo
is an ordinary video. 
"""
        )
        formatter.write("\n")
        formatter.write_text(
            "With the --directory and --filename options you may specify a template for the "
            + "export directory or filename, respectively. "
            + "The directory will be appended to the export path specified "
            + "in the export DEST argument to export.  For example, if template is "
            + "'{created.year}/{created.month}', and export destination DEST is "
            + "'/Users/maria/Pictures/export', "
            + "the actual export directory for a photo would be '/Users/maria/Pictures/export/2020/March' "
            + "if the photo was created in March 2020. "
        )
        formatter.write("\n")
        formatter.write_text(
            "The templating system may also be used with the --keyword-template option "
            + "to set keywords on export (with --exiftool or --sidecar), "
            + "for example, to set a new keyword in format 'folder/subfolder/album' to "
            + 'preserve the folder/album structure, you can use --keyword-template "{folder_album}"'
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
            + "for example, if template is '{created.year}/{place.address,NO_ADDRESS}' "
            + "but there was no address associated with the photo, the resulting output would be: "
            + "'2020/NO_ADDRESS/photoname.jpg'. "
            + "If specified, the default value may not contain a brace symbol ('{' or '}')."
        )
        formatter.write("\n")
        formatter.write_text(
            "If you do not specify a default value and the template substitution "
            + "has no value, '_' (underscore) will be used as the default value. For example, in the "
            + "above example, this would result in '2020/_/photoname.jpg' if address was null."
        )
        formatter.write("\n")
        formatter.write_text(
            'You may specify a null default (e.g. "" or empty string) by omitting the value after '
            + 'the comma, e.g. {title,} which would render to "" if title had no value.'
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


def deleted_options(f):
    o = click.option
    options = [
        o(
            "--deleted",
            is_flag=True,
            help="Include photos from the 'Recently Deleted' folder.",
        ),
        o(
            "--deleted-only",
            is_flag=True,
            help="Include only photos from the 'Recently Deleted' folder.",
        ),
    ]
    for o in options[::-1]:
        f = o(f)
    return f


def query_options(f):
    o = click.option
    options = [
        o(
            "--keyword",
            metavar="KEYWORD",
            default=None,
            multiple=True,
            help="Search for photos with keyword KEYWORD. "
            'If more than one keyword, treated as "OR", e.g. find photos matching any keyword',
        ),
        o(
            "--person",
            metavar="PERSON",
            default=None,
            multiple=True,
            help="Search for photos with person PERSON. "
            'If more than one person, treated as "OR", e.g. find photos matching any person',
        ),
        o(
            "--album",
            metavar="ALBUM",
            default=None,
            multiple=True,
            help="Search for photos in album ALBUM. "
            'If more than one album, treated as "OR", e.g. find photos matching any album',
        ),
        o(
            "--folder",
            metavar="FOLDER",
            default=None,
            multiple=True,
            help="Search for photos in an album in folder FOLDER. "
            'If more than one folder, treated as "OR", e.g. find photos in any FOLDER.  '
            "Only searches top level folders (e.g. does not look at subfolders)",
        ),
        o(
            "--uuid",
            metavar="UUID",
            default=None,
            multiple=True,
            help="Search for photos with UUID(s).",
        ),
        o(
            "--uuid-from-file",
            metavar="FILE",
            default=None,
            multiple=False,
            help="Search for photos with UUID(s) loaded from FILE. "
            "Format is a single UUID per line.  Lines preceeded with # are ignored.",
            type=click.Path(exists=True),
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
            "--label",
            metavar="LABEL",
            multiple=True,
            help="Search for photos with image classification label LABEL (Photos 5 only). "
            'If more than one label, treated as "OR", e.g. find photos matching any label',
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
            help="Case insensitive search for title, description, place, keyword, person, or album.",
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
            "--has-raw",
            is_flag=True,
            help="Search for photos with both a jpeg and raw version",
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
            help="Search by start item date, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601).",
            type=DateTimeISO8601(),
        ),
        o(
            "--to-date",
            help="Search by end item date, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601).",
            type=DateTimeISO8601(),
        ),
        o("--has-comment", is_flag=True, help="Search for photos that have comments."),
        o("--no-comment", is_flag=True, help="Search for photos with no comments."),
        o("--has-likes", is_flag=True, help="Search for photos that have likes."),
        o("--no-likes", is_flag=True, help="Search for photos with no likes."),
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


@cli.command(hidden=True)
@DB_OPTION
@DB_ARGUMENT
@click.option(
    "--dump",
    metavar="ATTR",
    help="Name of PhotosDB attribute to print; "
    + "can also use albums, persons, keywords, photos to dump related attributes.",
    multiple=True,
)
@click.option(
    "--uuid",
    metavar="UUID",
    help="Use with '--dump photos' to dump only certain UUIDs",
    multiple=True,
)
@click.option("--verbose", "-V", "verbose_", is_flag=True, help="Print verbose output.")
@click.pass_obj
@click.pass_context
def debug_dump(ctx, cli_obj, db, photos_library, dump, uuid, verbose_):
    """ Print out debug info """

    global VERBOSE
    VERBOSE = bool(verbose_)

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["debug-dump"].get_help(ctx), err=True)
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
            if uuid:
                for uuid_ in uuid:
                    print(f"_dbphotos['{uuid_}']:")
                    try:
                        pprint.pprint(photosdb._dbphotos[uuid_])
                    except KeyError:
                        print(f"Did not find uuid {uuid_} in _dbphotos")
            else:
                print("_dbphotos:")
                pprint.pprint(photosdb._dbphotos)
        else:
            try:
                val = getattr(photosdb, attr)
                print(f"{attr}:")
                pprint.pprint(val)
            except:
                print(f"Did not find attribute {attr} in PhotosDB")


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def keywords(ctx, cli_obj, db, json_, photos_library):
    """ Print out keywords found in the Photos library. """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["keywords"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    keywords = {"keywords": photosdb.keywords_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(keywords, ensure_ascii=False))
    else:
        click.echo(yaml.dump(keywords, sort_keys=False, allow_unicode=True))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def albums(ctx, cli_obj, db, json_, photos_library):
    """ Print out albums found in the Photos library. """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["albums"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    albums = {"albums": photosdb.albums_as_dict}
    if photosdb.db_version > _PHOTOS_4_VERSION:
        albums["shared albums"] = photosdb.albums_shared_as_dict

    if json_ or cli_obj.json:
        click.echo(json.dumps(albums, ensure_ascii=False))
    else:
        click.echo(yaml.dump(albums, sort_keys=False, allow_unicode=True))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def persons(ctx, cli_obj, db, json_, photos_library):
    """ Print out persons (faces) found in the Photos library. """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["persons"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    persons = {"persons": photosdb.persons_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(persons, ensure_ascii=False))
    else:
        click.echo(yaml.dump(persons, sort_keys=False, allow_unicode=True))


@cli.command()
@DB_OPTION
@JSON_OPTION
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def labels(ctx, cli_obj, db, json_, photos_library):
    """ Print out image classification labels found in the Photos library. """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["labels"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    labels = {"labels": photosdb.labels_as_dict}
    if json_ or cli_obj.json:
        click.echo(json.dumps(labels, ensure_ascii=False))
    else:
        click.echo(yaml.dump(labels, sort_keys=False, allow_unicode=True))


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

    photosdb = osxphotos.PhotosDB(dbfile=db)
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

    if cli_obj.json or json_:
        click.echo(json.dumps(info, ensure_ascii=False))
    else:
        click.echo(yaml.dump(info, sort_keys=False, allow_unicode=True))


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
        click.echo(json.dumps(places, ensure_ascii=False))
    else:
        click.echo(yaml.dump(places, sort_keys=False, allow_unicode=True))


@cli.command()
@DB_OPTION
@JSON_OPTION
@deleted_options
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def dump(ctx, cli_obj, db, json_, deleted, deleted_only, photos_library):
    """ Print list of all photos & associated info from the Photos library. """

    db = get_photos_db(*photos_library, db, cli_obj.db)
    if db is None:
        click.echo(cli.commands["dump"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    # check exclusive options
    if deleted and deleted_only:
        click.echo("Incompatible dump options", err=True)
        click.echo(cli.commands["dump"].get_help(ctx), err=True)
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    if deleted or deleted_only:
        photos = photosdb.photos(movies=True, intrash=True)
    else:
        photos = []
    if not deleted_only:
        photos += photosdb.photos(movies=True)

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
        click.echo(json.dumps(libs, ensure_ascii=False))
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
@deleted_options
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
    folder,
    uuid,
    uuid_from_file,
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
    has_raw,
    place,
    no_place,
    label,
    deleted,
    deleted_only,
    has_comment,
    no_comment,
    has_likes,
    no_likes,
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
        folder,
        uuid,
        uuid_from_file,
        edited,
        external_edit,
        uti,
        has_raw,
        from_date,
        to_date,
        label,
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
        (deleted, deleted_only),
        (shared, not_shared),
        (has_comment, no_comment),
        (has_likes, no_likes),
    ]
    # print help if no non-exclusive term or a double exclusive term is given
    if any(all(bb) for bb in exclusive) or not any(
        nonexclusive + [b ^ n for b, n in exclusive]
    ):
        click.echo("Incompatible query options", err=True)
        click.echo(cli.commands["query"].get_help(ctx), err=True)
        return

    # actually have something to query
    isphoto = ismovie = True  # default searches for everything
    if only_movies:
        isphoto = False
    if only_photos:
        ismovie = False

    # load UUIDs if necessary and append to any uuids passed with --uuid
    if uuid_from_file:
        uuid_list = list(uuid)  # Click option is a tuple
        uuid_list.extend(load_uuid_from_file(uuid_from_file))
        uuid = tuple(uuid_list)

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
        folder=folder,
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
        has_raw=has_raw,
        place=place,
        no_place=no_place,
        label=label,
        deleted=deleted,
        deleted_only=deleted_only,
        has_comment=has_comment,
        no_comment=no_comment,
        has_likes=has_likes,
        no_likes=no_likes,
    )

    # below needed for to make CliRunner work for testing
    cli_json = cli_obj.json if cli_obj is not None else None
    print_photo_info(photos, cli_json or json_)


@cli.command(cls=ExportCommand)
@DB_OPTION
@click.option("--verbose", "-V", "verbose_", is_flag=True, help="Print verbose output.")
@query_options
@deleted_options
@click.option(
    "--update",
    is_flag=True,
    help="Only export new or updated files. See notes below on export and --update.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run (test) the export but don't actually export any files; most useful with --verbose",
)
@click.option(
    "--export-as-hardlink",
    is_flag=True,
    help="Hardlink files instead of copying them.  "
    "Cannot be used with --exiftool which creates copies of the files with embedded EXIF data.",
)
@click.option(
    "--touch-file",
    is_flag=True,
    help="Sets the file's modification time to match photo date.",
)
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
    "--skip-edited",
    is_flag=True,
    help="Do not export edited version of photo if an edited version exists.",
)
@click.option(
    "--skip-original-if-edited",
    is_flag=True,
    help="Do not export original if there is an edited version (exports only the edited version).",
)
@click.option(
    "--skip-bursts",
    is_flag=True,
    help="Do not export all associated burst images in the library if a photo is a burst photo.  ",
)
@click.option(
    "--skip-live",
    is_flag=True,
    help="Do not export the associated live video component of a live photo.",
)
@click.option(
    "--skip-raw",
    is_flag=True,
    help="Do not export associated raw images of a RAW+JPEG pair.  "
    "Note: this does not skip raw photos if the raw photo does not have an associated jpeg image "
    "(e.g. the raw file was imported to Photos without a jpeg preview).",
)
@click.option(
    "--person-keyword",
    is_flag=True,
    help="Use person in image as keyword/tag when exporting metadata.",
)
@click.option(
    "--album-keyword",
    is_flag=True,
    help="Use album name as keyword/tag when exporting metadata.",
)
@click.option(
    "--keyword-template",
    metavar="TEMPLATE",
    multiple=True,
    default=None,
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "keyword in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to add "
    "the full path to the folder and album photo is contained in as a keyword when exporting "
    'you could specify --keyword-template "{folder_album}" '
    'You may specify more than one template, for example --keyword-template "{folder_album}" '
    '--keyword-template "{created.year}" '
    "See Templating System below.",
)
@click.option(
    "--description-template",
    metavar="TEMPLATE",
    multiple=False,
    default=None,
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "description in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to append "
    "'exported with osxphotos on [today's date]' to the description, you could specify "
    '--description-template "{descr} exported with osxphotos on {today.date}" '
    "See Templating System below.",
)
@click.option(
    "--current-name",
    is_flag=True,
    help="Use photo's current filename instead of original filename for export.  "
    "Note: Starting with Photos 5, all photos are renamed upon import.  By default, "
    "photos are exported with the the original name they had before import.",
)
@click.option(
    "--convert-to-jpeg",
    is_flag=True,
    help="Convert all non-jpeg images (e.g. raw, HEIC, PNG, etc) "
    "to JPEG upon export.  Only works if your Mac has a GPU.",
)
@click.option(
    "--jpeg-quality",
    type=click.FloatRange(0.0, 1.0),
    default=1.0,
    help="Value in range 0.0 to 1.0 to use with --convert-to-jpeg. "
    "A value of 1.0 specifies best quality, "
    "a value of 0.0 specifies maximum compression. "
    "Defaults to 1.0.",
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
    "Note: --download-missing does not currently export all burst images; "
    "only the primary photo will be exported--associated burst images will be skipped.",
)
@click.option(
    "--exiftool",
    is_flag=True,
    help="Use exiftool to write metadata directly to exported photos. "
    "To use this option, exiftool must be installed and in the path.  "
    "exiftool may be installed from https://exiftool.org/.  "
    "Cannot be used with --export-as-hardlink.",
)
@click.option(
    "--ignore-date-modified",
    is_flag=True,
    help="If used with --exiftool or --sidecar, will ignore the photo "
    "modification date and set EXIF:ModifyDate to EXIF:DateTimeOriginal; "
    "this is consistent with how Photos handles the EXIF:ModifyDate tag.",
)
@click.option(
    "--directory",
    metavar="DIRECTORY",
    default=None,
    help="Optional template for specifying name of output directory in the form '{name,DEFAULT}'. "
    "See below for additional details on templating system.",
)
@click.option(
    "--filename",
    "filename_template",
    metavar="FILENAME",
    default=None,
    help="Optional template for specifying name of output file in the form '{name,DEFAULT}'. "
    "File extension will be added automatically--do not include an extension in the FILENAME template. "
    "See below for additional details on templating system.",
)
@click.option(
    "--edited-suffix",
    metavar="SUFFIX",
    default="_edited",
    help="Optional suffix for naming edited photos.  Default name for edited photos is in form "
    "'photoname_edited.ext'. For example, with '--edited-suffix _bearbeiten', the edited photo "
    "would be named 'photoname_bearbeiten.ext'.  The default suffix is '_edited'.",
)
@click.option(
    "--no-extended-attributes",
    is_flag=True,
    default=False,
    help="Don't copy extended attributes when exporting.  You only need this if exporting "
    "to a filesystem that doesn't support Mac OS extended attributes.  Only use this if you get "
    "an error while exporting.",
)
@click.option(
    "--use-photos-export",
    is_flag=True,
    default=False,
    hidden=True,
    help="Force the use of AppleScript to export even if not missing (see also --download-missing).",
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
    folder,
    uuid,
    uuid_from_file,
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
    verbose_,
    update,
    dry_run,
    export_as_hardlink,
    touch_file,
    overwrite,
    export_by_date,
    skip_edited,
    skip_original_if_edited,
    skip_bursts,
    skip_live,
    skip_raw,
    person_keyword,
    album_keyword,
    keyword_template,
    description_template,
    current_name,
    convert_to_jpeg,
    jpeg_quality,
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
    ignore_date_modified,
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
    has_raw,
    directory,
    filename_template,
    edited_suffix,
    place,
    no_place,
    has_comment,
    no_comment,
    has_likes,
    no_likes,
    no_extended_attributes,
    label,
    deleted,
    deleted_only,
    use_photos_export,
):
    """ Export photos from the Photos database.
        Export path DEST is required.
        Optionally, query the Photos database using 1 or more search options; 
        if more than one option is provided, they are treated as "AND" 
        (e.g. search for photos matching all options).
        If no query options are provided, all photos will be exported.
        By default, all versions of all photos will be exported including edited
        versions, live photo movies, burst photos, and associated raw images. 
        See --skip-edited, --skip-live, --skip-bursts, and --skip-raw options
        to modify this behavior. 
    """

    global VERBOSE
    VERBOSE = bool(verbose_)

    if not os.path.isdir(dest):
        sys.exit(f"DEST {dest} must be valid path")

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
        (export_as_hardlink, exiftool),
        (any(place), no_place),
        (deleted, deleted_only),
        (skip_edited, skip_original_if_edited),
        (export_as_hardlink, convert_to_jpeg),
        (shared, not_shared),
        (has_comment, no_comment),
        (has_likes, no_likes),
    ]
    if any(all(bb) for bb in exclusive):
        click.echo("Incompatible export options", err=True)
        click.echo(cli.commands["export"].get_help(ctx), err=True)
        return

    # initialize export flags
    # by default, will export all versions of photos unless skip flag is set
    (export_edited, export_bursts, export_live, export_raw) = [
        not x for x in [skip_edited, skip_bursts, skip_live, skip_raw]
    ]

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

    # load UUIDs if necessary and append to any uuids passed with --uuid
    if uuid_from_file:
        uuid_list = list(uuid)  # Click option is a tuple
        uuid_list.extend(load_uuid_from_file(uuid_from_file))
        uuid = tuple(uuid_list)

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(cli.commands["export"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    # open export database and assign copy/link/unlink functions
    export_db_path = os.path.join(dest, OSXPHOTOS_EXPORT_DB)

    # check that export isn't in the parent or child of a previously exported library
    other_db_files = find_files_in_branch(dest, OSXPHOTOS_EXPORT_DB)
    if other_db_files:
        click.echo(
            "WARNING: found other export database files in this destination directory branch.  "
            + "This likely means you are attempting to export files into a directory "
            + "that is either the parent or a child directory of a previous export. "
            + "Proceeding may cause your exported files to be overwritten.",
            err=True,
        )
        click.echo(
            f"You are exporting to {dest}, found {OSXPHOTOS_EXPORT_DB} files in:"
        )
        for other_db in other_db_files:
            click.echo(f"{other_db}")
        click.confirm("Do you want to continue?", abort=True)

    if dry_run:
        export_db = ExportDBInMemory(export_db_path)
        fileutil = FileUtilNoOp
    else:
        export_db = ExportDB(export_db_path)
        fileutil = FileUtil

    if verbose_:
        if export_db.was_created:
            verbose(f"Created export database {export_db_path}")
        else:
            verbose(f"Using export database {export_db_path}")
        upgraded = export_db.was_upgraded
        if upgraded:
            verbose(
                f"Upgraded export database {export_db_path} from version {upgraded[0]} to {upgraded[1]}"
            )

    photos = _query(
        db=db,
        keyword=keyword,
        person=person,
        album=album,
        folder=folder,
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
        has_raw=has_raw,
        place=place,
        no_place=no_place,
        label=label,
        deleted=deleted,
        deleted_only=deleted_only,
        has_comment=has_comment,
        no_comment=no_comment,
        has_likes=has_likes,
        no_likes=no_likes,
    )

    if photos:
        if export_bursts:
            # add the burst_photos to the export set
            photos_burst = [p for p in photos if p.burst]
            for burst in photos_burst:
                burst_set = [p for p in burst.burst_photos if not p.ismissing]
                photos.extend(burst_set)

        num_photos = len(photos)
        # TODO: photos or photo appears several times, pull into a separate function
        photo_str = "photos" if num_photos > 1 else "photo"
        click.echo(f"Exporting {num_photos} {photo_str} to {dest}...")
        start_time = time.perf_counter()
        # though the command line option is current_name, internally all processing
        # logic uses original_name which is the boolean inverse of current_name
        # because the original code used --original-name as an option
        original_name = not current_name

        results_exported = []
        results_new = []
        results_updated = []
        results_skipped = []
        results_exif_updated = []
        results_touched = []
        if verbose_:
            for p in photos:
                results = export_photo(
                    photo=p,
                    dest=dest,
                    verbose_=verbose_,
                    export_by_date=export_by_date,
                    sidecar=sidecar,
                    update=update,
                    export_as_hardlink=export_as_hardlink,
                    overwrite=overwrite,
                    export_edited=export_edited,
                    skip_original_if_edited=skip_original_if_edited,
                    original_name=original_name,
                    export_live=export_live,
                    download_missing=download_missing,
                    exiftool=exiftool,
                    directory=directory,
                    filename_template=filename_template,
                    no_extended_attributes=no_extended_attributes,
                    export_raw=export_raw,
                    album_keyword=album_keyword,
                    person_keyword=person_keyword,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    export_db=export_db,
                    fileutil=fileutil,
                    dry_run=dry_run,
                    touch_file=touch_file,
                    edited_suffix=edited_suffix,
                    use_photos_export=use_photos_export,
                    convert_to_jpeg=convert_to_jpeg,
                    jpeg_quality=jpeg_quality,
                    ignore_date_modified=ignore_date_modified,
                )
                results_exported.extend(results.exported)
                results_new.extend(results.new)
                results_updated.extend(results.updated)
                results_skipped.extend(results.skipped)
                results_exif_updated.extend(results.exif_updated)
                results_touched.extend(results.touched)

                # if convert_to_jpeg and p.isphoto and p.uti != "public.jpeg":
                #     for photo_file in set(
                #         results.exported + results.updated + results.exif_updated
                #     ):
                #         verbose(f"Converting {photo_file} to jpeg")

        else:
            # show progress bar
            with click.progressbar(photos) as bar:
                for p in bar:
                    results = export_photo(
                        photo=p,
                        dest=dest,
                        verbose_=verbose_,
                        export_by_date=export_by_date,
                        sidecar=sidecar,
                        update=update,
                        export_as_hardlink=export_as_hardlink,
                        overwrite=overwrite,
                        export_edited=export_edited,
                        skip_original_if_edited=skip_original_if_edited,
                        original_name=original_name,
                        export_live=export_live,
                        download_missing=download_missing,
                        exiftool=exiftool,
                        directory=directory,
                        filename_template=filename_template,
                        no_extended_attributes=no_extended_attributes,
                        export_raw=export_raw,
                        album_keyword=album_keyword,
                        person_keyword=person_keyword,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        export_db=export_db,
                        fileutil=fileutil,
                        dry_run=dry_run,
                        touch_file=touch_file,
                        edited_suffix=edited_suffix,
                        use_photos_export=use_photos_export,
                        convert_to_jpeg=convert_to_jpeg,
                        jpeg_quality=jpeg_quality,
                        ignore_date_modified=ignore_date_modified,
                    )
                    results_exported.extend(results.exported)
                    results_new.extend(results.new)
                    results_updated.extend(results.updated)
                    results_skipped.extend(results.skipped)
                    results_exif_updated.extend(results.exif_updated)
                    results_touched.extend(results.touched)

        stop_time = time.perf_counter()
        # print summary results
        if update:
            photo_str_new = "photos" if len(results_new) != 1 else "photo"
            photo_str_updated = "photos" if len(results_updated) != 1 else "photo"
            photo_str_skipped = "photos" if len(results_skipped) != 1 else "photo"
            photo_str_exif_updated = (
                "photos" if len(results_exif_updated) != 1 else "photo"
            )
            summary = (
                f"Exported: {len(results_new)} {photo_str_new}, "
                f"updated: {len(results_updated)} {photo_str_updated}, "
                f"skipped: {len(results_skipped)} {photo_str_skipped}, "
                f"updated EXIF data: {len(results_exif_updated)} {photo_str_exif_updated}"
            )
        else:
            photo_str = "photos" if len(results_exported) != 1 else "photo"
            summary = f"Exported: {len(results_exported)} {photo_str}"
        photo_str_touched = "photos" if len(results_touched) != 1 else "photo"
        if touch_file:
            summary += f", touched date: {len(results_touched)} {photo_str_touched}"
        click.echo(summary)
        click.echo(f"Elapsed time: {(stop_time-start_time):.3f} seconds")
    else:
        click.echo("Did not find any photos to export")

    export_db.close()


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
    dump = []
    if json:
        for p in photos:
            dump.append(p.json())
        click.echo(f"[{', '.join(dump)}]")
    else:
        # dump as CSV
        csv_writer = csv.writer(
            sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
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
                "has_raw",
                "uti_raw",
                "path_raw",
                "intrash",
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
                    p.has_raw,
                    p.uti_raw,
                    p.path_raw,
                    p.intrash,
                ]
            )
        for row in dump:
            csv_writer.writerow(row)


def _query(
    db=None,
    keyword=None,
    person=None,
    album=None,
    folder=None,
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
    has_raw=None,
    place=None,
    no_place=None,
    label=None,
    deleted=False,
    deleted_only=False,
    has_comment=False,
    no_comment=False,
    has_likes=False,
    no_likes=False,
):
    """ run a query against PhotosDB to extract the photos based on user supply criteria 
        used by query and export commands 
        arguments must be passed in same order as query and export 
        if either is modified, need to ensure all three functions are updated """

    photosdb = osxphotos.PhotosDB(dbfile=db, verbose=verbose)
    if deleted or deleted_only:
        photos = photosdb.photos(
            uuid=uuid,
            images=isphoto,
            movies=ismovie,
            from_date=from_date,
            to_date=to_date,
            intrash=True,
        )
    else:
        photos = []
    if not deleted_only:
        photos += photosdb.photos(
            uuid=uuid,
            images=isphoto,
            movies=ismovie,
            from_date=from_date,
            to_date=to_date,
        )

    person = normalize_unicode(person)
    keyword = normalize_unicode(keyword)
    album = normalize_unicode(album)
    folder = normalize_unicode(folder)
    title = normalize_unicode(title)
    description = normalize_unicode(description)
    place = normalize_unicode(place)
    label = normalize_unicode(label)

    if album:
        photos = get_photos_by_attribute(photos, "albums", album, ignore_case)

    if keyword:
        photos = get_photos_by_attribute(photos, "keywords", keyword, ignore_case)

    if person:
        photos = get_photos_by_attribute(photos, "persons", person, ignore_case)

    if label:
        photos = get_photos_by_attribute(photos, "labels", label, ignore_case)

    if folder:
        # search for photos in an album in folder
        # finds photos that have albums whose top level folder matches folder
        photo_list = []
        for f in folder:
            photo_list.extend(
                [
                    p
                    for p in photos
                    if p.album_info
                    and f in [a.folder_names[0] for a in p.album_info if a.folder_names]
                ]
            )
        photos = photo_list

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
        photos = [p for p in photos if uti in p.uti_original]

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

    if has_raw:
        photos = [p for p in photos if p.has_raw]

    if has_comment:
        photos = [p for p in photos if p.comments]
    elif no_comment:
        photos = [p for p in photos if not p.comments]

    if has_likes:
        photos = [p for p in photos if p.likes]
    elif no_likes:
        photos = [p for p in photos if not p.likes]

    return photos


def get_photos_by_attribute(photos, attribute, values, ignore_case):
    """Search for photos based on values being in PhotoInfo.attribute

    Args:
        photos: a list of PhotoInfo objects 
        attribute: str, name of PhotoInfo attribute to search (e.g. keywords, persons, etc)
        values: list of values to search in property
        ignore_case: ignore case when searching

    Returns:
        list of PhotoInfo objects matching search criteria
    """
    photos_search = []
    if ignore_case:
        # case-insensitive
        for x in values:
            x = x.lower()
            photos_search.extend(
                p
                for p in photos
                if x in [attr.lower() for attr in getattr(p, attribute)]
            )
    else:
        for x in values:
            photos_search.extend(p for p in photos if x in getattr(p, attribute))
    return photos_search


def export_photo(
    photo=None,
    dest=None,
    verbose_=None,
    export_by_date=None,
    sidecar=None,
    update=None,
    export_as_hardlink=None,
    overwrite=None,
    export_edited=None,
    skip_original_if_edited=None,
    original_name=None,
    export_live=None,
    download_missing=None,
    exiftool=None,
    directory=None,
    filename_template=None,
    no_extended_attributes=None,
    export_raw=None,
    album_keyword=None,
    person_keyword=None,
    keyword_template=None,
    description_template=None,
    export_db=None,
    fileutil=FileUtil,
    dry_run=None,
    touch_file=None,
    edited_suffix="_edited",
    use_photos_export=False,
    convert_to_jpeg=False,
    jpeg_quality=1.0,
    ignore_date_modified=False,
):
    """ Helper function for export that does the actual export

    Args:
        photo: PhotoInfo object
        dest: destination path as string
        verbose_: boolean; print verbose output
        export_by_date: boolean; create export folder in form dest/YYYY/MM/DD
        sidecar: list zero, 1 or 2 of ["json","xmp"] of sidecar variety to export
        export_as_hardlink: boolean; hardlink files instead of copying them
        overwrite: boolean; overwrite dest file if it already exists
        original_name: boolean; use original filename instead of current filename
        export_live: boolean; also export live video component if photo is a live photo
                     live video will have same name as photo but with .mov extension
        download_missing: attempt download of missing iCloud photos
        exiftool: use exiftool to write EXIF metadata directly to exported photo
        directory: template used to determine output directory
        filename_template: template use to determine output file
        no_extended_attributes: boolean; if True, exports photo without preserving extended attributes
        export_raw: boolean; if True exports raw image associate with the photo
        export_edited: boolean; if True exports edited version of photo if there is one
        skip_original_if_edited: boolean; if True does not export original if photo has been edited
        album_keyword: boolean; if True, exports album names as keywords in metadata
        person_keyword: boolean; if True, exports person names as keywords in metadata
        keyword_template: list of strings; if provided use rendered template strings as keywords
        description_template: string; optional template string that will be rendered for use as photo description
        export_db: export database instance compatible with ExportDB_ABC
        fileutil: file util class compatible with FileUtilABC
        dry_run: boolean; if True, doesn't actually export or update any files
        touch_file: boolean; sets file's modification time to match photo date
        use_photos_export: boolean; if True forces the use of AppleScript to export even if photo not missing
        convert_to_jpeg: boolean; if True, converts non-jpeg images to jpeg
        jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set

    Returns:
        list of path(s) of exported photo or None if photo was missing
    
    Raises:
        ValueError on invalid filename_template
    """
    global VERBOSE
    VERBOSE = bool(verbose_)

    # TODO: if --skip-original-if-edited, it's possible edited version is on disk but
    # original is missing, in which case we should download the edited version
    if not download_missing:
        if photo.ismissing:
            space = " " if not verbose_ else ""
            verbose(f"{space}Skipping missing photo {photo.original_filename}")
            return ExportResults([], [], [], [], [], [])
        elif not os.path.exists(photo.path):
            space = " " if not verbose_ else ""
            verbose(
                f"{space}WARNING: file {photo.path} is missing but ismissing=False, "
                f"skipping {photo.original_filename}"
            )
            return ExportResults([], [], [], [], [], [])
    elif photo.ismissing and not photo.iscloudasset and not photo.incloud:
        verbose(
            f"Skipping missing {photo.original_filename}: not iCloud asset or missing from cloud"
        )
        return ExportResults([], [], [], [], [], [])

    results_exported = []
    results_new = []
    results_updated = []
    results_skipped = []
    results_exif_updated = []
    results_touched = []

    export_original = not (skip_original_if_edited and photo.hasadjustments)
    # slow_mo photos will always have hasadjustments=True even if not edited
    if photo.hasadjustments and photo.path_edited is None:
        if photo.slow_mo:
            export_original = True
            export_edited = False
        elif not download_missing:
            # requested edited version but it's missing, download original
            export_original = True
            export_edited = False
            verbose(
                f"Edited file for {photo.original_filename} is missing, exporting original"
            )

    filenames = get_filenames_from_template(photo, filename_template, original_name)
    for filename in filenames:
        verbose(f"Exporting {photo.original_filename} ({photo.filename}) as {filename}")

        dest_paths = get_dirnames_from_template(
            photo, directory, export_by_date, dest, dry_run
        )

        sidecar = [s.lower() for s in sidecar]
        sidecar_json = sidecar_xmp = False
        if "json" in sidecar:
            sidecar_json = True
        if "xmp" in sidecar:
            sidecar_xmp = True

        # if download_missing and the photo is missing or path doesn't exist,
        # try to download with Photos
        use_photos_export = use_photos_export or (
            download_missing
            and (
                photo.ismissing
                or not os.path.exists(photo.path)
                or (export_edited and photo.path_edited is None)
            )
        )

        # export the photo to each path in dest_paths
        for dest_path in dest_paths:
            if not export_original:
                verbose(f"Skipping original version of {photo.original_filename}")
            else:
                export_results = photo.export2(
                    dest_path,
                    filename,
                    sidecar_json=sidecar_json,
                    sidecar_xmp=sidecar_xmp,
                    live_photo=export_live,
                    raw_photo=export_raw,
                    export_as_hardlink=export_as_hardlink,
                    overwrite=overwrite,
                    use_photos_export=use_photos_export,
                    exiftool=exiftool,
                    no_xattr=no_extended_attributes,
                    use_albums_as_keywords=album_keyword,
                    use_persons_as_keywords=person_keyword,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    update=update,
                    export_db=export_db,
                    fileutil=fileutil,
                    dry_run=dry_run,
                    touch_file=touch_file,
                    convert_to_jpeg=convert_to_jpeg,
                    jpeg_quality=jpeg_quality,
                    ignore_date_modified=ignore_date_modified,
                )

                results_exported.extend(export_results.exported)
                results_new.extend(export_results.new)
                results_updated.extend(export_results.updated)
                results_skipped.extend(export_results.skipped)
                results_exif_updated.extend(export_results.exif_updated)
                results_touched.extend(export_results.touched)

                if verbose_:
                    for exported in export_results.exported:
                        verbose(f"Exported {exported}")
                    for new in export_results.new:
                        verbose(f"Exported new file {new}")
                    for updated in export_results.updated:
                        verbose(f"Exported updated file {updated}")
                    for skipped in export_results.skipped:
                        verbose(f"Skipped up to date file {skipped}")
                    for touched in export_results.touched:
                        verbose(f"Touched date on file {touched}")

            # if export-edited, also export the edited version
            # verify the photo has adjustments and valid path to avoid raising an exception
            if export_edited and photo.hasadjustments:
                # if download_missing and the photo is missing or path doesn't exist,
                # try to download with Photos
                if not download_missing and photo.path_edited is None:
                    verbose(f"Skipping missing edited photo for {filename}")
                else:
                    edited_name = pathlib.Path(filename)
                    # check for correct edited suffix
                    if photo.path_edited is not None:
                        edited_ext = pathlib.Path(photo.path_edited).suffix
                    else:
                        # use filename suffix which might be wrong,
                        # will be corrected by use_photos_export
                        edited_ext = pathlib.Path(photo.filename).suffix
                    edited_name = f"{edited_name.stem}{edited_suffix}{edited_ext}"
                    verbose(f"Exporting edited version of {filename} as {edited_name}")
                    export_results_edited = photo.export2(
                        dest_path,
                        edited_name,
                        sidecar_json=sidecar_json,
                        sidecar_xmp=sidecar_xmp,
                        export_as_hardlink=export_as_hardlink,
                        overwrite=overwrite,
                        edited=True,
                        use_photos_export=use_photos_export,
                        exiftool=exiftool,
                        no_xattr=no_extended_attributes,
                        use_albums_as_keywords=album_keyword,
                        use_persons_as_keywords=person_keyword,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        update=update,
                        export_db=export_db,
                        fileutil=fileutil,
                        dry_run=dry_run,
                        touch_file=touch_file,
                        convert_to_jpeg=convert_to_jpeg,
                        jpeg_quality=jpeg_quality,
                        ignore_date_modified=ignore_date_modified,
                    )

                    results_exported.extend(export_results_edited.exported)
                    results_new.extend(export_results_edited.new)
                    results_updated.extend(export_results_edited.updated)
                    results_skipped.extend(export_results_edited.skipped)
                    results_exif_updated.extend(export_results_edited.exif_updated)
                    results_touched.extend(export_results_edited.touched)

                    if verbose_:
                        for exported in export_results_edited.exported:
                            verbose(f"Exported {exported}")
                        for new in export_results_edited.new:
                            verbose(f"Exported new file {new}")
                        for updated in export_results_edited.updated:
                            verbose(f"Exported updated file {updated}")
                        for skipped in export_results_edited.skipped:
                            verbose(f"Skipped up to date file {skipped}")
                        for touched in export_results_edited.touched:
                            verbose(f"Touched date on file {touched}")

    return ExportResults(
        results_exported,
        results_new,
        results_updated,
        results_skipped,
        results_exif_updated,
        results_touched,
    )


def get_filenames_from_template(photo, filename_template, original_name):
    """ get list of export filenames for a photo

    Args:
        photo: a PhotoInfo instance
        filename_template: a PhotoTemplate template string, may be None
        original_name: boolean; if True, use photo's original filename instead of current filename
    
    Returns:
        list of filenames
    
    Raises:
        click.BadOptionUsage if template is invalid
    """
    if filename_template:
        photo_ext = pathlib.Path(photo.original_filename).suffix
        filenames, unmatched = photo.render_template(
            filename_template, path_sep="_", filename=True
        )
        if not filenames or unmatched:
            raise click.BadOptionUsage(
                "filename_template",
                f"Invalid template '{filename_template}': results={filenames} unmatched={unmatched}",
            )
        filenames = [f"{file_}{photo_ext}" for file_ in filenames]
    else:
        filenames = [photo.original_filename] if original_name else [photo.filename]

    filenames = [sanitize_filename(filename) for filename in filenames]
    return filenames


def get_dirnames_from_template(photo, directory, export_by_date, dest, dry_run):
    """ get list of directories to export a photo into, creates directories if they don't exist

    Args:
        photo: a PhotoInstance object
        directory: a PhotoTemplate template string, may be None
        export_by_date: boolean; if True, creates output directories in form YYYY-MM-DD
        dest: top-level destination directory
        dry_run: boolean; if True, runs in dry-run mode and does not create output directories

    Returns:
        list of export directories

    Raises:
        click.BadOptionUsage if template is invalid
    """

    if export_by_date:
        date_created = DateTimeFormatter(photo.date)
        dest_path = os.path.join(
            dest, date_created.year, date_created.mm, date_created.dd
        )
        if not (dry_run or os.path.isdir(dest_path)):
            os.makedirs(dest_path)
        dest_paths = [dest_path]
    elif directory:
        # got a directory template, render it and check results are valid
        dirnames, unmatched = photo.render_template(directory, dirname=True)
        if not dirnames or unmatched:
            raise click.BadOptionUsage(
                "directory",
                f"Invalid template '{directory}': results={dirnames} unmatched={unmatched}",
            )

        dest_paths = []
        for dirname in dirnames:
            dirname = sanitize_filepath(dirname)
            dest_path = os.path.join(dest, dirname)
            if not is_valid_filepath(dest_path):
                raise ValueError(f"Invalid file path: '{dest_path}'")
            if not dry_run and not os.path.isdir(dest_path):
                os.makedirs(dest_path)
            dest_paths.append(dest_path)
    else:
        dest_paths = [dest]
    return dest_paths


def find_files_in_branch(pathname, filename):
    """ Search a directory branch to find file(s) named filename
        The branch searched includes all folders below pathname and 
        the parent tree of pathname but not pathname itself.

        e.g. find filename in children folders and parent folders

    Args:
        pathname: str, full path of directory to search
        filename: str, filename to search for
    
    Returns: list of full paths to any matching files
    """

    pathname = pathlib.Path(pathname).resolve()
    files = []

    # walk down the tree
    for root, _, filenames in os.walk(pathname):
        # for directory in directories:
        # print(os.path.join(root, directory))
        for fname in filenames:
            if fname == filename and pathlib.Path(root) != pathname:
                files.append(os.path.join(root, fname))

    # walk up the tree
    path = pathlib.Path(pathname)
    for root in path.parents:
        filenames = os.listdir(root)
        for fname in filenames:
            filepath = os.path.join(root, fname)
            if fname == filename and os.path.isfile(filepath):
                files.append(os.path.join(root, fname))

    return files


def load_uuid_from_file(filename):
    """ Load UUIDs from file.  Does not validate UUIDs.
        Format is 1 UUID per line, any line beginning with # is ignored.
        Whitespace is stripped.

    Arguments:
        filename: file name of the file containing UUIDs
    
    Returns:
        list of UUIDs or empty list of no UUIDs in file
    
    Raises:
        FileNotFoundError if file does not exist
    """

    if not pathlib.Path(filename).is_file():
        raise FileNotFoundError(f"Could not find file {filename}")

    uuid = []
    with open(filename, "r") as uuid_file:
        for line in uuid_file:
            line = line.strip()
            if len(line) and line[0] != "#":
                uuid.append(line)
    return uuid


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
