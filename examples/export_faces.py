""" Export all photos that contain a detected face and draw rectangles around each face
    photos with no persons/detected faces will not be export 

    This shows how to use the FaceInfo class and is useful for validating that FaceInfo is
    correctly handling faces.

    To use this, you'll need to install Pillow:
    python3 -m pip install Pillow
"""

import os

import click
from PIL import Image, ImageDraw

import osxphotos


@click.command()
@click.argument("export-path", type=click.Path(exists=True))
@click.option(
    "--uuid",
    metavar="UUID",
    help="Limit export to optional UUID(s)",
    required=False,
    multiple=True,
)
@click.option(
    "--library-path",
    metavar="PATH",
    help="Path to Photos library, default to last used library",
    default=None,
)
def export(export_path, library_path, uuid):
    """ export photos to export_path and draw faces """
    library_path = os.path.expanduser(library_path) if library_path else None
    if library_path is not None:
        photosdb = osxphotos.PhotosDB(library_path)
    else:
        photosdb = osxphotos.PhotosDB()

    photos = photosdb.photos(uuid=uuid) if uuid else photosdb.photos(movies=False)
    for p in photos:
        if p.person_info and not p.ismissing:
            # has persons and not missing
            if "heic" in p.filename.lower():
                print(f"skipping heic image {p.filename}")
                continue
            print(f"exporting photo {p.original_filename}, uuid = {p.uuid}")
            export = p.export(export_path, p.original_filename, edited=p.hasadjustments)
            if export:
                im = Image.open(export[0])
                draw = ImageDraw.Draw(im)
                for face in p.face_info:
                    coords = face.face_rect()
                    draw.rectangle(coords, width=3)
                    draw.ellipse(get_circle_points(face.center, 3), width=1)
                im.save(export[0])
            else:
                print(f"no photos exported for {p.uuid}")


def get_circle_points(xy, radius):
    """ Returns tuples of (x0, y0), (x1, y1) for a circle centered at x, y with radius

    Arguments:
        xy: tuple of x, y coordinates
        radius: radius of circle to draw

    Returns:
        [(x0, y0), (x1, y1)] for bounding box of circle centered at x, y
    """
    x, y = xy
    x0, y0 = x - radius, y - radius
    x1, y1 = x + radius, y + radius
    return [(x0, y0), (x1, y1)]


if __name__ == "__main__":
    export()  # pylint: disable=no-value-for-parameter
