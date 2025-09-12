""" Parse --inspect and --compare-exif output for testing"""

from __future__ import annotations

import datetime
import logging
from collections import namedtuple
from typing import List

logger = logging.getLogger("osxphotos")

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


def compare_inspect_output(
    value1: InspectValues | list[InspectValues],
    value2: InspectValues | list[InspectValues],
) -> bool:
    """Compare two InspectValues named tuples"""

    if not isinstance(value1, list):
        value1 = [value1]
    if not isinstance(value2, list):
        value2 = [value2]

    if len(value1) != len(value2):
        logger.warning(
            f"compare_inspect_output: value1 and value2 have different lengths: {len(value1)} != {len(value2)}"
        )
        return False

    fields = value1[0]._fields
    for v1, v2 in zip(value1, value2):
        for field in fields:
            if field.startswith("date"):
                # the date values need to be converted from ISO8601 to datetime objects for comparison
                value1_date = datetime.datetime.fromisoformat(getattr(v1, field))
                value2_date = datetime.datetime.fromisoformat(getattr(v2, field))
                if value1_date != value2_date:
                    logger.warning(
                        f"compare_inspect_output: {field} does not match: {value1_date} != {value2_date}"
                    )
                    return False
            else:
                if getattr(v1, field) != getattr(v2, field):
                    logger.warning(
                        f"compare_inspect_output: {field} does not match: {getattr(v1, field)} != {getattr(v2, field)}"
                    )
                    return False
    return True
