""" Example showing how to use a custom function for osxphotos {function} template with the `osxphotos import` command 
    Use:  osxphotos import /path/to/import/*.jpg --album "{function:/path/to/template_function_import.py::example}"

    You may place more than one template function in a single file as each is called by name using the {function:file.py::function_name} format
"""

import pathlib
from typing import List, Optional, Union


def example(
    filepath: pathlib.Path, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """example function for {function} template for use with `osxphotos import`

    This example parses filenames in format album_img_123.jpg and returns the album name

    Args:
        filepath: pathlib.Path object of file being imported
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}
    Returns:
        str or list of str of values that should be substituted for the {function} template
    """
    filename = filepath.stem
    fields = filename.split("_")
    return fields[0] if len(fields) > 1 else ""
