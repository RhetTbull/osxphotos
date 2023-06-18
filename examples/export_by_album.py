""" Export all photos to specified directory using album names as folders
    If file has been edited, also export the edited version, 
    otherwise, export the original version 
    This will result in duplicate photos if photo is in more than album """

import os.path
import pathlib
import sys

import click
from pathvalidate import is_valid_filepath, sanitize_filepath

import osxphotos


@click.command()
@click.argument("export_path", type=click.Path(exists=True))
@click.option(
    "--default-album",
    help="Default folder for photos with no album. Defaults to 'unfiled'",
    default="unfiled",
)
@click.option(
    "--library-path",
    help="Path to Photos library, default to last used library",
    default=None,
)
@click.option(
    "--edited",
    help="Also export edited versions of photos (default is originals only)",
    is_flag=True,
    default=False,
)
def export(export_path, default_album, library_path, edited):
    """Export all photos, organized by album"""
    export_path = os.path.expanduser(export_path)
    library_path = os.path.expanduser(library_path) if library_path else None

    if library_path is not None:
        photosdb = osxphotos.PhotosDB(library_path)
    else:
        photosdb = osxphotos.PhotosDB()

    photos = photosdb.photos()

    for p in photos:
        if not p.ismissing:
            albums = p.albums
            if not albums:
                albums = [default_album]
            for album in albums:
                click.echo(f"exporting {p.original_filename} in album {album}")

                # make sure no invalid characters in destination path (could be in album name)
                album_name = sanitize_filepath(album, platform="auto")

                # create destination folder, if necessary, based on album name
                dest_dir = os.path.join(export_path, album_name)

                # verify path is a valid path
                if not is_valid_filepath(dest_dir, platform="auto"):
                    sys.exit(f"Invalid filepath {dest_dir}")

                # create destination dir if needed
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)

                filename = p.original_filename
                # export the photo but only if --edited, photo has adjustments, and
                # path_edited is not None (can be None if edited photo is missing)
                if edited and p.hasadjustments and p.path_edited:
                    # export edited version
                    # use original filename with _edited appended but make sure suffix is
                    # same as edited file
                    edited_filename = f"{pathlib.Path(filename).stem}_edited{pathlib.Path(p.path_edited).suffix}"
                    exported = p.export(dest_dir, edited_filename, edited=True)
                    click.echo(f"Exported {edited_filename} to {exported}")
                # export unedited version
                exported = p.export(dest_dir, filename)
                click.echo(f"Exported {filename} to {exported}")
        else:
            click.echo(f"Skipping missing photo: {p.original_filename}")


if __name__ == "__main__":
    export()  # pylint: disable=no-value-for-parameter
