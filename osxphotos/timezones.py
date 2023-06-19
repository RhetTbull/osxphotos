"""Get list of valid timezones on macOS"""

from typing import Union

from .platform import is_macos


def format_offset_time(offset: int) -> str:
    """Format offset time to exiftool format: -04:00"""
    sign = "-" if offset < 0 else "+"
    hours, remainder = divmod(abs(offset), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


if is_macos:
    import Foundation
    import objc

    def known_timezone_names():
        """Get list of valid timezones on macOS"""
        return Foundation.NSTimeZone.knownTimeZoneNames()

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

else:
    import zoneinfo
    from datetime import datetime

    def known_timezone_names():
        """Get list of valid timezones"""
        return zoneinfo.available_timezones()

    class Timezone:
        """Create Timezone object from either name (str) or offset from GMT (int)"""

        def __init__(self, tz: Union[str, int]):
            if isinstance(tz, str):
                self.timezone = zoneinfo.ZoneInfo(tz)
                self._name = tz
            elif isinstance(tz, int):
                if tz > 0:
                    name = f"Etc/GMT+{tz // 3600}"
                else:
                    name = f"Etc/GMT-{-tz // 3600}"
                self.timezone = zoneinfo.ZoneInfo(name)
                self._name = self.timezone.key
            else:
                raise TypeError("Timezone must be a string or an int")

        @property
        def name(self) -> str:
            return self._name

        @property
        def offset(self) -> int:
            td = self.timezone.utcoffset(datetime.now())
            assert td
            return int(td.total_seconds())

        @property
        def offset_str(self) -> str:
            return format_offset_time(self.offset)

        @property
        def abbreviation(self) -> str:
            return self.timezone.key

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

        def __eq__(self, other):
            if isinstance(other, Timezone):
                return self.timezone == other.timezone
            return False
