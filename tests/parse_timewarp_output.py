""" Parse --inspect and --compare-exif output for testing"""

from collections import namedtuple
from typing import List

# filename, uuid, photo time (local), photo time, timezone offset, timezone name
InspectValues = namedtuple(
    "InspectValues",
    [
        "filename",
        "uuid",
        "date_local",
        "date_tz",
        "tz_offset",
        "tz_name",
    ],
)

InspectValuesDateAdded = namedtuple(
    "InspectValues",
    [
        "filename",
        "uuid",
        "date_local",
        "date_tz",
        "tz_offset",
        "tz_name",
        "date_added",
    ],
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


def parse_inspect_output(
    output: str, date_added: bool = False
) -> List[InspectValues] | List[InspectValuesDateAdded]:
    """Parse output of --inspect and return list of InspectValues named tuple"""

    lines = [line for line in output.split("\n") if line.strip()]
    # remove header
    lines.pop(0)
    values = []
    for line in lines:
        parts = line.split(",")
        parts = [part.strip() for part in parts]
        if not date_added:
            # remove date added
            parts.pop()
            values.append(InspectValues(*parts))
        else:
            values.append(InspectValuesDateAdded(*parts))
    return values


def parse_compare_exif(output: str) -> List[CompareValues]:
    """Parse output of --compare-exif and return list of CompareValues named tuple"""
    lines = [line for line in output.split("\n") if line.strip()]
    # remove header
    lines.pop(0)
    values = []
    for line in lines:
        parts = line.split(",")
        parts = [part.strip() for part in parts]
        values.append(CompareValues(*parts))
    return values
