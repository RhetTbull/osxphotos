"""Metadata from files

Run with `osxphotos run metadata_from_files.py /path/to/photos/* [--walk] [--dry-run]`
"""

import os
import sys

import click
import photoscript

import osxphotos
from osxphotos._constants import _OSXPHOTOS_NONE_SENTINEL
from osxphotos.cli import echo, echo_error
from osxphotos.cli.batch_edit import photoscript_photo
from osxphotos.cli.cli_params import DB_OPTION
from osxphotos.cli.param_types import TemplateString
from osxphotos.cli.signaturequery import SignatureQuery
from osxphotos.fingerprint import fingerprint
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.image_file_utils import is_image_file, is_video_file
from osxphotos.photosalbum import PhotosAlbumPhotoScript
from osxphotos.phototemplate import RenderOptions
from osxphotos.utils import get_last_library_path, pluralize


@click.command()
@click.option(
    "--title",
    metavar="TITLE_TEMPLATE",
    type=TemplateString(),
    help="Set title of photo.",
)
@click.option(
    "--description",
    metavar="DESCRIPTION_TEMPLATE",
    type=TemplateString(),
    help="Set description of photo.",
)
@click.option(
    "--keyword",
    metavar="KEYWORD_TEMPLATE",
    type=TemplateString(),
    multiple=True,
    help="Set keywords of photo. May be specified multiple times.",
)
@click.option(
    "--album",
    "-a",
    metavar="ALBUM_TEMPLATE",
    multiple=True,
    type=TemplateString(),
    help="Add photo to album ALBUM_TEMPLATE. "
    "ALBUM_TEMPLATE is an osxphotos template string. "
    "Photos may be added to more than one album by repeating --album. "
    "See also, --split-folder. "
    "See Template System in help (`osxphotos docs`) for additional information.",
)
@click.option(
    "--split-folder",
    "-f",
    help="When used with --album, automatically create hierarchal folders for albums "
    "as needed by splitting album name into folders and album. "
    "You must specify the character used to split folders and albums. "
    "For example, '--split-folder \"/\"' will split the album name 'Folder/Album' "
    "into folder 'Folder' and album 'Album'. ",
)
@click.option(
    "--signature",
    "-U",
    type=TemplateString(),
    help="Custom template for signature for matching photos in the library to those being scanned. "
    "The signature is used to match photos in the library to those being scanned. "
    "If you do not use --signature, the fingerprint will be used for photos "
    "and lowercase filename + size will be used for videos "
    "(a fingerprint is not always stored for videos in the Photos library). ",
)
@click.option("--walk", is_flag=True, help="Walk directories recursively")
@click.option("--dry-run", is_flag=True, help="Dry run: Do not modify Photos library")
@DB_OPTION
@click.argument("paths", nargs=-1)
def main(
    title: str | None,
    description: str | None,
    keyword: tuple[str, ...],
    album: tuple[str, ...],
    split_folder: str | None,
    signature: str | None,
    walk: bool,
    dry_run: bool,
    db: str,
    paths: tuple[str],
):
    """
    Batch edit metadata for assets in Photos from files on disk.

    Scans one or more files and directories for images and videos, finds matching assets in the Photos
    library by fingerprint, and sets each asset's caption to the file's parent directory path.
    """
    if not paths:
        print("No paths provided")
        return

    echo("Collecting files to check...")
    files = scan_files(paths, walk)
    echo(f"Found [num]{len(files)}[/] file{'s' if len(files) != 1 else ''} to check")

    echo("Loading Photos library...")
    library = db or get_last_library_path()
    photosdb = osxphotos.PhotosDB(library)

    fq = SignatureQuery(library, signature) if signature else FingerprintQuery(library)
    for file in files:
        matches = fq.possible_duplicates(file)
        if matches:
            parent_path = os.path.dirname(file)
            for uuid, date, filename in matches:
                echo(
                    f"Found match for file [filename]{file}[/] in Photos: "
                    f"[filename]{filename}[/] ([uuid]{uuid}[/])"
                )
                photo = photosdb.get_photo(uuid)
                set_photo_title_from_template(photo, file, title, dry_run)
                set_photo_description_from_template(photo, file, description, dry_run)
                set_photo_keywords_from_template(photo, file, keyword, False, dry_run)
                set_photo_albums_from_template(
                    photo, file, album, split_folder, dry_run
                )
        else:
            echo(f"No match found for file [filename]{file}[/] in Photos")


