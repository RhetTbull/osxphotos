"""query command for osxphotos CLI"""

import sys

import click

import osxphotos
from osxphotos.cli.click_rich_echo import (
    rich_click_echo,
    set_rich_console,
    set_rich_theme,
)
from osxphotos.iphoto import is_iphoto_library
from osxphotos.photoquery import query_options_from_kwargs
from osxphotos.phototemplate import RenderOptions
from osxphotos.platform import assert_macos, is_macos

if is_macos:
    from osxphotos.photosalbum import PhotosAlbum

from .cli_params import (
    DB_ARGUMENT,
    DB_OPTION,
    DELETED_OPTIONS,
    FIELD_OPTION,
    JSON_OPTION,
    QUERY_OPTIONS,
    make_click_option_decorator,
)
from .color_themes import get_default_theme
from .common import CLI_COLOR_ERROR, CLI_COLOR_WARNING, OSXPHOTOS_HIDDEN, get_photos_db
from .list import _list_libraries
from .print_photo_info import print_photo_fields, print_photo_info
from .verbose import get_verbose_console

MACOS_OPTIONS = make_click_option_decorator(
    *[
        click.Option(
            ["--add-to-album"],
            metavar="ALBUM",
            help="Add all photos from query to album ALBUM in Photos. Album ALBUM will be created "
            "if it doesn't exist.  All photos in the query results will be added to this album. "
            "This only works if the Photos library being queried is the last-opened (default) library in Photos. "
            "This feature is currently experimental.  I don't know how well it will work on large query sets.",
        ),
    ]
    if is_macos
    else []
)


@click.command()
@DB_OPTION
@JSON_OPTION
@click.option(
    "--count", is_flag=True, help="Print count of photos matching query and exit."
)
@QUERY_OPTIONS
@DELETED_OPTIONS
@MACOS_OPTIONS
@click.option(
    "--quiet",
    is_flag=True,
    help="Quiet output; doesn't actually print query results. "
    "Useful with --print and --add-to-album if you don't want to see the actual query results.",
)
@FIELD_OPTION
@click.option(
    "--print",
    "print_template",
    metavar="TEMPLATE",
    multiple=True,
    help="Render TEMPLATE string for each photo queried and print to stdout. "
    "TEMPLATE is an osxphotos template string. "
    "This may be useful for creating custom reports, etc. "
    "Most useful with --quiet. "
    "May be repeated to print multiple template strings. ",
)
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def query(
    ctx,
    cli_obj,
    db,
    field,
    json_,
    count,
    print_template,
    quiet,
    photos_library,
    add_to_album=False,
    **kwargs,
):
    """Query the Photos database using 1 or more search options;
    if more than one different option is provided, they are treated as "AND"
    (e.g. search for photos matching all options).
    If the same query option is provided multiple times, they are treated as
    "OR" (e.g. search for photos matching any of the options).

    For example:

    osxphotos query --person "John Doe" --person "Jane Doe" --keyword "vacation"

    will return all photos with either person of ("John Doe" OR "Jane Doe") AND keyword of "vacation"

    If not query options are provided, all photos in the library will be returned.
    """

    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(get_default_theme())

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["query"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    try:
        query_options = query_options_from_kwargs(**kwargs)
    except Exception as e:
        raise click.BadOptionUsage("query", str(e)) from e

    photosdb = (
        osxphotos.iPhotoDB(db)
        if is_iphoto_library(db)
        else osxphotos.PhotosDB(dbfile=db)
    )

    try:
        photos = photosdb.query(query_options)
    except ValueError as e:
        if "Invalid query_eval CRITERIA:" not in str(e):
            raise ValueError(e) from e

        msg = str(e).split(":")[1]
        raise click.BadOptionUsage(
            "query_eval", f"Invalid query-eval CRITERIA: {msg}"
        ) from e

    # below needed for to make CliRunner work for testing
    cli_json = cli_obj.json if cli_obj is not None else None

    if count:
        click.echo(len(photos))
        return

    if add_to_album and photos:
        assert_macos()

        album_query = PhotosAlbum(add_to_album, verbose=None)
        photo_len = len(photos)
        photo_word = "photos" if photo_len > 1 else "photo"
        click.echo(
            f"Adding {photo_len} {photo_word} to album '{album_query.name}'. Note: Photos may prompt you to confirm this action.",
            err=True,
        )
        try:
            album_query.add_list(photos)
        except Exception as e:
            click.secho(
                f"Error adding photos to album {add_to_album}: {e}",
                fg=CLI_COLOR_ERROR,
                err=True,
            )

    if field:
        print_photo_fields(photos, field, cli_json or json_)

    if print_template:
        options = RenderOptions()
        for p in photos:
            for template in print_template:
                rendered_templates, unmatched = p.render_template(
                    template,
                    options,
                )
                if unmatched:
                    rich_click_echo(
                        f"[warning]Unmatched template field: {unmatched}[/]"
                    )
                for rendered_template in rendered_templates:
                    if not rendered_template:
                        continue
                    print(rendered_template)

    if not quiet and not field:
        print_photo_info(photos, cli_json or json_, print_func=click.echo)
