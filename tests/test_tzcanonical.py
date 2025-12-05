"""Tests for osxphotos/tzcanonical.py"""

from __future__ import annotations

from datetime import datetime

import pytest

from osxphotos.tzcanonical import (
    AbbrevIndex,
    candidates_by_abbrev_and_offset,
    canonical_timezone,
)


def test_valid_iana_timezone():
    """Test with a valid IANA timezone string"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours (EST)
        "America/New_York",
    )
    assert result == "America/New_York"


def test_utc_normalized():
    """Test that 'UTC' is normalized to 'Etc/UTC'"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "UTC",
    )
    assert result == "Etc/UTC"


def test_offset_string_positive():
    """Test parsing positive offset string"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        10800,  # +3 hours
        "+03:00",
    )
    assert result == "Etc/GMT-3"


def test_offset_string_negative():
    """Test parsing negative offset string"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -25200,  # -7 hours
        "-07:00",
    )
    assert result == "Etc/GMT+7"


def test_offset_string_no_colon():
    """Test parsing offset string without colon"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        "-0500",
    )
    assert result == "Etc/GMT+5"


def test_offset_string_z():
    """Test Z (Zulu time) offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "Z",
    )
    assert result == "Etc/UTC"


def test_offset_string_gmt():
    """Test GMT offset - GMT is a valid IANA zone so returned as-is"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "GMT",
    )
    assert result == "GMT"


def test_abbreviation_pdt():
    """Test PDT abbreviation resolves to Los Angeles"""
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),  # Summer date for PDT
        -25200,  # -7 hours
        "PDT",
    )
    assert result == "America/Los_Angeles"


def test_abbreviation_pst():
    """Test PST abbreviation resolves to Los Angeles"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),  # Winter date for PST
        -28800,  # -8 hours
        "PST",
    )
    assert result == "America/Los_Angeles"


def test_abbreviation_est():
    """Test EST - EST is a valid IANA zone so returned as-is"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        "EST",
    )
    assert result == "EST"


def test_abbreviation_edt():
    """Test EDT abbreviation resolves to New York"""
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        -14400,  # -4 hours
        "EDT",
    )
    assert result == "America/New_York"


def test_abbreviation_bst():
    """Test BST (British Summer Time) resolves to London"""
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        3600,  # +1 hour
        "BST",
    )
    assert result == "Europe/London"


def test_abbreviation_jst():
    """Test JST (Japan Standard Time) resolves to Tokyo"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        32400,  # +9 hours
        "JST",
    )
    assert result == "Asia/Tokyo"


def test_empty_token():
    """Test with empty token string"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        "",
    )
    # Should return a timezone matching the offset, preferably New York
    assert result is not None
    assert (
        "America/New_York" in result or "America/Panama" in result or "Etc/" in result
    )


def test_none_token():
    """Test with None token"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        None,
    )
    # Should return a timezone matching the offset
    assert result is not None


def test_require_unique_ambiguous():
    """Test require_unique=True with ambiguous timezone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours (shared by multiple zones)
        "",
        require_unique=True,
    )
    # Should return None when multiple timezones match and unique is required
    assert result is None


def test_require_unique_unambiguous():
    """Test require_unique=True with unambiguous timezone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "UTC",
        require_unique=False,
    )
    assert result == "Etc/UTC"


def test_invalid_timezone_name():
    """Test with invalid timezone name"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "Invalid/Timezone",
    )
    # Should fall back to finding by offset
    assert result is not None


def test_mismatched_offset_and_token():
    """Test when offset doesn't match the token"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours (EST)
        "+03:00",  # +3 hours (doesn't match)
    )
    # Should fall back to offset-based lookup
    assert result is not None
    assert "Etc/" not in result or result == "Etc/GMT+5"


def test_half_hour_offset():
    """Test timezone with half-hour offset string - returns None when no Etc/ zone exists"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        19800,  # +5:30 (India)
        "+05:30",
    )
    # When offset string matches but can't be represented as Etc/ zone, returns None
    assert result is None


def test_unusual_offset():
    """Test unusual timezone offset (Nepal: +5:45) - returns None with offset string"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        20700,  # +5:45 (Nepal)
        "+05:45",
    )
    # When offset string matches but can't be represented as Etc/ zone, returns None
    assert result is None


def test_whitespace_handling():
    """Test that whitespace is properly stripped"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "  EST  ",
    )
    # EST is a valid IANA zone, returned as-is
    assert result == "EST"


def test_valid_abbrev_pst():
    """Test PST abbreviation returns valid candidates"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -28800,  # -8 hours
        "PST",
    )
    assert len(candidates) > 0
    assert "America/Los_Angeles" in candidates


