""" Example showing how to use a custom function for osxphotos {function} template """

import pathlib
from typing import List, Union

import osxphotos


def example(photo: osxphotos.PhotoInfo, **kwargs) -> Union[List, str]:
    """ example function for {function} template

    Args:
        photo: osxphotos.PhotoInfo object
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    filename = pathlib.Path(photo.original_filename).stem
    if photo.hasadjustments:
        filename += "#"
    if photo.favorite:
        filename += "!"

    return filename
