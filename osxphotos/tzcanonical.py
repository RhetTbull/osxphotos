"""
tzcanon: resolve a canonical IANA timezone from
(naive local datetime, UTC offset seconds, and a timezone name token).

Public API:
    - canonical_timezone(naive_local_dt, offset_seconds_from_gmt, tz_token, require_unique=False) -> str | None
    - candidates_by_abbrev_and_offset(naive_local_dt, offset_seconds_from_gmt, abbr) -> list[str]

Requires Python 3.10+ (uses PEP 604 unions and zoneinfo).
"""

import re
from datetime import datetime
from functools import cache, lru_cache
from zoneinfo import ZoneInfo, available_timezones

# Cache available_timezones() as it's extremely expensive (filesystem scan)
# This set is static for the lifetime of the process
_AVAILABLE_TIMEZONES: set[str] | None = None


def _get_available_timezones() -> set[str]:
    """Get cached set of available timezones.

    available_timezones() scans the filesystem and is extremely expensive.
    Cache it once for the lifetime of the process.
    """
    global _AVAILABLE_TIMEZONES
    if _AVAILABLE_TIMEZONES is None:
        _AVAILABLE_TIMEZONES = available_timezones()
    return _AVAILABLE_TIMEZONES


def _etc_from_offset_seconds(offset_seconds: int) -> str | None:
    """
    Map a whole-hour UTC offset (seconds) to an IANA Etc/ zone.
    Note: Etc/GMT sign is inverted per IANA convention:
      UTC+3  -> "Etc/GMT-3"
      UTC-7  -> "Etc/GMT+7"
    Returns None if offset isn't a whole number of hours or zone not present.
    """
    if offset_seconds % 3600 != 0:
        return None
    hours = offset_seconds // 3600
    if hours == 0:
        return "Etc/UTC"
    # invert sign for Etc naming
    sign = "-" if hours > 0 else "+"
    name = f"Etc/GMT{sign}{abs(hours)}"
    return name if name in _get_available_timezones() else None


TZ_OVERRIDES: dict[str, str | None] = {
    "IDT": "Asia/Jerusalem",
    "BST": "Europe/London",
    "CET": "Europe/Berlin",
    "CEST": "Europe/Berlin",
    "PDT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "MDT": "America/Denver",
    "MST": "America/Denver",
    "CDT": "America/Chicago",
    "CST": "America/Chicago",
    "EDT": "America/New_York",
    "EST": "America/New_York",
    "AKDT": "America/Anchorage",
    "AKST": "America/Anchorage",
    "HST": "Pacific/Honolulu",
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "ACST": "Australia/Adelaide",
    "ACDT": "Australia/Adelaide",
    "AWST": "Australia/Perth",
    "NZDT": "Pacific/Auckland",
    "NZST": "Pacific/Auckland",
    "UTC": "Etc/UTC",
    "GMT": "Etc/GMT",
}


@cache
def _parse_offset_str(s: str) -> int | None:
    if not s:
        return None
    t = s.strip().upper()
    if t in {"Z", "UTC", "GMT"}:
        return 0
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", t)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        h = int(m.group(2))
        mi = int(m.group(3))
        return sign * (h * 3600 + mi * 60)
    m2 = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if m2:
        h = int(m2.group(1))
        mi = int(m2.group(2))
        return h * 3600 + mi * 60
    return None


@cache
def _get_zoneinfo_cached(tzname: str) -> ZoneInfo | None:
    """Cache ZoneInfo object creation to avoid repeated parsing."""
    try:
        return ZoneInfo(tzname)
    except Exception:
        return None


@cache
def _get_offset_for_zone(
    tzname: str, year: int, month: int, day: int, hour: int, minute: int
) -> int | None:
    """Cache UTC offset calculation for a specific timezone and datetime.

    Args:
        tzname: IANA timezone name
        year, month, day, hour, minute: datetime components

    Returns:
        UTC offset in seconds, or None if calculation fails
    """
    zi = _get_zoneinfo_cached(tzname)
    if zi is None:
        return None
    try:
        dt = datetime(year, month, day, hour, minute)
        utcoff = dt.replace(tzinfo=zi).utcoffset()
        return int(utcoff.total_seconds()) if utcoff is not None else None
    except Exception:
        return None


class AbbrevIndex:
    def __init__(self, sample_dates: list[datetime] | None = None):
        if sample_dates is None:
            sample_dates = [datetime(2025, 1, 15), datetime(2025, 7, 15)]
        self.abbrev_to_zones: dict[str, set[str]] = {}
        tzs = _get_available_timezones()
        for dt in sample_dates:
            for tzname in tzs:
                try:
                    # Use cached ZoneInfo lookup
                    zi = _get_zoneinfo_cached(tzname)
                    if zi is None:
                        continue
                    abbr = zi.tzname(dt)
                except Exception:
                    continue
                if not abbr:
                    continue
                self.abbrev_to_zones.setdefault(abbr, set()).add(tzname)

    def candidates(self, abbr: str) -> list[str]:
        return sorted(self.abbrev_to_zones.get(abbr, set()))


_ABBREV_INDEX = AbbrevIndex()


