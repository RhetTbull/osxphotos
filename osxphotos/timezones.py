"""Get list of valid timezones on macOS"""

import datetime
import re
import zoneinfo
from functools import cache
from math import floor
from typing import Union

from .platform import is_macos
from .timeutils import timezone_for_offset
from .tzcanonical import abbrev_to_canonical_timezone

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


def match_etc_tzname(tz_string: str) -> tuple[str, str] | bool:
    """Check if the timezone string matches the '±X' tzname format.

    Args:
        tz_string: Timezone string to match

    Returns:
        tuple[str, int]: Tuple of sign and offset in hoursif match, False otherwise.
    """
    if match := re.fullmatch(r"([+-])(\d{1,2})", tz_string.strip(), re.IGNORECASE):
        sign, hh = match.groups()
        return sign, int(hh)
    return False


def etc_tzname_to_etc(tz_string: str) -> str:
    """Convert the tzname for a 'Etc/GMT±X' timezone back to 'Etc/GMT±X'
    Args:
        tz_string (str): Timezone string to convert

    Returns:
        str: 'Etc/GMT±X' string

    Raises:
        ValueError: If the timezone format is invalid or the offset is not a valid integer.

    Note:
        'Etc/GMT±X' timezones, tzname() yields ±x where x is 2 digit offset, e.g. 'Etc/GMT-8' -> '+08'
    """
    match = match_etc_tzname(tz_string)
    if not match:
        raise ValueError(f"Invalid timezone format: '{tz_string}'")
    sign, hh = match
    if hh < 0 or hh > 23:
        raise ValueError(
            f"Invalid timezone offset: '{hh}'. Expected integer between 0 and 23."
        )
    if hh == 0:
        return "Etc/GMT"
    sign = "+" if sign == "-" else "-"
    return f"Etc/GMT{sign}{hh}"


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

    @cache
    def known_timezone_names() -> list[str]:
        """Get list of valid timezones on macOS"""
        # sort by shortest length then alphabetically
        timezones = list(Foundation.NSTimeZone.knownTimeZoneNames())
        return sorted(timezones, key=lambda x: (len(x), x))

    def ns_timezone_with_name(name: str) -> Foundation.NSTimeZone | None:
        """Create NSTimeZone object from name or abbreviation"""
        return Foundation.NSTimeZone.timeZoneWithAbbreviation_(
            name
        ) or Foundation.NSTimeZone.timeZoneWithName_(name)

    class Timezone:
        """Create Timezone object from either name (str) or offset from GMT (int)"""

        def __init__(self, tz: Union[str, int, float]):
            with objc.autorelease_pool():
                self._from_offset = False
                if isinstance(tz, str):
                    # the NSTimeZone methods return nil if the timezone is invalid
                    self.timezone = ns_timezone_with_name(tz)
                    if not self.timezone:
                        # try the canonical name (this is a fallback best guess; I've seen Photos databases with invalid timezones like "IDT")
                        if canonical_timezone := abbrev_to_canonical_timezone(
                            tz.upper()
                        ):
                            self.timezone = ns_timezone_with_name(canonical_timezone)
                        elif match_etc_tzname(tz):
                            self.timezone = ns_timezone_with_name(etc_tzname_to_etc(tz))
                        if not self.timezone:
                            raise ValueError(f"Invalid timezone: {tz}")
                elif isinstance(tz, (int, float)):
                    self.timezone = Foundation.NSTimeZone.timeZoneForSecondsFromGMT_(
                        int(tz)
                    )
                    if not self.timezone:
                        raise ValueError(f"Invalid timezone offset: {tz}")
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

else:

    @cache
    def known_timezone_names() -> list[str]:
        """Get list of valid timezones"""
        return sorted(list(zoneinfo.available_timezones()))

    class Timezone:
        """Create Timezone object from either name (str) or offset from GMT (int)"""

        def __init__(self, tz: Union[str, int, float]):
            if isinstance(tz, str):
                try:
                    self.timezone = zoneinfo.ZoneInfo(tz)
                    self._name = tz
                except Exception as e:
                    if tz_canonical := abbrev_to_canonical_timezone(tz):
                        try:
                            self.timezone = zoneinfo.ZoneInfo(tz_canonical)
                            self._name = tz_canonical
                        except Exception as e:
                            if match_etc_tzname(tz):
                                tz_name = etc_tzname_to_etc(tz)
                                self.timezone = ns_timezone_with_name(tz_name)
                                self._name = tz_name
                            else:
                                raise ValueError(f"Invalid timezone: {tz}") from e
                    else:
                        raise ValueError(f"Invalid timezone: {tz}") from e
            elif isinstance(tz, (int, float)):
                if isinstance(tz, float):
                    tz: int = floor(tz)
                # POSIX convention for Etc/GMT±X: the sign is inverted from intuitive meaning
                # Positive offset (east of GMT) uses GMT- prefix
                # Negative offset (west of GMT) uses GMT+ prefix
                hours = tz // 3600
                if hours == 0:
                    name = "Etc/GMT"
                elif hours > 0:
                    name = f"Etc/GMT-{hours}"
                else:
                    name = f"Etc/GMT+{-hours}"
                self.timezone = zoneinfo.ZoneInfo(name)
                self._name = self.timezone.key
            else:
                raise TypeError("Timezone must be a string or an int")

        @property
        def name(self) -> str:
            return self._name

        @property
        def offset(self) -> int:
            td = self.timezone.utcoffset(datetime.datetime.now())
            return int(td.total_seconds())

        @property
        def offset_str(self) -> str:
            return format_offset_time(self.offset)

        @property
        def abbreviation(self) -> str:
            return self.timezone.key

        def offset_for_date(self, dt: datetime.datetime) -> int:
            dtz = dt.replace(tzinfo=self.timezone)
            return int(dtz.utcoffset().total_seconds())

        def offset_str_for_date(self, dt: datetime.datetime) -> str:
            return format_offset_time(self.offset_for_date(dt))

        def tzinfo(self, dt: datetime.datetime) -> zoneinfo.ZoneInfo:
            """Return zoneinfo.ZoneInfo object for the timezone at the given datetime"""
            if dt.tzinfo is None:
                aware_dt = dt.replace(tzinfo=self.timezone)
            else:
                aware_dt = dt.astimezone(self.timezone)
            return aware_dt.tzinfo

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

        def __eq__(self, other):
            if isinstance(other, Timezone):
                return self.timezone == other.timezone
            return False
