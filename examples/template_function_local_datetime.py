"""Example showing how to use a custom function for osxphotos {function} template
Use:  osxphotos export /path/to/export --filename "{function:/path/to/template_function_local_datetime.py::example}"
"""

from typing import List, Optional, Union

from osxphotos import PhotoInfo
from osxphotos.datetime_utils import datetime_remove_tz, get_local_tz
from osxphotos.phototemplate import RenderOptions


def local_datetime(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """example function for {function} template; returns a string formatted using the local datetime in format YYYY-MM-DD_HH-MM-SS
    Args:
        photo: osxphotos.PhotoInfo object
        options: osxphotos.phototemplate.RenderOptions object
        args: optional str of arguments passed to template function
        **kwargs: not currently used, placeholder to keep functions compatible with possible changes to {function}

    Returns:
        str or list of str of values that should be substituted for the {function} template
    """

    local_tz = get_local_tz(datetime_remove_tz(photo.date))
    local_dt = photo.date.astimezone(local_tz)
    return local_dt.strftime("%Y-%m-%d_%H-%M-%S")
