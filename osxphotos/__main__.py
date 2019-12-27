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
from .utils import create_path_by_date

# TODO: add "--any" to search any field (e.g. keyword, description, title contains "wedding") (add case insensitive option)


class CLI_Obj:
    def __init__(self, db=None, json=False, debug=False):
        if debug:
            osxphotos._debug(True)
        self.db = db
        self.json = json


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify database file.",
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
@click.pass_obj
def keywords(cli_obj):
    """ Print out keywords found in the Photos library. """
    photosdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    keywords = {"keywords": photosdb.keywords_as_dict}
    if cli_obj.json:
        click.echo(json.dumps(keywords))
    else:
        click.echo(yaml.dump(keywords, sort_keys=False))


@cli.command()
@click.pass_obj
def albums(cli_obj):
    """ Print out albums found in the Photos library. """
    photosdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    albums = {"albums": photosdb.albums_as_dict}
    if photosdb.db_version >= _PHOTOS_5_VERSION:
        albums["shared albums"] = photosdb.albums_shared_as_dict

    if cli_obj.json:
        click.echo(json.dumps(albums))
    else:
        click.echo(yaml.dump(albums, sort_keys=False))



@cli.command()
@click.pass_obj
def persons(cli_obj):
    """ Print out persons (faces) found in the Photos library. """
    photosdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    persons = {"persons": photosdb.persons_as_dict}
    if cli_obj.json:
        click.echo(json.dumps(persons))
    else:
        click.echo(yaml.dump(persons, sort_keys=False))


@cli.command()
@click.pass_obj
def info(cli_obj):
    """ Print out descriptive info of the Photos library database. """
    pdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    info = {}
    info["database_path"] = pdb.db_path
    info["database_version"] = pdb.db_version

    photos = pdb.photos()
    info["photo_count"] = len(photos)

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

    if cli_obj.json:
        click.echo(json.dumps(info))
    else:
        click.echo(yaml.dump(info, sort_keys=False))


@cli.command()
@click.option(
    "--json",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)
@click.pass_obj
def dump(cli_obj, json):
    """ Print list of all photos & associated info from the Photos library. """
    pdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    photos = pdb.photos()
    print_photo_info(photos, cli_obj.json or json)


@cli.command(name="list")
@click.pass_obj
def list_libraries(cli_obj):
    """ Print list of Photos libraries found on the system. """
    photo_libs = osxphotos.utils.list_photo_libraries()
    sys_lib = None
    _, major, _ = osxphotos.utils._get_os_version()
    if int(major) >= 15:
        sys_lib = osxphotos.utils.get_system_library_path()

    last_lib = osxphotos.utils.get_last_library_path()

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
    "--shared", is_flag=True, help="Search for photos in shared iCloud album (Photos 5 only)."
)
@click.option(
    "--not-shared", is_flag=True, help="Search for photos not in shared iCloud album (Photos 5 only)."
)
@click.option(
    "--json",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format",
)
@click.pass_obj
@click.pass_context
def query(
    ctx,
    cli_obj,
    keyword,
    person,
    album,
    uuid,
    title,
    no_title,
    description,
    no_description,
    ignore_case,
    json,
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
    else:
        photos = _query(
            cli_obj,
            keyword,
            person,
            album,
            uuid,
            title,
            no_title,
            description,
            no_description,
            ignore_case,
            json,
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
        )
        print_photo_info(photos, cli_obj.json or json)


@cli.command()
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
    "--shared", is_flag=True, help="Search for photos in shared iCloud album (Photos 5 only)."
)
@click.option(
    "--not-shared", is_flag=True, help="Search for photos not in shared iCloud album (Photos 5 only)."
)
@click.option("--verbose", is_flag=True, help="Print verbose output.")
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
    help="Also export edited version of photo "
    'if an edited version exists.  Edited photo will be named in form of "photoname_edited.ext"',
)
@click.option(
    "--original-name",
    is_flag=True,
    help="Use photo's original filename instead of current filename for export.",
)
@click.option(
    "--sidecar",
    is_flag=True,
    help="Create json sidecar for each photo exported "
    f"in format useable by exiftool ({_EXIF_TOOL_URL}) "
    "The sidecar file can be used to apply metadata to the file with exiftool, for example: "
    '"exiftool -j=photoname.jpg.json photoname.jpg" '
    "The sidecar file is named in format photoname.ext.json where ext is extension of the photo (e.g. jpg).",
)
@click.argument("dest", nargs=1)
@click.pass_obj
@click.pass_context
def export(
    ctx,
    cli_obj,
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
    shared,
    not_shared,
    verbose,
    overwrite,
    export_by_date,
    export_edited,
    original_name,
    sidecar,
    dest,
):
    """ Export photos from the Photos database.
        Export path DEST is required.
        Optionally, query the Photos database using 1 or more search options; 
        if more than one option is provided, they are treated as "AND" 
        (e.g. search for photos matching all options).
        If no query options are provided, all photos will be exported.
    """

    # TODO: --export-edited, --export-original

    if not os.path.isdir(dest):
        sys.exit("DEST must be valid path")

    # if no query terms, show help and return
    photos = _query(
        cli_obj,
        keyword,
        person,
        album,
        uuid,
        title,
        no_title,
        description,
        no_description,
        ignore_case,
        json,
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
    )

    if photos:
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
            ]
        )
        for p in photos:
            dump.append(
                [
                    p.uuid,
                    p.filename,
                    p.original_filename,
                    str(p.date),
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
                ]
            )
        for row in dump:
            csv_writer.writerow(row)


def _query(
    cli_obj,
    keyword,
    person,
    album,
    uuid,
    title,
    no_title,
    description,
    no_description,
    ignore_case,
    json,
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
):
    """ run a query against PhotosDB to extract the photos based on user supply criteria """
    """ used by query and export commands """
    """ arguments must be passed in same order as query and export """
    """ if either is modified, need to ensure all three functions are updated """

    photosdb = osxphotos.PhotosDB(dbfile=cli_obj.db)
    photos = photosdb.photos(keywords=keyword, persons=person, albums=album, uuid=uuid)

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
        # if more than one, find photos with all name values in in description
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
):
    """ Helper function for export that does the actual export
        photo: PhotoInfo object
        dest: destination path as string
        verbose: boolean; print verbose output
        export_by_date: boolean; create export folder in form dest/YYYY/MM/DD
        sidecar: boolean; create json sidecar file with export
        overwrite: boolean; overwrite dest file if it already exists
        original_name: boolean; use original filename instead of current filename
        returns destination path of exported photo or None if photo was missing 
    """

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

    photo_path = photo.export(dest, filename, sidecar=sidecar, overwrite=overwrite)

    # if export-edited, also export the edited version
    # verify the photo has adjustments and valid path to avoid raising an exception
    if export_edited and photo.hasadjustments and photo.path_edited is not None:
        edited_name = pathlib.Path(filename)
        edited_name = f"{edited_name.stem}_edited{edited_name.suffix}"
        if verbose:
            click.echo(f"Exporting edited version of {filename} as {edited_name}")
        photo.export(
            dest, edited_name, sidecar=sidecar, overwrite=overwrite, edited=True
        )

    return photo_path


if __name__ == "__main__":
    cli()
