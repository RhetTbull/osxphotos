"""query command for osxphotos CLI"""

import click

import osxphotos
from osxphotos.debug import set_debug
from osxphotos.photosalbum import PhotosAlbum
from osxphotos.queryoptions import QueryOptions

from .common import (
    CLI_COLOR_ERROR,
    CLI_COLOR_WARNING,
    DB_ARGUMENT,
    DB_OPTION,
    DELETED_OPTIONS,
    JSON_OPTION,
    OSXPHOTOS_HIDDEN,
    QUERY_OPTIONS,
    get_photos_db,
    load_uuid_from_file,
)
from .list import _list_libraries
from .print_photo_info import print_photo_info


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
    keyword,
    person,
    album,
    folder,
    name,
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
    from_time,
    to_time,
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
    location,
    no_location,
    label,
    deleted,
    deleted_only,
    has_comment,
    no_comment,
    has_likes,
    no_likes,
    is_reference,
    in_album,
    not_in_album,
    duplicate,
    min_size,
    max_size,
    regex,
    selected,
    exif,
    query_eval,
    query_function,
    add_to_album,
    debug,  # handled in cli/__init__.py
):
    """Query the Photos database using 1 or more search options;
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
        name,
        uuid,
        uuid_from_file,
        edited,
        external_edit,
        uti,
        has_raw,
        from_date,
        to_date,
        from_time,
        to_time,
        label,
        is_reference,
        query_eval,
        query_function,
        min_size,
        max_size,
        regex,
        selected,
        exif,
        duplicate,
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
        (in_album, not_in_album),
        (location, no_location),
    ]
    # print help if no non-exclusive term or a double exclusive term is given
    if any(all(bb) for bb in exclusive) or not any(
        nonexclusive + [b ^ n for b, n in exclusive]
    ):
        click.echo("Incompatible query options", err=True)
        click.echo(ctx.obj.group.commands["query"].get_help(ctx), err=True)
        return

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
        photos=photos,
        movies=movies,
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
        from_time=from_time,
        to_time=to_time,
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
        location=location,
        no_location=no_location,
        label=label,
        deleted=deleted,
        deleted_only=deleted_only,
        has_comment=has_comment,
        no_comment=no_comment,
        has_likes=has_likes,
        no_likes=no_likes,
        is_reference=is_reference,
        in_album=in_album,
        not_in_album=not_in_album,
        name=name,
        min_size=min_size,
        max_size=max_size,
        query_eval=query_eval,
        function=query_function,
        regex=regex,
        selected=selected,
        exif=exif,
        duplicate=duplicate,
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

    print_photo_info(photos, cli_json or json_, print_func=click.echo)