def _is_valid_iana(name: str) -> bool:
    """Check if a string is a valid IANA timezone name (cached)."""
    return _get_zoneinfo_cached(name) is not None


def _filter_by_offset(
    local_dt: datetime, offset_seconds: int, zones: list[str]
) -> list[str]:
    """Filter timezone list to those matching the given offset at the given datetime.

    This function is heavily optimized with caching since it's called frequently.
    """
    out: list[str] = []
    target_offset = int(offset_seconds)
    # Use cached offset lookup to avoid repeated ZoneInfo creation
    for tzname in zones:
        cached_offset = _get_offset_for_zone(
            tzname,
            local_dt.year,
            local_dt.month,
            local_dt.day,
            local_dt.hour,
            local_dt.minute,
        )
        if cached_offset is not None and cached_offset == target_offset:
            out.append(tzname)
    return out


def _rank_preferred(zones: list[str]) -> list[str]:
    if not zones:
        return zones
    PREFERRED: set[str] = {
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
        "America/Toronto",
        "America/Vancouver",
        "America/Mexico_City",
        "Europe/London",
        "Europe/Dublin",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Rome",
        "Europe/Madrid",
        "Europe/Amsterdam",
        "Europe/Brussels",
        "Europe/Warsaw",
        "Europe/Athens",
        "Europe/Moscow",
        "Asia/Jerusalem",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Asia/Shanghai",
        "Asia/Hong_Kong",
        "Asia/Singapore",
        "Asia/Kolkata",
        "Australia/Sydney",
        "Australia/Melbourne",
        "Australia/Perth",
        "Pacific/Auckland",
    }

    def score(z: str) -> tuple[int, int, str]:
        is_pref = 0 if z in PREFERRED else 1
        is_bad = 1 if z.startswith("Etc/") or z.startswith("posix/") else 0
        return (is_pref, is_bad, z)

    return sorted(zones, key=score)


def candidates_by_abbrev_and_offset(
    naive_dt: datetime,
    offset_seconds_from_gmt: int,
    abbr: str,
) -> list[str]:
    abbr = (abbr or "").upper()
    cand = _ABBREV_INDEX.candidates(abbr)
    if not cand:
        return []
    return _filter_by_offset(naive_dt, offset_seconds_from_gmt, cand)


@lru_cache(maxsize=8192)
def _canonical_timezone_cached(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    offset_seconds_from_gmt: int,
    tz_token: str,
    require_unique: bool,
) -> str | None:
    """Cached implementation of canonical_timezone.

    Uses datetime components as separate parameters to make the function hashable.
    Note: seconds omitted because timezone rules operate at minute precision.
    """
    # Seconds don't affect timezone resolution, so we omit them for better cache hits
    naive_dt = datetime(year, month, day, hour, minute)
    token = tz_token.strip()

    # Fast path: if token is a valid IANA timezone, return it
    # This trusts explicit IANA names without validation
    if token and _is_valid_iana(token):
        return "Etc/UTC" if token == "UTC" else token

    # Fast path: for whole-hour offsets with no token, try Etc/GMT zones first
    # But skip this if require_unique is True, as other zones might also match
    if not token and not require_unique:
        etc = _etc_from_offset_seconds(offset_seconds_from_gmt)
        if etc:
            return etc

    parsed = _parse_offset_str(token) if token else None
    if parsed is not None and parsed == offset_seconds_from_gmt:
        etc = _etc_from_offset_seconds(parsed)
        return etc

    key = token.upper()
    if key in TZ_OVERRIDES and TZ_OVERRIDES[key]:
        cand = TZ_OVERRIDES[key]
        matched = (
            _filter_by_offset(naive_dt, offset_seconds_from_gmt, [cand]) if cand else []
        )
        if matched:
            return matched[0]

    if token:
        cand = candidates_by_abbrev_and_offset(naive_dt, offset_seconds_from_gmt, token)
        if len(cand) == 1:
            return cand[0]
        if len(cand) > 1:
            if require_unique:
                return None
            return _rank_preferred(cand)[0]

    # Last resort: search all timezones (expensive even with caching)
    # Use cached set to avoid filesystem scan
    all_match = _filter_by_offset(
        naive_dt, offset_seconds_from_gmt, list(_get_available_timezones())
    )
    if not all_match:
        return None
    if len(all_match) == 1:
        return all_match[0]
    if require_unique:
        return None
    return _rank_preferred(all_match)[0]


def canonical_timezone(
    naive_dt: datetime,
    offset_seconds_from_gmt: int,
    tz_token: str | None,
    require_unique: bool = False,
) -> str | None:
    """Return canonical timezone name for given datetime, offset, and token.

    Args:
        naive_dt: datetime object without timezone information
        offset_seconds_from_gmt: offset in seconds from GMT
        tz_token: timezone token
        require_unique: require unique timezone

    Returns:
        Canonical timezone name or None if no match found
    """
    # Delegate to cached implementation (seconds omitted for better cache hit rate)
    return _canonical_timezone_cached(
        naive_dt.year,
        naive_dt.month,
        naive_dt.day,
        naive_dt.hour,
        naive_dt.minute,
        offset_seconds_from_gmt,
        tz_token or "",
        require_unique,
    )
