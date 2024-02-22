""" Example showing how to use a custom function for osxphotos {function} template
    to allow use of the `{album_seq}` template in the `--filename` option.

    Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_sequence.py::album_seq}"
    
    To specify a default album name if photo is not in any album, use the following:
    Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_sequence.py::album_seq(Default)}"

    otherwise, the default album name will be "None"

    To use a different starting sequence number, use the following:
    Use:  osxphotos export /path/to/export --filename "{function:/path/to/album_sequence.py::album_seq(Default,1)}"
    where 1 is the starting sequence number

    If providing the starting sequence number, you must also provide the default album name, even if it is "None"

    In osxphotos you can use the `{album_seq}` template to get the order of a photo in an album
    but this only works if you also use `{album}` or `{folder_album}` as the `--directory` template.

    This custom template creates a filename that includes both the album name and the sequence number.
"""

from __future__ import annotations

from osxphotos import PhotoInfo
from osxphotos.phototemplate import RenderOptions, _get_album_by_name


def album_seq(
    photo: PhotoInfo, options: RenderOptions, args: str | None = None, **kwargs
) -> list[str] | str:
    """Example function for {function} template; returns value in form `YYYY-MM-DD-Album-Seq` or `YYYY-MM-DD-None-ID` if no album

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    # default album name if photo is not in any album
    default = "None"
    # starting sequence number
    start = 0

    # parse args if provided, for default album name and starting sequence number
    if args:
        arg_values = args.split(",")
        if len(arg_values) > 2:
            raise ValueError("album_seq: Too many arguments; must be 0 or 1 argument")
        if len(arg_values) == 1:
            default = arg_values[0]
            start = 0
        else:
            default = arg_values[0]
            start = int(arg_values[1])

    albums = sorted(photo.burst_albums) if photo.burst else sorted(photo.albums)
    if not albums:
        rendered, _ = photo.render_template("{created.date}-" + default + "-{id}")
        return rendered

    values = []
    for album in albums:
        rendered, _ = photo.render_template("{created.date}-")
        value = rendered[0]
        album_info = _get_album_by_name(photo, album)
        seq = album_info.photo_index(photo) if album_info else 0
        seq += start
        value += f"{album}-{seq}"
        values.append(value)
    return values