def set_caption(uuid: str, caption: str) -> None:
    """Set the caption (description) for a photo in Photos"""
    try:
        photo = photoscript.Photo(uuid)
        photo.description = caption
    except Exception as e:
        echo(f"Error setting caption for photo [uuid]{uuid}[/]: {e}")


def scan_files(paths: tuple[str], walk: bool) -> list[str]:
    """Scan given paths and return a list of image and video file paths"""
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            if walk:
                for root, _, filenames in os.walk(path):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
            else:
                for filename in os.listdir(path):
                    files.append(os.path.join(path, filename))
        else:
            files.append(os.path.abspath(path))
    return [file for file in files if is_image_file(file) or is_video_file(file)]


def set_photo_title_from_template(
    photo: osxphotos.PhotoInfo, filepath: str, title_template: str, dry_run: bool
):
    """Set photo title from template"""
    if not title_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="", filepath=filepath)

    title_string, _ = photo.render_template(title_template, render_options)
    title_string = [ts for ts in title_string if ts]
    if not title_string:
        echo(f"No title returned from template, nothing to do: [bold]{title_template}")
        return

    if len(title_string) > 1:
        echo_error(
            f"[error] Title template must return a single string: [bold]{title_string}"
        )
        sys.exit(1)

    echo(f"Setting [i]title[/i] to [bold]{title_string[0]}")
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.title = title_string[0]


def set_photo_description_from_template(
    photo: osxphotos.PhotoInfo, filepath: str, description_template: str, dry_run: bool
):
    """Set photo description from template"""
    if not description_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="", filepath=filepath)

    description_string, _ = photo.render_template(description_template, render_options)
    description_string = [ds for ds in description_string if ds]
    if not description_string:
        echo(
            f"No description returned from template, nothing to do: [bold]{description_template}"
        )
        return

    if len(description_string) > 1:
        echo_error(
            f"[error] Description template must return a single string: [bold]{description_string}"
        )
        sys.exit(1)

    echo(f"Setting [i]description[/] to [bold]{description_string[0]}")
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.description = description_string[0]


def set_photo_keywords_from_template(
    photo: osxphotos.PhotoInfo,
    filepath: str,
    keyword_template: list[str],
    replace_keywords: bool,
    dry_run: bool,
):
    """Set photo keywords from template"""
    if not keyword_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="", filepath=filepath)

    keywords = set()
    for kw in keyword_template:
        kw_string, _ = photo.render_template(kw, render_options)
        if kw_string:
            # filter out empty strings
            keywords.update([k for k in kw_string if k])

    if not keywords:
        echo(
            f"No keywords returned from template, nothing to do: [bold]{keyword_template}"
        )
        return

    if not replace_keywords:
        keywords.update(photo.keywords)

    echo(f"Setting [i]keywords[/] to {', '.join(f'[bold]{kw}[/]' for kw in keywords)}")
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.keywords = list(keywords)


def set_photo_albums_from_template(
    photo: osxphotos.PhotoInfo,
    filepath: str,
    album: tuple[str, ...],
    split_folder: str | None,
    dry_run: bool,
):
    """Add photo to album(s) based on album template"""
    if not album:
        return

    albums = []
    for a in album:
        albums.extend(render_album_template(photo, filepath, a))
    echo(
        f"Adding photo to [num]{len(albums)}[/] [i]{pluralize(len(albums), 'album', 'albums')}[/]"
    )

    # add photo to albums
    for a in albums:
        echo(f"Adding photo to [i]album[/] [bold]{a}[/]")
        if not dry_run:
            photos_album = PhotosAlbumPhotoScript(
                a, split_folder=split_folder, rich=True
            )
            ps_photo = photoscript_photo(photo)
            photos_album.add(ps_photo)


def render_album_template(
    photo: osxphotos.PhotoInfo,
    filepath: str,
    album_template: str,
):
    """Render template string for a photo"""
    options = RenderOptions(
        none_str=_OSXPHOTOS_NONE_SENTINEL, caller="batch_edit", filepath=filepath
    )
    template_values, _ = photo.render_template(album_template, options=options)

    # filter out empty strings
    template_values = [v.replace(_OSXPHOTOS_NONE_SENTINEL, "") for v in template_values]
    template_values = [v for v in template_values if v]
    return template_values


if __name__ == "__main__":
    main()
