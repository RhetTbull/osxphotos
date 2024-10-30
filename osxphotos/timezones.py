"""Get list of valid timezones on macOS"""

import datetime
import zoneinfo
from typing import Union

from .platform import is_macos
from .timeutils import timezone_for_offset


def format_offset_time(offset: int) -> str:
    """Format offset time to exiftool format: -04:00"""
    sign = "-" if offset < 0 else "+"
    hours, remainder = divmod(abs(offset), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


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

        def __init__(self, tz: Union[str, int]):
            with objc.autorelease_pool():
                self._from_offset = False
                if isinstance(tz, str):
                    # the NSTimeZone methods return nil if the timezone is invalid
                    self.timezone = Foundation.NSTimeZone.timeZoneWithAbbreviation_(
                        tz
                    ) or Foundation.NSTimeZone.timeZoneWithName_(tz)
                    if not self.timezone:
                        raise ValueError(f"Invalid timezone: {tz}")
                elif isinstance(tz, int):
                    self.timezone = Foundation.NSTimeZone.timeZoneForSecondsFromGMT_(tz)
                    self._from_offset = True
                else:
                    raise TypeError("Timezone must be a string or an int")
                self._name = self.timezone.name()

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

        def tzinfo(self, dt: datetime.datetime) -> zoneinfo.ZoneInfo:
            """Return zoneinfo.ZoneInfo object for the timezone at the given datetime"""
            if not self._from_offset:
                return zoneinfo.ZoneInfo(self.timezone.name())
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
