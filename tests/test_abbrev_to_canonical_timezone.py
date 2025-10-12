"""Tests for abbrev_to_canonical_timezone function"""

from __future__ import annotations

import pytest

from osxphotos.tzcanonical import abbrev_to_canonical_timezone


def test_idt_to_jerusalem():
    """Test IDT abbreviation maps to Asia/Jerusalem"""
    assert abbrev_to_canonical_timezone("IDT") == "Asia/Jerusalem"


def test_pst_to_los_angeles():
    """Test PST abbreviation maps to America/Los_Angeles"""
    assert abbrev_to_canonical_timezone("PST") == "America/Los_Angeles"


def test_pdt_to_los_angeles():
    """Test PDT abbreviation maps to America/Los_Angeles"""
    assert abbrev_to_canonical_timezone("PDT") == "America/Los_Angeles"


def test_est_to_new_york():
    """Test EST abbreviation maps to America/New_York"""
    assert abbrev_to_canonical_timezone("EST") == "America/New_York"


def test_edt_to_new_york():
    """Test EDT abbreviation maps to America/New_York"""
    assert abbrev_to_canonical_timezone("EDT") == "America/New_York"


def test_jst_to_tokyo():
    """Test JST abbreviation maps to Asia/Tokyo"""
    assert abbrev_to_canonical_timezone("JST") == "Asia/Tokyo"


def test_ist_to_india():
    """Test IST abbreviation maps to India (most populous) not Israel/Ireland"""
    assert abbrev_to_canonical_timezone("IST") == "Asia/Kolkata"


def test_cst_to_chicago():
    """Test CST abbreviation maps to America/Chicago (US) not China"""
    assert abbrev_to_canonical_timezone("CST") == "America/Chicago"


def test_ast_to_halifax():
    """Test AST abbreviation maps to America/Halifax (Atlantic) not Arabia"""
    assert abbrev_to_canonical_timezone("AST") == "America/Halifax"


def test_bst_to_london():
    """Test BST abbreviation maps to Europe/London (British) not Bangladesh"""
    assert abbrev_to_canonical_timezone("BST") == "Europe/London"


def test_utc_normalized():
    """Test UTC maps to Etc/UTC"""
    assert abbrev_to_canonical_timezone("UTC") == "Etc/UTC"


def test_gmt_to_gmt():
    """Test GMT maps to Etc/GMT"""
    assert abbrev_to_canonical_timezone("GMT") == "Etc/GMT"


def test_z_to_utc():
    """Test Z (Zulu time) maps to Etc/UTC"""
    assert abbrev_to_canonical_timezone("Z") == "Etc/UTC"


def test_aest_to_sydney():
    """Test AEST abbreviation maps to Australia/Sydney"""
    assert abbrev_to_canonical_timezone("AEST") == "Australia/Sydney"


def test_aedt_to_sydney():
    """Test AEDT abbreviation maps to Australia/Sydney"""
    assert abbrev_to_canonical_timezone("AEDT") == "Australia/Sydney"


def test_nzst_to_auckland():
    """Test NZST abbreviation maps to Pacific/Auckland"""
    assert abbrev_to_canonical_timezone("NZST") == "Pacific/Auckland"


def test_nzdt_to_auckland():
    """Test NZDT abbreviation maps to Pacific/Auckland"""
    assert abbrev_to_canonical_timezone("NZDT") == "Pacific/Auckland"


def test_cet_to_paris():
    """Test CET abbreviation maps to Europe/Paris"""
    assert abbrev_to_canonical_timezone("CET") == "Europe/Paris"


def test_cest_to_paris():
    """Test CEST abbreviation maps to Europe/Paris"""
    assert abbrev_to_canonical_timezone("CEST") == "Europe/Paris"


def test_hst_to_honolulu():
    """Test HST abbreviation maps to Pacific/Honolulu"""
    assert abbrev_to_canonical_timezone("HST") == "Pacific/Honolulu"


def test_kst_to_seoul():
    """Test KST abbreviation maps to Asia/Seoul"""
    assert abbrev_to_canonical_timezone("KST") == "Asia/Seoul"


def test_case_insensitive():
    """Test that abbreviations are case-insensitive"""
    assert abbrev_to_canonical_timezone("pst") == "America/Los_Angeles"
    assert abbrev_to_canonical_timezone("Pst") == "America/Los_Angeles"
    assert abbrev_to_canonical_timezone("PST") == "America/Los_Angeles"


def test_whitespace_handling():
    """Test that whitespace is properly stripped"""
    assert abbrev_to_canonical_timezone("  PST  ") == "America/Los_Angeles"
    assert abbrev_to_canonical_timezone("\tIDT\n") == "Asia/Jerusalem"


def test_none_input():
    """Test None input returns None"""
    assert abbrev_to_canonical_timezone(None) is None


def test_empty_string():
    """Test empty string returns None"""
    assert abbrev_to_canonical_timezone("") is None
    assert abbrev_to_canonical_timezone("   ") is None


