"""osxphotos show command"""

import pathlib
import re

import click

from osxphotos._constants import UUID_PATTERN
from osxphotos.export_db_utils import get_uuid_for_filepath
from osxphotos.photosdb.photosdb_utils import get_photos_library_version
from osxphotos.platform import assert_macos
from osxphotos.utils import get_last_library_path

assert_macos()

from osxphotos.photoscript_utils import (
    photoscript_object_from_name,
    photoscript_object_from_uuid,
)

from .cli_commands import echo, echo_error
from .cli_params import DB_OPTION
from .click_rich_echo import set_rich_theme


@click.command(name="show")
@DB_OPTION
@click.argument("uuid_or_name", metavar="UUID_OR_NAME", nargs=1, required=True)
@click.pass_context
def show(ctx, db, uuid_or_name):
    """Show photo, album, or folder in Photos from UUID_OR_NAME

    Examples:

    osxphotos show 12345678-1234-1234-1234-123456789012

    osxphotos show "My Album"

    osxphotos show "My Folder"

    osxphotos show IMG_1234.JPG

    show can also be used to show a photo exported with `osxphotos export`:

    osxphotos show /path/to/exported/photo.jpg

    In this case, the UUID_OR_NAME is the path to the exported photo and osxphotos
    will attempt to find the export database to match the photo to the original in
    Photos. If your export database is not in the default location in the root of the
    export directory, this will not work.

    Notes:

    This command requires Photos library version 5 or higher.
    Currently this command cannot be used to show subfolders in Photos.
    """
    db = db or get_last_library_path()
    if not db:
        echo(
            "Could not find Photos library. Use --library/--db to specify path to Photos library."
        )
        ctx.exit(1)

    if get_photos_library_version(db) < 5:
        echo_error("[error]show command requires Photos library version 5 or higher")
        ctx.exit(1)

    try:
        if re.match(UUID_PATTERN, uuid_or_name):
            if not (obj := photoscript_object_from_uuid(uuid_or_name, db)):
                raise ValueError(
                    f"could not find asset with UUID [uuid]{uuid_or_name}[/]"
                )
            obj_type = obj.__class__.__name__
            echo(f"Found [filename]{obj_type}[/] with UUID: [uuid]{uuid_or_name}[/]")
            obj.spotlight()
        elif obj := photoscript_object_from_name(uuid_or_name, db):
            obj_type = obj.__class__.__name__
            echo(
                f"Found [filename]{obj_type}[/] with name: [filepath]{uuid_or_name}[/]"
            )
            obj.spotlight()
        elif uuid := get_uuid_for_filepath(pathlib.Path(uuid_or_name).resolve()):
            if not (obj := photoscript_object_from_uuid(uuid, db)):
                raise ValueError(
                    f"could not find asset with UUID [uuid]{uuid}[/] for file [filepath]{uuid_or_name}[/]"
                )
            obj_type = obj.__class__.__name__
            echo(
                f"Found [filename]{obj_type}[/] from export database: [filepath]{uuid_or_name}[/]"
            )
            obj.spotlight()
        else:
            raise ValueError(
                f"could not find asset with name [filepath]{uuid_or_name}[/]"
            )
    except Exception as e:
        echo_error(f"[error]Error finding asset [uuid]{uuid_or_name}[/]: {e}")
        ctx.exit(1)
