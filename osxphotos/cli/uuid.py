"""uuid command for osxphotos CLI"""

import click
import photoscript


@click.command(name="uuid")
@click.pass_obj
@click.pass_context
@click.option(
    "--filename",
    "-f",
    required=False,
    is_flag=True,
    default=False,
    help="Include filename of selected photos in output",
)
def uuid(ctx, cli_obj, filename):
    """Print out unique IDs (UUID) of photos selected in Photos

    Prints outs UUIDs in form suitable for --uuid-from-file and --skip-uuid-from-file
    """
    for photo in photoscript.PhotosLibrary().selection:
        if filename:
            print(f"# {photo.filename}")
        print(photo.uuid)
