"""query command for osxphotos CLI"""

import click

import osxphotos
from osxphotos.cli.click_rich_echo import (
    rich_click_echo,
    set_rich_console,
    set_rich_theme,
)
from osxphotos.debug import set_debug
from osxphotos.photosalbum import PhotosAlbum
from osxphotos.phototemplate import RenderOptions
from osxphotos.queryoptions import QueryOptions

from .color_themes import get_default_theme
from .common import (
    CLI_COLOR_ERROR,
    CLI_COLOR_WARNING,
    DB_ARGUMENT,
    DB_OPTION,
    DELETED_OPTIONS,
    FIELD_OPTION,
    JSON_OPTION,
    OSXPHOTOS_HIDDEN,
    QUERY_OPTIONS,
    get_photos_db,
    load_uuid_from_file,
)
from .list import _list_libraries
from .print_photo_info import print_photo_fields, print_photo_info
from .verbose import get_verbose_console


@click.command()
@DB_OPTION
@JSON_OPTION
@QUERY_OPTIONS
@DELETED_OPTIONS
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
@click.option(
    "--add-to-album",
    metavar="ALBUM",
    help="Add all photos from query to album ALBUM in Photos. Album ALBUM will be created "
    "if it doesn't exist.  All photos in the query results will be added to this album. "
    "This only works if the Photos library being queried is the last-opened (default) library in Photos. "
    "This feature is currently experimental.  I don't know how well it will work on large query sets.",
)
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
@click.option(
    "--debug", required=False, is_flag=True, default=False, hidden=OSXPHOTOS_HIDDEN
)
@DB_ARGUMENT
@click.pass_obj
@click.pass_context
def query(
    ctx,
    cli_obj,
    db,
    photos_library,
    add_to_album,
    added_after,
    added_before,
    added_in_last,
    album,
    burst,
    cloudasset,
    deleted_only,
    deleted,
    description,
    duplicate,
    edited,
    exif,
    external_edit,
    favorite,
    field,
    folder,
    from_date,
    from_time,
    has_comment,
    has_likes,
    has_raw,
    hdr,
    hidden,
    ignore_case,
    in_album,
    incloud,
    is_reference,
    json_,
    keyword,
    label,
    live,
    location,
    max_size,
    min_size,
    missing,
    name,
    no_comment,
    no_description,
    no_likes,
    no_location,
    no_keyword,
    no_place,
    no_title,
    not_burst,
    not_cloudasset,
    not_favorite,
    not_hdr,
    not_hidden,
    not_in_album,
    not_incloud,
    not_live,
    not_missing,
    not_panorama,
    not_portrait,
    not_reference,
    not_screenshot,
    not_selfie,
    not_shared,
    not_slow_mo,
    not_time_lapse,
    only_movies,
    only_photos,
    panorama,
    person,
    place,
    portrait,
    print_template,
    query_eval,
    query_function,
    quiet,
    regex,
    screenshot,
    selected,
    selfie,
    shared,
    slow_mo,
    time_lapse,
    title,
    to_date,
    to_time,
    uti,
    uuid_from_file,
    uuid,
    year,
    debug,  # handled in cli/__init__.py
):
    """Query the Photos database using 1 or more search options;
    if more than one option is provided, they are treated as "AND"
    (e.g. search for photos matching all options).
    """

    # if no query terms, show help and return
    # sanity check input args
    nonexclusive = [
        added_after,
        added_before,
        added_in_last,
        album,
        duplicate,
        edited,
        exif,
        external_edit,
        folder,
        from_date,
        from_time,
        has_raw,
        keyword,
        label,
        max_size,
        min_size,
        name,
        person,
        query_eval,
        query_function,
        regex,
        selected,
        to_date,
        to_time,
        uti,
        uuid_from_file,
        uuid,
        year,
    ]
    exclusive = [
        (any(description), no_description),
        (any(place), no_place),
        (any(title), no_title),
        (any(keyword), no_keyword),
        (burst, not_burst),
        (cloudasset, not_cloudasset),
        (deleted, deleted_only),
        (favorite, not_favorite),
        (has_comment, no_comment),
        (has_likes, no_likes),
        (hdr, not_hdr),
        (hidden, not_hidden),
        (in_album, not_in_album),
        (incloud, not_incloud),
        (live, not_live),
        (location, no_location),
        (missing, not_missing),
        (only_photos, only_movies),
        (panorama, not_panorama),
        (portrait, not_portrait),
        (screenshot, not_screenshot),
        (selfie, not_selfie),
        (shared, not_shared),
        (slow_mo, not_slow_mo),
        (time_lapse, not_time_lapse),
        (is_reference, not_reference),
    ]
    # print help if no non-exclusive term or a double exclusive term is given
    if any(all(bb) for bb in exclusive) or not any(
        nonexclusive + [b ^ n for b, n in exclusive]
    ):
        click.echo("Incompatible query options", err=True)
        click.echo(ctx.obj.group.commands["query"].get_help(ctx), err=True)
        return

    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(get_default_theme())

    # actually have something to query
    # default searches for everything
    photos = True
    movies = True
    if only_movies:
        photos = False
    if only_photos:
        movies = False

    # load UUIDs if necessary and append to any uuids passed with --uuid
    if uuid_from_file:
        uuid_list = list(uuid)  # Click option is a tuple
        uuid_list.extend(load_uuid_from_file(uuid_from_file))
        uuid = tuple(uuid_list)

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["query"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    photosdb = osxphotos.PhotosDB(dbfile=db)
    query_options = QueryOptions(
        added_after=added_after,
        added_before=added_before,
        added_in_last=added_in_last,
        album=album,
        burst=burst,
        cloudasset=cloudasset,
        deleted_only=deleted_only,
        deleted=deleted,
        description=description,
        duplicate=duplicate,
        edited=edited,
        exif=exif,
        external_edit=external_edit,
        favorite=favorite,
        folder=folder,
        from_date=from_date,
        from_time=from_time,
        function=query_function,
        has_comment=has_comment,
        has_likes=has_likes,
        has_raw=has_raw,
        hdr=hdr,
        hidden=hidden,
        ignore_case=ignore_case,
        in_album=in_album,
        incloud=incloud,
        is_reference=is_reference,
        keyword=keyword,
        label=label,
        live=live,
        location=location,
        max_size=max_size,
        min_size=min_size,
        missing=missing,
        movies=movies,
        name=name,
        no_comment=no_comment,
        no_description=no_description,
        no_likes=no_likes,
        no_location=no_location,
        no_keyword=no_keyword,
        no_place=no_place,
        no_title=no_title,
        not_burst=not_burst,
        not_cloudasset=not_cloudasset,
        not_favorite=not_favorite,
        not_hdr=not_hdr,
        not_hidden=not_hidden,
        not_in_album=not_in_album,
        not_incloud=not_incloud,
        not_live=not_live,
        not_missing=not_missing,
        not_panorama=not_panorama,
        not_portrait=not_portrait,
        not_reference=not_reference,
        not_screenshot=not_screenshot,
        not_selfie=not_selfie,
        not_shared=not_shared,
        not_slow_mo=not_slow_mo,
        not_time_lapse=not_time_lapse,
        panorama=panorama,
        person=person,
        photos=photos,
        place=place,
        portrait=portrait,
        query_eval=query_eval,
        regex=regex,
        screenshot=screenshot,
        selected=selected,
        selfie=selfie,
        shared=shared,
        slow_mo=slow_mo,
        time_lapse=time_lapse,
        title=title,
        to_date=to_date,
        to_time=to_time,
        uti=uti,
        uuid=uuid,
        year=year,
    )

    try:
        photos = photosdb.query(query_options)
    except ValueError as e:
        if "Invalid query_eval CRITERIA:" in str(e):
            msg = str(e).split(":")[1]
            raise click.BadOptionUsage(
                "query_eval", f"Invalid query-eval CRITERIA: {msg}"
            )
        else:
            raise ValueError(e)

    # below needed for to make CliRunner work for testing
    cli_json = cli_obj.json if cli_obj is not None else None

    if add_to_album and photos:
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
