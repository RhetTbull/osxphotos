"""
tzcanon: resolve a canonical IANA timezone from
(naive local datetime, UTC offset seconds, and a timezone name token).

Public API:
    - canonical_timezone(naive_local_dt, offset_seconds_from_gmt, tz_token, require_unique=False) -> str | None
    - candidates_by_abbrev_and_offset(naive_local_dt, offset_seconds_from_gmt, abbr) -> list[str]
    - abbrev_to_canonical_timezone(abbrev) -> str | None

Requires Python 3.10+ (uses PEP 604 unions and zoneinfo).
"""

import re
from datetime import datetime
from functools import cache, lru_cache
from zoneinfo import ZoneInfo, available_timezones

# Cache available_timezones() as it's extremely expensive (filesystem scan)
# This set is static for the lifetime of the process
_AVAILABLE_TIMEZONES: set[str] | None = None

__all__ = [
    "canonical_timezone",
    "candidates_by_abbrev_and_offset",
    "abbrev_to_canonical_timezone",
]


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

# Comprehensive timezone abbreviation lookup table
# For ambiguous abbreviations, the most common/populous timezone is chosen
ABBREV_TO_CANONICAL: dict[str, str] = {
    # UTC/GMT
    "UTC": "Etc/UTC",
    "GMT": "Etc/GMT",
    "Z": "Etc/UTC",
    "WET": "Europe/Lisbon",  # Western European Time
    "WEST": "Europe/Lisbon",  # Western European Summer Time
    # North America - Pacific
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    # North America - Mountain
    "MST": "America/Denver",
    "MDT": "America/Denver",
    # North America - Central
    "CST": "America/Chicago",  # Note: Also China Standard Time - US more common
    "CDT": "America/Chicago",
    # North America - Eastern
    "EST": "America/New_York",
    "EDT": "America/New_York",
    # North America - Atlantic
    "AST": "America/Halifax",  # Note: Also Arabia Standard Time - Atlantic more common
    "ADT": "America/Halifax",
    # North America - Alaska
    "AKST": "America/Anchorage",
    "AKDT": "America/Anchorage",
    # North America - Hawaii
    "HST": "Pacific/Honolulu",
    "HAST": "Pacific/Honolulu",
    "HADT": "Pacific/Honolulu",
    # North America - Other
    "NST": "America/St_Johns",  # Newfoundland Standard Time
    "NDT": "America/St_Johns",  # Newfoundland Daylight Time
    # Europe - UK/Ireland
    "BST": "Europe/London",  # British Summer Time
    "IST": "Asia/Kolkata",  # Note: Ambiguous - India (most populous), also Israel/Ireland
    "GMT": "Etc/GMT",
    # Europe - Central
    "CET": "Europe/Paris",
    "CEST": "Europe/Paris",
    "MEZ": "Europe/Berlin",  # Mitteleuropäische Zeit (German for CET)
    "MESZ": "Europe/Berlin",  # Mitteleuropäische Sommerzeit (German for CEST)
    # Europe - Eastern
    "EET": "Europe/Athens",
    "EEST": "Europe/Athens",
    # Europe - Moscow
    "MSK": "Europe/Moscow",
    "MSD": "Europe/Moscow",
    # Middle East
    "IDT": "Asia/Jerusalem",  # Israel Daylight Time
    "IST": "Asia/Kolkata",  # India Standard Time (most populous)
    "PKT": "Asia/Karachi",  # Pakistan Time
    "AFT": "Asia/Kabul",  # Afghanistan Time
    "IRST": "Asia/Tehran",  # Iran Standard Time
    "IRDT": "Asia/Tehran",  # Iran Daylight Time
    "GST": "Asia/Dubai",  # Gulf Standard Time
    "AST": "America/Halifax",  # Note: Also Arabia Standard Time - choosing Atlantic
    # Asia - East
    "CST": "America/Chicago",  # Note: Also China Standard Time - US more common for photos
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
    "HKT": "Asia/Hong_Kong",
    "SGT": "Asia/Singapore",
    "PHT": "Asia/Manila",  # Philippine Time
    "WIB": "Asia/Jakarta",  # Western Indonesia Time
    "WITA": "Asia/Makassar",  # Central Indonesia Time
    "WIT": "Asia/Jayapura",  # Eastern Indonesia Time
    # Asia - South
    "IST": "Asia/Kolkata",  # India Standard Time
    "NPT": "Asia/Kathmandu",  # Nepal Time
    "BST": "Europe/London",  # Note: Also Bangladesh Standard Time - UK more common
    "BTT": "Asia/Thimphu",  # Bhutan Time
    "MVT": "Indian/Maldives",  # Maldives Time
    # Asia - Southeast
    "ICT": "Asia/Bangkok",  # Indochina Time (Thailand, Vietnam, Cambodia)
    "MMT": "Asia/Yangon",  # Myanmar Time
    # Australia/New Zealand
    "AWST": "Australia/Perth",  # Australian Western Standard Time
    "ACST": "Australia/Adelaide",  # Australian Central Standard Time
    "ACDT": "Australia/Adelaide",  # Australian Central Daylight Time
    "AEST": "Australia/Sydney",  # Australian Eastern Standard Time
    "AEDT": "Australia/Sydney",  # Australian Eastern Daylight Time
    "NZST": "Pacific/Auckland",  # New Zealand Standard Time
    "NZDT": "Pacific/Auckland",  # New Zealand Daylight Time
    # Pacific
    "CHST": "Pacific/Guam",  # Chamorro Standard Time
    "SST": "Pacific/Pago_Pago",  # Samoa Standard Time
    "CHAST": "Pacific/Chatham",  # Chatham Standard Time
    "CHADT": "Pacific/Chatham",  # Chatham Daylight Time
    "FJST": "Pacific/Fiji",  # Fiji Summer Time
    "FJT": "Pacific/Fiji",  # Fiji Time
    "TOT": "Pacific/Tongatapu",  # Tonga Time
    # South America
    "BRT": "America/Sao_Paulo",  # Brasília Time
    "BRST": "America/Sao_Paulo",  # Brasília Summer Time
    "ART": "America/Argentina/Buenos_Aires",  # Argentina Time
    "ARST": "America/Argentina/Buenos_Aires",  # Argentina Summer Time
    "CLT": "America/Santiago",  # Chile Standard Time
    "CLST": "America/Santiago",  # Chile Summer Time
    "PET": "America/Lima",  # Peru Time
    "COT": "America/Bogota",  # Colombia Time
    "VET": "America/Caracas",  # Venezuelan Standard Time
    "GYT": "America/Guyana",  # Guyana Time
    "BOT": "America/La_Paz",  # Bolivia Time
    "ECT": "America/Guayaquil",  # Ecuador Time
    "PYST": "America/Asuncion",  # Paraguay Summer Time
    "PYT": "America/Asuncion",  # Paraguay Time
    "UYT": "America/Montevideo",  # Uruguay Time
    "UYST": "America/Montevideo",  # Uruguay Summer Time
    # Africa
    "CAT": "Africa/Maputo",  # Central Africa Time
    "EAT": "Africa/Nairobi",  # East Africa Time
    "WAT": "Africa/Lagos",  # West Africa Time
    "WAST": "Africa/Lagos",  # West Africa Summer Time
    "SAST": "Africa/Johannesburg",  # South Africa Standard Time
    # Atlantic
    "AZOST": "Atlantic/Azores",  # Azores Summer Time
    "AZOT": "Atlantic/Azores",  # Azores Time
    "CVT": "Atlantic/Cape_Verde",  # Cape Verde Time
    # Other common abbreviations
    "CAT": "Africa/Maputo",  # Central Africa Time
    "SAST": "Africa/Johannesburg",  # South Africa Standard Time
}


