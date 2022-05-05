"""Get list of valid timezones on macOS"""

from typing import Union

import Foundation
import objc


def known_timezone_names():
    """Get list of valid timezones on macOS"""
    return Foundation.NSTimeZone.knownTimeZoneNames()


def format_offset_time(offset: int) -> str:
    """Format offset time to exiftool format: -04:00"""
    sign = "-" if offset < 0 else "+"
    hours, remainder = divmod(abs(offset), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


class Timezone:
    """Create Timezone object from either name (str) or offset from GMT (int)"""

    def __init__(self, tz: Union[str, int]):
        with objc.autorelease_pool():
            if isinstance(tz, str):
                self.timezone = Foundation.NSTimeZone.timeZoneWithName_(tz)
                self._name = tz
            elif isinstance(tz, int):
                self.timezone = Foundation.NSTimeZone.timeZoneForSecondsFromGMT_(tz)
                self._name = self.timezone.name()
            else:
                raise TypeError("Timezone must be a string or an int")

    @property
    def name(self) -> str:
        return self._name

    @property
    def offset(self) -> int:
        return self.timezone.secondsFromGMT()

    @property
    def offset_str(self) -> str:
        return format_offset_time(self.offset)

    @property
    def abbreviation(self) -> str:
        return self.timezone.abbreviation()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Timezone):
            return self.timezone == other.timezone
        return False
