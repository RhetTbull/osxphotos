"""Get list of valid timezones on macOS"""

import datetime
import re
import zoneinfo
from datetime import timedelta, timezone
from typing import Union

from .platform import is_macos
from .timeutils import timezone_for_offset

VALID_ETC_TIMEZONES = {
    "Etc/GMT",
    "Etc/GMT+0",
    "Etc/GMT+1",
    "Etc/GMT+2",
    "Etc/GMT+3",
    "Etc/GMT+4",
    "Etc/GMT+5",
    "Etc/GMT+6",
    "Etc/GMT+7",
    "Etc/GMT+8",
    "Etc/GMT+9",
    "Etc/GMT+10",
    "Etc/GMT+11",
    "Etc/GMT+12",
    "Etc/GMT-0",
    "Etc/GMT-1",
    "Etc/GMT-2",
    "Etc/GMT-3",
    "Etc/GMT-4",
    "Etc/GMT-5",
    "Etc/GMT-6",
    "Etc/GMT-7",
    "Etc/GMT-8",
    "Etc/GMT-9",
    "Etc/GMT-10",
    "Etc/GMT-11",
    "Etc/GMT-12",
    "Etc/GMT-13",
    "Etc/GMT-14",
    "Etc/GMT0",
    "Etc/UTC",
    "Etc/UCT",
    "Etc/Zulu",
    "Etc/Universal",
    "Etc/Greenwich",
}


def format_offset_time(offset: int) -> str:
    """Format offset time to exiftool format: -04:00"""
    sign = "-" if offset < 0 else "+"
    hours, remainder = divmod(abs(offset), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def convert_offset_timezone_to_etc(tz_string: str):
    """
    Convert a timezone string like 'GMT-0800', 'UTC+0500', etc. to matching 'Etc/GMT±X' string if possible

    Args:
        tz_string (str): Timezone string to convert

    Returns:
        str: 'Etc/GMT±X' string

    Raises:
        ValueError: on invalid format or invalid offset
    """
    match = re.fullmatch(
        r"(?:GMT|UTC)?([+-])(\d{2})(\d{2})", tz_string.strip(), re.IGNORECASE
    )
    if not match:
        raise ValueError(
            f"Invalid timezone format: '{tz_string}'. Expected 'GMT±HHMM' or 'UTC±HHMM'."
        )

    sign, hh, mm = match.groups()
    hours = int(hh)
    minutes = int(mm)

    if hours > 14 or minutes >= 60:
        raise ValueError(f"Invalid offset: hours={hours}, minutes={minutes}")

    offset_minutes = hours * 60 + minutes
    total_offset = offset_minutes if sign == "+" else -offset_minutes

    # Reverse sign for POSIX-style Etc/GMT±X
    posix_hours = -total_offset // 60
    if (
        minutes == 0
        and f"Etc/GMT{posix_hours:+}".replace("+", "+").replace("-0", "-0")
        in VALID_ETC_TIMEZONES
    ):
        return (
            f"Etc/GMT{posix_hours:+}".replace("+0", "+0")
            .replace("-0", "-0")
            .replace("+", "+")
            .replace("-", "-")
        )

    raise ValueError(f"Invalid timezone offset: {total_offset} minutes")


class Timezone:
    """Create Timezone object from either name (str) or offset from GMT (int)"""

    # this is a dummy class to allow use of Timezone in param_types.py
    def __init__(self, tz: Union[str, int]):
        pass


if is_macos:
    import Foundation
    import objc

    def known_timezone_names() -> list[str]:
        """Get list of valid timezones on macOS"""
        # sort by shortest length then alphabetically
        timezones = list(Foundation.NSTimeZone.knownTimeZoneNames())
        return sorted(timezones, key=lambda x: (len(x), x))

    class Timezone:
        """Create Timezone object from either name (str) or offset from GMT (int)"""

        def __init__(self, tz: Union[str, int, float]):
            with objc.autorelease_pool():
                self._from_offset = False
                if isinstance(tz, str):
                    # the NSTimeZone methods return nil if the timezone is invalid
                    self.timezone = Foundation.NSTimeZone.timeZoneWithAbbreviation_(
                        tz
                    ) or Foundation.NSTimeZone.timeZoneWithName_(tz)
                    if not self.timezone:
                        raise ValueError(f"Invalid timezone: {tz}")
                elif isinstance(tz, (int, float)):
                    self.timezone = Foundation.NSTimeZone.timeZoneForSecondsFromGMT_(
                        int(tz)
                    )
                    self._from_offset = True
                else:
                    raise TypeError("Timezone must be a string or an int")
                self._name = self.timezone.name()

        @property
        def name(self) -> str:
            return str(self._name)

        @property
        def offset(self) -> int:
            return int(self.timezone.secondsFromGMT())

        @property
        def offset_str(self) -> str:
            return format_offset_time(self.offset)

        @property
        def abbreviation(self) -> str:
            return str(self.timezone.abbreviation())

        def offset_for_date(self, dt: datetime.datetime) -> int:
            return int(self.timezone.secondsFromGMTForDate_(dt))

        def offset_str_for_date(self, dt: datetime.datetime) -> str:
            return format_offset_time(self.offset_for_date(dt))

        def tzinfo(self, dt: datetime.datetime) -> zoneinfo.ZoneInfo:
            """Return zoneinfo.ZoneInfo object for the timezone at the given datetime"""
            if not self._from_offset:
                try:
                    return zoneinfo.ZoneInfo(self.name)
                except zoneinfo.ZoneInfoNotFoundError:
                    pass
            try:  # try to get timezone from offset
                tz_name = timezone_for_offset(self.offset_str, dt)
                return zoneinfo.ZoneInfo(tz_name)
            except Exception as e:
                raise ValueError(
                    f"Could not get ZoneInfo for {dt} with offset {self.offset}"
                ) from e

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

        def __eq__(self, other):
            if isinstance(other, Timezone):
                return self.timezone == other.timezone
            return False


# else:

#     def known_timezone_names() -> list[str]:
#         """Get list of valid timezones"""
#         return sorted(list(zoneinfo.available_timezones()))

#     class Timezone:
#         """Create Timezone object from either name (str) or offset from GMT (int)"""

#         def __init__(self, tz: Union[str, int]):
#             if isinstance(tz, str):
#                 try:
#                     self.timezone = zoneinfo.ZoneInfo(tz)
#                 except Exception as e:
#                     raise ValueError(f"Invalid timezone: {tz}") from e
#                 self._name = tz
#             elif isinstance(tz, int):
#                 if tz > 0:
#                     name = f"Etc/GMT+{tz // 3600}"
#                 else:
#                     name = f"Etc/GMT-{-tz // 3600}"
#                 self.timezone = zoneinfo.ZoneInfo(name)
#                 self._name = self.timezone.key
#             else:
#                 raise TypeError("Timezone must be a string or an int")

#         @property
#         def name(self) -> str:
#             return self._name

#         @property
#         def offset(self) -> int:
#             td = self.timezone.utcoffset(datetime.datetime.now())
#             assert td
#             return int(td.total_seconds())

#         @property
#         def offset_str(self) -> str:
#             return format_offset_time(self.offset)

#         @property
#         def abbreviation(self) -> str:
#             return self.timezone.key

#         @property
#         def tzinfo(self) -> zoneinfo.ZoneInfo:
#             """Return zoneinfo.ZoneInfo object"""
#             return self.timezone

#         def __str__(self):
#             return self.name

#         def __repr__(self):
#             return self.name

#         def __eq__(self, other):
#             if isinstance(other, Timezone):
#                 return self.timezone == other.timezone
#             return False