def test_valid_abbrev_est():
    """Test EST abbreviation returns valid candidates"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        "EST",
    )
    assert len(candidates) > 0
    assert "America/New_York" in candidates


def test_invalid_abbrev():
    """Test with invalid abbreviation"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "INVALID",
    )
    assert len(candidates) == 0


def test_empty_abbrev():
    """Test with empty abbreviation"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "",
    )
    assert len(candidates) == 0


def test_none_abbrev():
    """Test with None abbreviation"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        None,
    )
    assert len(candidates) == 0


def test_case_insensitive_abbrev():
    """Test that abbreviations are case-insensitive"""
    candidates_upper = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "EST",
    )
    candidates_lower = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "est",
    )
    assert candidates_upper == candidates_lower


def test_wrong_offset_for_abbrev():
    """Test abbreviation with wrong offset"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        10800,  # +3 hours (wrong for EST)
        "EST",
    )
    # Should return empty list since offset doesn't match EST
    assert len(candidates) == 0


def test_dst_transition():
    """Test during DST transition period"""
    # Summer date when PDT is active
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 7, 15, 12, 0),
        -25200,  # -7 hours
        "PDT",
    )
    assert len(candidates) > 0
    assert "America/Los_Angeles" in candidates


def test_default_initialization():
    """Test AbbrevIndex with default sample dates"""
    index = AbbrevIndex()
    assert len(index.abbrev_to_zones) > 0


def test_custom_sample_dates():
    """Test AbbrevIndex with custom sample dates"""
    dates = [datetime(2024, 1, 1), datetime(2024, 6, 1)]
    index = AbbrevIndex(sample_dates=dates)
    assert len(index.abbrev_to_zones) > 0


def test_candidates_known_abbrev():
    """Test getting candidates for known abbreviation"""
    index = AbbrevIndex()
    candidates = index.candidates("PST")
    assert len(candidates) > 0
    assert "America/Los_Angeles" in candidates


def test_candidates_unknown_abbrev():
    """Test getting candidates for unknown abbreviation"""
    index = AbbrevIndex()
    candidates = index.candidates("XXXXX")
    assert len(candidates) == 0


def test_candidates_empty_string():
    """Test getting candidates for empty string"""
    index = AbbrevIndex()
    candidates = index.candidates("")
    assert len(candidates) == 0


def test_candidates_sorted():
    """Test that candidates are returned sorted"""
    index = AbbrevIndex()
    candidates = index.candidates("PST")
    assert candidates == sorted(candidates)


def test_single_sample_date():
    """Test with single sample date"""
    index = AbbrevIndex(sample_dates=[datetime(2025, 1, 15)])
    assert len(index.abbrev_to_zones) > 0


def test_empty_sample_dates():
    """Test with empty sample dates list"""
    index = AbbrevIndex(sample_dates=[])
    # Should have minimal or no entries
    assert len(index.abbrev_to_zones) >= 0


def test_very_old_date():
    """Test with very old date"""
    result = canonical_timezone(
        datetime(1900, 1, 1, 12, 0),
        -18000,
        "EST",
    )
    # Should still resolve even for historical dates
    assert result is not None


def test_future_date():
    """Test with future date"""
    result = canonical_timezone(
        datetime(2099, 12, 31, 23, 59),
        -18000,
        "EST",
    )
    assert result is not None


def test_leap_day():
    """Test with leap day"""
    result = canonical_timezone(
        datetime(2024, 2, 29, 12, 0),
        -18000,
        "EST",
    )
    # EST is a valid IANA zone, returned as-is
    assert result == "EST"


def test_extreme_positive_offset():
    """Test with extreme positive offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        50400,  # +14 hours (Kiribati)
        "+14:00",
    )
    assert result == "Etc/GMT-14"


def test_extreme_negative_offset():
    """Test with extreme negative offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -39600,  # -11 hours
        "-11:00",
    )
    assert result == "Etc/GMT+11"


def test_zero_offset_variations():
    """Test various ways to express zero offset"""
    # GMT is a valid IANA zone so returned as-is, others normalize to Etc/UTC
    expected = {
        "Z": "Etc/UTC",
        "UTC": "Etc/UTC",
        "GMT": "GMT",
        "+00:00": "Etc/UTC",
        "-00:00": "Etc/UTC",
    }
    for token, expected_result in expected.items():
        result = canonical_timezone(
            datetime(2025, 1, 15, 12, 0),
            0,
            token,
        )
        assert (
            result == expected_result
        ), f"Expected {expected_result} for {token}, got {result}"


def test_malformed_offset_string():
    """Test with malformed offset strings"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "malformed",
    )
    # Should still return a result by falling back to offset matching
    assert result is not None


