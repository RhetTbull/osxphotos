""" Example showing how to use a custom template function for osxphotos {function} template
    Example use:  osxphotos query --quiet --print "{function:date_delta.py::months_since(2021-01-01)}"
"""

import datetime
import pathlib
from typing import List, Optional, Union

from osxphotos import PhotoInfo
from osxphotos.datetime_utils import datetime_naive_to_local
from osxphotos.phototemplate import RenderOptions


def years_since(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Return the number of years between the photo date and the date passed as an argument in format YYYY-MM-DD"""

    if not args:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )
    # if args doesn't match the expected format, raise an error
    try:
        date_arg = datetime_naive_to_local(datetime.datetime.strptime(args, "%Y-%m-%d"))
    except ValueError:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )

    return str(_years_since(photo.date, date_arg))


def months_since(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Return the number of months between the photo date and the date passed as an argument in format YYYY-MM-DD"""

    if not args:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )
    # if args doesn't match the expected format, raise an error
    try:
        date_arg = datetime_naive_to_local(datetime.datetime.strptime(args, "%Y-%m-%d"))
    except ValueError:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )

    return str(_months_since(photo.date, date_arg))


def days_since(
    photo: PhotoInfo, options: RenderOptions, args: Optional[str] = None, **kwargs
) -> Union[List, str]:
    """Return the number of days between the photo date and the date passed as an argument in format YYYY-MM-DD"""

    if not args:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )
    # if args doesn't match the expected format, raise an error
    try:
        date_arg = datetime_naive_to_local(datetime.datetime.strptime(args, "%Y-%m-%d"))
    except ValueError:
        raise ValueError(
            "months_since function requires an argument in the form of a date string in the format YYYY-MM-DD"
        )

    return str(_days_since(photo.date, date_arg))


def _months_since(start_date: datetime, end_date: datetime) -> int:
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    years_difference = end_date.year - start_date.year
    months_difference = end_date.month - start_date.month
    return years_difference * 12 + months_difference


def _years_since(start_date: datetime, end_date: datetime) -> int:
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    years_difference = end_date.year - start_date.year
    if (end_date.month, end_date.day) < (start_date.month, start_date.day):
        years_difference -= 1
    return years_difference


def _days_since(start_date: datetime, end_date: datetime) -> int:
    return abs((end_date - start_date).days)
