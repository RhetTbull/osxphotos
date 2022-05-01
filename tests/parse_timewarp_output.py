""" Parse --inspect and --compare-exif output for testing"""

from collections import namedtuple
from typing import List

# filename, uuid, photo time (local), photo time, timezone offset, timezone name
InspectValues = namedtuple(
    "InspectValues",
    ["filename", "uuid", "date_local", "date_tz", "tz_offset", "tz_name"],
)

CompareValues = namedtuple(
    "CompareValues",
    [
        "filename",
        "uuid",
        "date_photos",
        "date_exif",
        "tz_offset_photos",
        "tz_offset_exif",
    ],
)


def parse_inspect_output(output: str) -> List[InspectValues]:
    """Parse output of --inspect and return list of InspectValues named tuple"""
    
    with open(output, "r") as f:
        lines = f.readlines()
    lines = [line for line in lines if line.strip()]
    # remove header
    lines.pop(0)
    values = []
    for line in lines:
        parts = line.split(",")
        parts = [part.strip() for part in parts]
        values.append(InspectValues(*parts))
    return values


def parse_compare_exif(output: str) -> List[CompareValues]:
    """Parse output of --compare-exif and return list of CompareValues named tuple"""
    with open(output, "r") as f:
        lines = f.readlines()
    lines = [line for line in lines if line.strip()]
    # remove header
    lines.pop(0)
    values = []
    for line in lines:
        parts = line.split(",")
        parts = [part.strip() for part in parts]
        values.append(CompareValues(*parts))
    return values