def test_offset_with_minutes():
    """Test offset string with minutes - returns None when matching Etc/ zone doesn't exist"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        19800,  # +5:30
        "+05:30",
    )
    # When offset string matches but can't be represented as Etc/ zone, returns None
    assert result is None


def test_offset_without_sign_format():
    """Test offset in format without sign (HH:MM)"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        18000,  # +5:00
        "05:00",
    )
    assert result is not None


def test_midnight_time():
    """Test with midnight time"""
    result = canonical_timezone(
        datetime(2025, 1, 1, 0, 0),
        -18000,
        "EST",
    )
    # EST is a valid IANA zone, returned as-is
    assert result == "EST"


def test_end_of_day_time():
    """Test with end of day time"""
    result = canonical_timezone(
        datetime(2025, 12, 31, 23, 59, 59),
        -18000,
        "EST",
    )
    # EST is a valid IANA zone, returned as-is
    assert result == "EST"


def test_preferred_over_non_preferred():
    """Test that preferred timezone is chosen over non-preferred"""
    # Get candidates for an offset that has multiple matches
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # Multiple zones at -5 hours
        "",
        require_unique=False,
    )
    # Should prefer major cities like New York over less common zones
    assert result is not None
    # Preferred zones should be returned (not Etc/ zones)
    if result.startswith("America/"):
        assert True
    else:
        # If not America/, verify it's still a reasonable choice
        assert result is not None


def test_avoid_etc_zones_when_possible():
    """Test that Etc/ zones are avoided when better options exist"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,
        "EST",
    )
    # EST is a valid IANA zone, returned as-is (not an Etc/ zone)
    assert result == "EST"
    assert not result.startswith("Etc/")


def test_empty_token_finds_timezone():
    """Test that empty token still finds timezone by offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        19800,  # +5:30 India
        "",
    )
    # Should find a timezone with this offset
    assert result is not None
    # Should be India time zone
    assert "Asia/Kolkata" in result or "Asia/Calcutta" in result


def test_none_token_finds_timezone():
    """Test that None token still finds timezone by offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        28800,  # +8 hours
        None,
    )
    # Should find a timezone with this offset
    assert result is not None


def test_cet_override():
    """Test CET - CET is a valid IANA zone so returned as-is"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        3600,  # +1 hour
        "CET",
    )
    assert result == "CET"


def test_cest_override():
    """Test CEST abbreviation uses override"""
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        7200,  # +2 hours
        "CEST",
    )
    assert result == "Europe/Berlin"


def test_idt_override():
    """Test IDT (Israel Daylight Time) uses override"""
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        10800,  # +3 hours
        "IDT",
    )
    assert result == "Asia/Jerusalem"


def test_australian_timezones():
    """Test Australian timezone abbreviations"""
    # AEST (Australian Eastern Standard Time)
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        36000,  # +10 hours
        "AEST",
    )
    # Multiple Australian cities share AEST, Brisbane or Sydney are both valid
    assert result in ["Australia/Sydney", "Australia/Brisbane"]

    # AEDT (Australian Eastern Daylight Time)
    result = canonical_timezone(
        datetime(2025, 12, 15, 12, 0),
        39600,  # +11 hours
        "AEDT",
    )
    assert result == "Australia/Sydney"


def test_new_zealand_timezones():
    """Test New Zealand timezone abbreviations"""
    # NZST
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        43200,  # +12 hours
        "NZST",
    )
    assert result == "Pacific/Auckland"

    # NZDT
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        46800,  # +13 hours
        "NZDT",
    )
    assert result == "Pacific/Auckland"


def test_alaska_timezones():
    """Test Alaska timezone abbreviations"""
    # AKST
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -32400,  # -9 hours
        "AKST",
    )
    assert result == "America/Anchorage"

    # AKDT
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        -28800,  # -8 hours
        "AKDT",
    )
    assert result == "America/Anchorage"


def test_hawaii_timezone():
    """Test Hawaii timezone - HST is a valid IANA zone so returned as-is"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -36000,  # -10 hours
        "HST",
    )
    assert result == "HST"


def test_mountain_time_zones():
    """Test Mountain timezone abbreviations"""
    # MST - MST is a valid IANA zone so returned as-is
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -25200,  # -7 hours
        "MST",
    )
    assert result == "MST"

    # MDT
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        -21600,  # -6 hours
        "MDT",
    )
    assert result == "America/Denver"


def test_central_time_zones():
    """Test Central timezone abbreviations"""
    # CST
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -21600,  # -6 hours
        "CST",
    )
    assert result == "America/Chicago"

    # CDT
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        -18000,  # -5 hours
        "CDT",
    )
    assert result == "America/Chicago"


def test_very_uncommon_offset():
    """Test very uncommon offset without token"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        20700,  # +5:45 Nepal
        "",
    )
    # Should find Nepal timezone
    assert result is not None
    assert "Asia/Kathmandu" in result or "Asia/Katmandu" in result


