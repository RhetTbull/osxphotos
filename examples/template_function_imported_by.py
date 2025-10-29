"""Example showing how to use a custom function for osxphotos {function} template
Use:  osxphotos export /path/to/export --filename "{function:/path/to/template_function_imported_by.py::name}"
"""

from typing import List, Optional, Union

from osxphotos import PhotoInfo
from osxphotos.phototemplate import RenderOptions


def name(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Get imported by name

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    rows = photo.tables().ZADDITIONALASSETATTRIBUTES.rows_dict()
    if not rows:
        return ""
    return rows[0].get("ZIMPORTEDBYDISPLAYNAME", "")


def bundle_id(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Get imported by bundle ID

    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    rows = photo.tables().ZADDITIONALASSETATTRIBUTES.rows_dict()
    if not rows:
        return ""
    return rows[0].get("ZIMPORTEDBYBUNDLEIDENTIFIER", "")
