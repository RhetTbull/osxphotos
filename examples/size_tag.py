""" Example showing how to use a custom function for osxphotos {function} template

    This function returns a size tag based on the size of the photo

    QVGA for 320x240, VGA for images > 320x240 and ≤ 640x480 and SVGA for > VGA and ≤ 800x600

    If photo / video does not fit any of these categories, the function returns empty str.

    Use:  osxphotos batch-edit --keyword "{function:https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/size_tag.py::size_tag}"

    You may place more than one template function in a single file as each is called by name using the {function:file.py::function_name} format
"""

from __future__ import annotations

import pathlib
from typing import List, Optional, Union

from osxphotos import PhotoInfo
from osxphotos.phototemplate import RenderOptions


def size_tag(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Example showing how to use a custom function for osxphotos {function} template

        This function returns a size tag based on the size of the photo

        QVGA for 320x240, VGA for images > 320x240 and ≤ 640x480 and SVGA for > VGA and ≤ 800x600

        If photo / video does not fit any of these categories, the function returns empty str.

        Use:  osxphotos batch-edit --keyword "{function:https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/size_tag.py::size_tag}"

        You may place more than one template function in a single file as each is called by name using the {function:file.py::function_name} format

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    x, y = sorted([photo.width, photo.height])
    if not x or not y:
        return ""

    if (x, y) == (240, 320):
        return "QVGA"
    elif (240 < x <= 480) and (320 < y <= 640):
        return "VGA"
    elif (480 < x <= 600) and (640 < y <= 800):
        return "SVGA"
    else:
        return ""
