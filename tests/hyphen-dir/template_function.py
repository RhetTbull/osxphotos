"""Example showing how to use a custom function for osxphotos {function} template"""

import pathlib

import osxphotos


def foo(photo: osxphotos.PhotoInfo, **kwargs) -> list | str:
    """example function for {function} template

    Args:
        photo: osxphotos.PhotoInfo object
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    return photo.original_filename + "-FOO"