def test_unknown_abbreviation():
    """Test unknown abbreviation returns None"""
    assert abbrev_to_canonical_timezone("UNKNOWN") is None
    assert abbrev_to_canonical_timezone("XXX") is None
    assert abbrev_to_canonical_timezone("NOTREAL") is None


def test_valid_iana_timezone_passthrough():
    """Test that valid IANA timezones are returned as-is"""
    assert abbrev_to_canonical_timezone("America/New_York") == "America/New_York"
    assert abbrev_to_canonical_timezone("Asia/Tokyo") == "Asia/Tokyo"
    assert abbrev_to_canonical_timezone("Europe/London") == "Europe/London"


def test_south_america_timezones():
    """Test South American timezone abbreviations"""
    assert abbrev_to_canonical_timezone("BRT") == "America/Sao_Paulo"
    assert abbrev_to_canonical_timezone("ART") == "America/Argentina/Buenos_Aires"
    assert abbrev_to_canonical_timezone("CLT") == "America/Santiago"


def test_africa_timezones():
    """Test African timezone abbreviations"""
    assert abbrev_to_canonical_timezone("EAT") == "Africa/Nairobi"
    assert abbrev_to_canonical_timezone("WAT") == "Africa/Lagos"
    assert abbrev_to_canonical_timezone("SAST") == "Africa/Johannesburg"


def test_middle_east_timezones():
    """Test Middle Eastern timezone abbreviations"""
    assert abbrev_to_canonical_timezone("PKT") == "Asia/Karachi"
    assert abbrev_to_canonical_timezone("GST") == "Asia/Dubai"
    assert abbrev_to_canonical_timezone("IRST") == "Asia/Tehran"


def test_asia_timezones():
    """Test Asian timezone abbreviations"""
    assert abbrev_to_canonical_timezone("HKT") == "Asia/Hong_Kong"
    assert abbrev_to_canonical_timezone("SGT") == "Asia/Singapore"
    assert abbrev_to_canonical_timezone("ICT") == "Asia/Bangkok"


def test_pacific_timezones():
    """Test Pacific timezone abbreviations"""
    assert abbrev_to_canonical_timezone("CHST") == "Pacific/Guam"
    assert abbrev_to_canonical_timezone("SST") == "Pacific/Pago_Pago"
    assert abbrev_to_canonical_timezone("FJT") == "Pacific/Fiji"


def test_north_america_all_zones():
    """Test all North American timezone abbreviations"""
    # Pacific
    assert abbrev_to_canonical_timezone("PST") == "America/Los_Angeles"
    assert abbrev_to_canonical_timezone("PDT") == "America/Los_Angeles"
    # Mountain
    assert abbrev_to_canonical_timezone("MST") == "America/Denver"
    assert abbrev_to_canonical_timezone("MDT") == "America/Denver"
    # Central
    assert abbrev_to_canonical_timezone("CST") == "America/Chicago"
    assert abbrev_to_canonical_timezone("CDT") == "America/Chicago"
    # Eastern
    assert abbrev_to_canonical_timezone("EST") == "America/New_York"
    assert abbrev_to_canonical_timezone("EDT") == "America/New_York"
    # Atlantic
    assert abbrev_to_canonical_timezone("AST") == "America/Halifax"
    assert abbrev_to_canonical_timezone("ADT") == "America/Halifax"
    # Alaska
    assert abbrev_to_canonical_timezone("AKST") == "America/Anchorage"
    assert abbrev_to_canonical_timezone("AKDT") == "America/Anchorage"
    # Hawaii
    assert abbrev_to_canonical_timezone("HST") == "Pacific/Honolulu"
    # Newfoundland
    assert abbrev_to_canonical_timezone("NST") == "America/St_Johns"
    assert abbrev_to_canonical_timezone("NDT") == "America/St_Johns"


def test_australia_timezones():
    """Test Australian timezone abbreviations"""
    assert abbrev_to_canonical_timezone("AWST") == "Australia/Perth"
    assert abbrev_to_canonical_timezone("ACST") == "Australia/Adelaide"
    assert abbrev_to_canonical_timezone("ACDT") == "Australia/Adelaide"
    assert abbrev_to_canonical_timezone("AEST") == "Australia/Sydney"
    assert abbrev_to_canonical_timezone("AEDT") == "Australia/Sydney"


def test_europe_timezones():
    """Test European timezone abbreviations"""
    assert abbrev_to_canonical_timezone("WET") == "Europe/Lisbon"
    assert abbrev_to_canonical_timezone("WEST") == "Europe/Lisbon"
    assert abbrev_to_canonical_timezone("CET") == "Europe/Paris"
    assert abbrev_to_canonical_timezone("CEST") == "Europe/Paris"
    assert abbrev_to_canonical_timezone("EET") == "Europe/Athens"
    assert abbrev_to_canonical_timezone("EEST") == "Europe/Athens"
    assert abbrev_to_canonical_timezone("MSK") == "Europe/Moscow"
