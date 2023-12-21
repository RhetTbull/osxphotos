"""Determine if a strpdatetime format string contains date and/or time codes

See also: https://github.com/RhetTbull/strpdatetime
"""

from __future__ import annotations

import datetime
import re

from strpdatetime import strpdatetime

# Reference: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
DATE_CODES = "aAwdbBmyYjUWxGuV"
TIME_CODES = "HIpMSfzZX"


def fmt_has_date_time_codes(fmt: str) -> tuple[bool, bool]:
    """Determine if a strpdatetime format string contains date and/or time codes

    Args:
        fmt: strpdatetime format string

    Returns: tuple of (has_date, has_time)
    """
    # has a date code if the pattern matches %[-]?DATE_CODES
    # ignore % if preceded by % (e.g. %%d is not a date code)
    # has a time code if the pattern matches %[-]?TIME_CODES
    # return tuple of (has_date, has_time)

    fmt = fmt.replace("%%", "")  # remove escaped % (e.g. %%d is not a date code)
    has_date = bool(re.search(r"%[-]?[" + DATE_CODES + r"]", fmt))
    has_time = bool(re.search(r"%[-]?[" + TIME_CODES + r"]", fmt))
    return has_date, has_time


def date_str_matches_date_time_codes(date_str: str, fmt: str) -> tuple[bool, bool]:
    """Determine if a date str parsed with strpdatetime contains date and/or time codes

    Args:
        date_str: date string to parse
        fmt: strpdatetime format string

    Returns: tuple of (has_date, has_time)
    """

    fmt = fmt.replace("%%", "")  # remove escaped % (e.g. %%d is not a date code)
    fmt = fmt.replace("%|", "")  # remove escaped |
    fmts = fmt.split("|")
    for f in fmts:
        try:
            # if date_str doesn't match fmt, strpdatetime will raise ValueError
            strpdatetime(date_str, f)
            return fmt_has_date_time_codes(f)
        except ValueError:
            continue
    return False, False