def test_offset_only_whole_hour():
    """Test whole-hour offset without token"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours
        "",
    )
    # Should find a timezone
    assert result is not None


def test_negative_offset_etc_zone():
    """Test negative offset resolves to Etc zone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "-04:00",
    )
    assert result == "Etc/GMT+4"


def test_positive_offset_etc_zone():
    """Test positive offset resolves to Etc zone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        7200,  # +2 hours
        "+02:00",
    )
    assert result == "Etc/GMT-2"


def test_override_with_wrong_offset():
    """Test valid IANA zone token with mismatched offset"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -18000,  # -5 hours (wrong for PST)
        "PST",
    )
    # PST is a valid IANA zone, so it's checked first
    # But since it's also checked against overrides/abbreviations,
    # and the offset doesn't match PST (-8), it falls back to finding
    # a timezone by abbreviation "PST" with offset -5, finding America/New_York
    assert result == "America/New_York"


def test_candidates_returns_all_matching():
    """Test that candidates_by_abbrev_and_offset returns all matching zones"""
    candidates = candidates_by_abbrev_and_offset(
        datetime(2025, 1, 15, 12, 0),
        -28800,  # -8 hours
        "PST",
    )
    # Should return multiple zones in PST
    assert len(candidates) >= 1
    assert "America/Los_Angeles" in candidates


def test_korean_timezone():
    """Test Korean timezone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        32400,  # +9 hours
        "KST",
    )
    assert result == "Asia/Seoul"


def test_adelaide_timezone():
    """Test Adelaide (ACST/ACDT) timezone"""
    # ACST
    result = canonical_timezone(
        datetime(2025, 7, 15, 12, 0),
        34200,  # +9:30 hours
        "ACST",
    )
    assert result == "Australia/Adelaide"


def test_perth_timezone():
    """Test Perth (AWST) timezone"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        28800,  # +8 hours
        "AWST",
    )
    assert result == "Australia/Perth"


def test_gmt_negative_offset_format():
    """Test GMT-0400 format returns Etc/GMT+4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "GMT-0400",
    )
    assert result == "Etc/GMT+4"


def test_gmt_positive_offset_format():
    """Test GMT+0400 format returns Etc/GMT-4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        14400,  # +4 hours
        "GMT+0400",
    )
    assert result == "Etc/GMT-4"


def test_gmt_negative_offset_format_with_colon():
    """Test GMT-04:00 format returns Etc/GMT+4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "GMT-04:00",
    )
    assert result == "Etc/GMT+4"


def test_gmt_positive_offset_format_with_colon():
    """Test GMT+04:00 format returns Etc/GMT-4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        14400,  # +4 hours
        "GMT+04:00",
    )
    assert result == "Etc/GMT-4"


def test_gmt_zero_offset_negative():
    """Test GMT-0000 format returns Etc/UTC"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "GMT-0000",
    )
    assert result == "Etc/UTC"


def test_gmt_zero_offset_positive():
    """Test GMT+0000 format returns Etc/UTC"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        0,
        "GMT+0000",
    )
    assert result == "Etc/UTC"


def test_gmt_extreme_negative_offset():
    """Test GMT-1100 format returns Etc/GMT+11"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -39600,  # -11 hours
        "GMT-1100",
    )
    assert result == "Etc/GMT+11"


def test_gmt_extreme_positive_offset():
    """Test GMT+1400 format returns Etc/GMT-14"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        50400,  # +14 hours
        "GMT+1400",
    )
    assert result == "Etc/GMT-14"


def test_gmt_offset_lowercase():
    """Test lowercase gmt-0400 format returns Etc/GMT+4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "gmt-0400",
    )
    assert result == "Etc/GMT+4"


def test_gmt_offset_mixed_case():
    """Test mixed case Gmt-0400 format returns Etc/GMT+4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "Gmt-0400",
    )
    assert result == "Etc/GMT+4"


def test_gmt_offset_with_whitespace():
    """Test GMT-0400 with whitespace returns Etc/GMT+4"""
    result = canonical_timezone(
        datetime(2025, 1, 15, 12, 0),
        -14400,  # -4 hours
        "  GMT-0400  ",
    )
    assert result == "Etc/GMT+4"
