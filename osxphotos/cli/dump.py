"""dump command for osxphotos CLI """

import click

import osxphotos
from osxphotos.cli.click_rich_echo import (
    rich_click_echo,
    set_rich_console,
    set_rich_theme,
)
from osxphotos.iphoto import is_iphoto_library
from osxphotos.photoquery import QueryOptions
from osxphotos.phototemplate import RenderOptions

from .cli_params import (
    DB_ARGUMENT,
    DB_OPTION,
    DELETED_OPTIONS,
    FIELD_OPTION,
    JSON_OPTION,
)
from .color_themes import get_default_theme
from .common import get_photos_db
from .list import _list_libraries
from .print_photo_info import print_photo_fields, print_photo_info
from .verbose import get_verbose_console


@click.command()
@DB_OPTION
@JSON_OPTION
@DELETED_OPTIONS
@FIELD_OPTION
@click.option(
    "--print",
    "print_template",
    metavar="TEMPLATE",
    multiple=True,
    help="Render TEMPLATE string for each photo queried and print to stdout. "
    "TEMPLATE is an osxphotos template string. "
    "This may be useful for creating custom reports, etc. "
    "If --print TEMPLATE is provided, regular output is suppressed "
    "and only the rendered TEMPLATE values are printed. "
    "May be repeated to print multiple template strings. ",
)
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def dump(
    ctx,
    cli_obj,
    db,
    deleted,
    deleted_only,
    field,
    json_,
    photos_library,
    print_template,
):
    """Print list of all photos & associated info from the Photos library.

    NOTE: dump is DEPRECATED and will be removed in a future release.
    Use `osxphotos query` instead.
    """

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    cli_json = cli_obj.json if cli_obj is not None else None

    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["dump"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    # check exclusive options
    if deleted and deleted_only:
        click.echo("Incompatible dump options", err=True)
        click.echo(ctx.obj.group.commands["dump"].get_help(ctx), err=True)
        return

    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(get_default_theme())

    photosdb = (
        osxphotos.iPhotoDB(db)
        if is_iphoto_library(db)
        else osxphotos.PhotosDB(dbfile=db)
    )
    if deleted or deleted_only:
        photos = photosdb.photos(movies=True, intrash=True)
    else:
        photos = []
    if not deleted_only:
        photos += photosdb.photos(movies=True)

    if not print_template and not field:
        # just dump and be done
        print_photo_info(photos, cli_json or json_)
        return

    if field:
        print_photo_fields(photos, field, cli_json or json_)

    if print_template:
        # have print template(s)
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
