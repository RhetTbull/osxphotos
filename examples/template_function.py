""" Example showing how to use a custom function for osxphotos {function} template 
    Use:  osxphotos export /path/to/export --filename "{function:/path/to/template_function.py::example}"

    You may place more than one template function in a single file as each is called by name using the {function:file.py::function_name} format
"""

import pathlib
from typing import List, Optional, Union

from osxphotos import ExportOptions, PhotoInfo


def example(
    photo: PhotoInfo, options: ExportOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """example function for {function} template; adds suffix of # if photo has adjustments and ! if photo is a favorite

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.ExportOptions object
        args: optional str of arguments passed to template function
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