@cache
def _parse_offset_str(s: str) -> int | None:
    if not s:
        return None
    t = s.strip().upper()
    if t in {"Z", "UTC", "GMT"}:
        return 0
    # Match GMT±HHMM or GMT±HH:MM format
    m_gmt = re.fullmatch(r"GMT([+-])(\d{2}):?(\d{2})", t)
    if m_gmt:
        sign = 1 if m_gmt.group(1) == "+" else -1
        h = int(m_gmt.group(2))
        mi = int(m_gmt.group(3))
        return sign * (h * 3600 + mi * 60)
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


@cache
def abbrev_to_canonical_timezone(abbrev: str | None) -> str | None:
    """Map a timezone abbreviation to a canonical IANA timezone name.

    This function performs a simple lookup without requiring date/time context.
    For ambiguous abbreviations (e.g., IST, CST, AST), the most common/populous
    timezone is returned.

    Args:
        abbrev: Timezone abbreviation (e.g., "IDT", "PST", "JST")

    Returns:
        Canonical IANA timezone name (e.g., "Asia/Jerusalem", "America/Los_Angeles")
        or None if the abbreviation is not recognized

    Examples:
        >>> abbrev_to_canonical_timezone("IDT")
        'Asia/Jerusalem'
        >>> abbrev_to_canonical_timezone("PST")
        'America/Los_Angeles'
        >>> abbrev_to_canonical_timezone("IST")  # Ambiguous - returns India (most populous)
        'Asia/Kolkata'
        >>> abbrev_to_canonical_timezone("UNKNOWN")
        None

    Note:
        For ambiguous abbreviations:
        - IST: Returns Asia/Kolkata (India) instead of Israel/Ireland
        - CST: Returns America/Chicago (US Central) instead of China
        - AST: Returns America/Halifax (Atlantic) instead of Arabia
        - BST: Returns Europe/London (British) instead of Bangladesh
    """
    if not abbrev:
        return None

    # Normalize to uppercase for lookup
    abbrev_upper = abbrev.strip().upper()

    # First check the lookup table (prefer this over IANA names)
    # Some abbreviations like EST, MST are also valid IANA zones but we want the location-based zones
    if abbrev_upper in ABBREV_TO_CANONICAL:
        return ABBREV_TO_CANONICAL[abbrev_upper]

    # If not in lookup table, check if it's already a valid IANA timezone
    # (e.g., "America/New_York" passed directly)
    if _is_valid_iana(abbrev):
        return "Etc/UTC" if abbrev_upper == "UTC" else abbrev

    return None
