""" Export previews for photos in the Photos library

To run this with osxphotos on currently selected photos:

    osxphotos run export_previews.py --selected export_path
"""

from __future__ import annotations

import pathlib
import shutil

import click

import osxphotos
from osxphotos.cli import echo, echo_error, query_command, verbose
from osxphotos.cli.export import get_dirnames_from_template, get_filenames_from_template
from osxphotos.cli.param_types import TemplateString
from osxphotos.utils import pluralize


@query_command
@click.option("--dry-run", is_flag=True, help="Dry run, don't actually export")
@click.option(
    "--directory",
    type=TemplateString(),
    help="Directory to export to under export_path. This is an osxphotos template string. "
    "For example, to export previews to directories based on creation date: "
    "--directory '{created.year}/{created.mm}/{created.dd}' ",
)
@click.option(
    "--filename",
    "filename_template",
    type=TemplateString(),
    help="Filename for exported preview. "
    "This is an osxphotos template string; "
    "for example, to export previews to filename based on creation date: "
    "--filename '{original_name}-{created.year}-{created.mm}-{created.dd}' ",
)
@click.argument(
    "export_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
def export_previews(
    photos: list[osxphotos.PhotoInfo],
    dry_run: bool,
    directory: str,
    filename_template: str,
    export_dir: str,
    **kwargs,
):
    """Export previews for photos in the Photos library.

    Pass one or more query options to select photos to export or use without query options
    to export all images.

    If --directory is passed, the previews will be exported to subdirectories under export_path
    based on the template string passed to --directory. For example, to export previews to
    directories based on creation date: --directory '{created.year}/{created.mm}/{created.dd}'

    If --filename is passed, the previews will be exported with the filename specified by the
    template string passed to --filename. For example, to export previews to filename based on
    creation date: --filename '{original_name}-{created.year}-{created.mm}-{created.dd}'

    If --dry-run is passed, the previews will not actually be exported but the export will be
    simulated and the export paths printed to stdout.
    """

    verbose(f"Found {len(photos)} photo(s)")
    count = 0
    for photo in photos:
        try:
            # first derivative is the largest preview, so use that one
            preview = pathlib.Path(photo.path_derivatives[0])
        except IndexError:
            echo(f"No preview for {photo.original_filename} ({photo.uuid})")
            continue

        verbose(f"Found preview for {photo.original_filename}: {preview}")
        count += export_preview_to_directory_with_filename(
            photo, preview, export_dir, directory, filename_template, dry_run
        )
    echo(f"Exported {count} preview {pluralize(count, 'image', 'images')}")


def export_preview_to_directory_with_filename(
    photo: osxphotos.PhotoInfo,
    preview_path: str,
    export_dir: str,
    directory: str,
    filename_template: str,
    dry_run: bool,
) -> int:
    """Export preview for photo to directory with filename; returns count of images exported"""
    count = 0
    for dirname in get_dirnames_from_template(
        photo=photo,
        directory=directory,
        export_by_date=False,
        dest=export_dir,
        dry_run=dry_run,
    ):
        for filename in get_filenames_from_template(
            photo=photo,
            filename_template=filename_template,
            export_dir=export_dir,
            dest_path=dirname,
            original_name=True,
        ):
            # need to change filename extension to match preview
            filename = pathlib.Path(filename).with_suffix(preview_path.suffix)
            dest_path = pathlib.Path(dirname) / filename
            echo(
                f"Exporting preview for {photo.original_filename} ({photo.uuid}) to {dest_path}"
            )
            if not dry_run:
                try:
                    shutil.copy(preview_path, dest_path)
                except Exception as e:
                    echo_error(f"Error exporting preview: {e}")
                    continue
            count += 1
    return count


if __name__ == "__main__":
    export_previews()
