""" Test data for timewarp command on Catalina/Photos 5 """

import datetime
import pathlib

from tests.parse_timewarp_output import CompareValues, InspectValues

TEST_LIBRARY_TIMEWARP = "tests/TestTimeWarp-13.1.0.photoslibrary"


def get_file_timestamp(file: str) -> str:
    """Get timestamp of file"""
    return datetime.datetime.fromtimestamp(pathlib.Path(file).stat().st_mtime).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


VENTURA_PHOTOS_5 = {
    "filenames": {
        "pumpkins": "IMG_6522.jpeg",
        "pears": "IMG_6501.jpeg",
        "sunflowers": "IMG_6520.jpeg",
        "apple tree": "IMG_6526.jpeg",
        "marigold flowers": "IMG_6517.jpeg",
        "multi-colored zinnia flowers": "IMG_6506.jpeg",
        "sunset": "IMG_6551.mov",
    },
    "inspect": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [
            InspectValues(
                "IMG_6501.jpeg",
                "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
                "2021-10-02 12:40:07-0700",
                "2021-10-02 12:40:07-0700",
                "-0700",
                "GMT-0700",
            )
        ],
    },
    "date": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "value": "2020-09-01",
        "date": datetime.datetime(2020, 9, 1, 12, 40, 7),
    },
    "date_delta": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("1", "2020-09-02 12:40:07-0700"),
            ("1 day", "2020-09-03 12:40:07-0700"),
            ("1 week", "2020-09-10 12:40:07-0700"),
            ("-1", "2020-09-09 12:40:07-0700"),
            ("-1 day", "2020-09-08 12:40:07-0700"),
            ("-1 week", "2020-09-01 12:40:07-0700"),
        ],
    },
    "time": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("14:42", "2020-09-01 14:42:00-0700"),
            ("14:42:30", "2020-09-01 14:42:30-0700"),
            # Photos doesn't return the milliseconds
            ("14:42:31.234", "2020-09-01 14:42:31-0700"),
        ],
    },
    "time_delta": {
        # IMG_6501.jpeg
        # Format is one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S'(where S is seconds)
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("1:10:20", "2020-09-01 15:52:51-0700"),
            ("1 hours", "2020-09-01 16:52:51-0700"),
            ("1", "2020-09-01 16:52:52-0700"),
            ("+1", "2020-09-01 16:52:53-0700"),
            ("-1", "2020-09-01 16:52:52-0700"),
            ("-1 hour", "2020-09-01 15:52:52-0700"),
            ("3 minutes", "2020-09-01 15:55:52-0700"),
            ("3 min", "2020-09-01 15:58:52-0700"),
            ("-6 min", "2020-09-01 15:52:52-0700"),
            ("+10 sec", "2020-09-01 15:53:02-0700"),
        ],
    },
    "time_zone": {
        # IMG_6501.jpeg
        # Format is one of '±HH:MM', '±H:MM', or '±HHMM'
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("-06:00", "2020-09-01 16:53:02-0600", "-0600"),
        ],
    },
    "compare_exif": {
        # IMG_6501.jpeg
        # filename, uuid, photo time (Photos), photo time (EXIF), timezone offset (Photos), timezone offset (EXIF)
        # IMG_6501.jpeg, 2F00448D-3C0D-477A-9B10-5F21DCAB405A, 2020-09-01 16:53:02, 2021-10-02 12:40:07, -0600, -0700
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [
            CompareValues(
                "IMG_6501.jpeg",
                "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
                "2020-09-01 16:53:02",
                "2021-10-02 12:40:07",
                "-0600",
                "-0700",
            ),
        ],
    },
    "compare_exif_add_to_album": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [("found 1 that is different", "Different EXIF")],
    },
    "compare_exif_3": {
        # IMG_6520.jpeg
        # IMG_6520.jpeg, 53615D56-91F7-4908-81F1-B93B5DEA7449, 2021-10-02 12:54:36,  , -0700,
        "uuid": "53615D56-91F7-4908-81F1-B93B5DEA7449",
        "expected": [
            CompareValues(
                "IMG_6520.jpeg",
                "53615D56-91F7-4908-81F1-B93B5DEA7449",
                "2021-10-02 12:54:36",
                "",
                "-0700",
                "",
            ),
        ],
    },
    "match": {  # IMG_6520.jpeg
        # IMG_6520.jpeg, 53615D56-91F7-4908-81F1-B93B5DEA7449, 2021-10-02 12:54:36,  , -0700,
        "uuid": "53615D56-91F7-4908-81F1-B93B5DEA7449",
        "parameters": [
            ("-0500", "2021-10-02 12:54:36-0500"),
            ("+01:00", "2021-10-02 12:54:36+0100"),
        ],
    },
    "exiftool": {
        # IMG_6522.jpeg
        "uuid": "FD1E3A36-3E65-48AF-9B14-DCFF65A9D3D2",
        # match,tz_value,time_delta_value,expected_date,exif_date,exif_offset
        "parameters": [
            (
                True,
                "-0300",
                "+1 hour",
                "2021-10-02 13:56:11-0300",
                "2021:10:02 13:56:11",
                "-03:00",
            ),
            (
                False,
                "-0400",
                "+2 hours",
                "2021-10-02 14:56:11-0400",
                "2021:10:02 14:56:11",
                "-04:00",
            ),
        ],
    },
    "push_exif": {
        # IMG_6501.jpeg
        "pre": CompareValues(
            "IMG_6501.jpeg",
            "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
            "2020-09-01 16:53:02",
            "2021-10-02 12:40:07",
            "-0600",
            "-0700",
        ),
        "post": CompareValues(
            "IMG_6501.jpeg",
            "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
            "2020-09-01 16:53:02",
            "2020-09-01 16:53:02",
            "-0600",
            "-0600",
        ),
    },
    "pull_exif_1": {
        # IMG_6501.jpeg
        "pre": CompareValues(
            "IMG_6501.jpeg",
            "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
            "2020-09-02 16:53:02",
            "2020-09-01 16:53:02",
            "-0400",
            "-0600",
        ),
        "post": CompareValues(
            "IMG_6501.jpeg",
            "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
            "2020-09-01 16:53:02",
            "2020-09-01 16:53:02",
            "-0600",
            "-0600",
        ),
    },
    "pull_exif_no_time": {
        # IMG_6526.jpeg (apple tree)
        "pre": CompareValues(
            "IMG_6526.jpeg",
            "1A61156A-5747-42DE-A9B3-4A468CC49D9E",
            "2021-10-02 15:15:00",
            "2021-10-02 00:00:00",
            "-0400",
            "-0700",
        ),
        "post": CompareValues(
            "IMG_6526.jpeg",
            "1A61156A-5747-42DE-A9B3-4A468CC49D9E",
            "2021-10-02 00:00:00",
            "2021-10-02 00:00:00",
            "-0700",
            "-0700",
        ),
    },
    "pull_exif_no_offset": {
        # IMG_6517.jpeg
        "pre": CompareValues(
            "IMG_6517.jpeg",
            "C4D952AF-983D-438E-9070-6310B1BC4826",
            "2021-10-02 12:50:00",
            "2021-10-02 12:51:15",
            "-0700",
            "",
        ),
        "post": CompareValues(
            "IMG_6517.jpeg",
            "C4D952AF-983D-438E-9070-6310B1BC4826",
            "2021-10-02 12:51:15",
            "2021-10-02 12:51:15",
            "-0700",
            "",
        ),
    },
    "pull_exif_no_data": {
        # IMG_6506.jpeg (zinnia flowers)
        "pre": CompareValues(
            "IMG_6506.jpeg",
            "7E9DF2EE-A5B0-4077-80EC-30565221A3B9",
            "2021-10-08 16:11:09",
            "",
            "-0700",
            "",
        ),
        "post": CompareValues(
            "IMG_6506.jpeg",
            "7E9DF2EE-A5B0-4077-80EC-30565221A3B9",
            "2021-10-08 16:11:09",
            "",
            "-0700",
            "",
        ),
    },
    "pull_exif_no_data_use_file_time": {
        # IMG_6506.jpeg (zinnia flowers)
        "pre": CompareValues(
            "IMG_6506.jpeg",
            "7E9DF2EE-A5B0-4077-80EC-30565221A3B9",
            "2021-10-08 16:11:09",
            "",
            "-0700",
            "",
        ),
        "post": CompareValues(
            "IMG_6506.jpeg",
            "7E9DF2EE-A5B0-4077-80EC-30565221A3B9",
            get_file_timestamp(
                f"{TEST_LIBRARY_TIMEWARP}/originals/7/7E9DF2EE-A5B0-4077-80EC-30565221A3B9.jpeg"
            ),
            "",
            "-0700",
            "",
        ),
    },
    "compare_video_1": {
        # IMG_6551.mov
        "expected": [
            CompareValues(
                "IMG_6551.mov",
                "16BEC0BE-4188-44F1-A8F1-7250E978AD12",
                "2021-10-04 19:01:03",
                "2021-10-04 19:01:03",
                "-0700",
                "-0700",
            )
        ]
    },
    "video_date_delta": {
        # IMG_6551.mov
        "parameters": [("-1 day", "2021-10-03 19:01:03-0700")]
    },
    "video_time_delta": {
        # IMG_6551.mov
        "parameters": [("+1 hour", "2021-10-03 20:01:03-0700")]
    },
    "video_date": {
        # IMG_6551.mov
        "parameters": [("2021-10-04", "2021-10-04 20:01:03-0700")]
    },
    "video_time": {
        # IMG_6551.mov
        "parameters": [("20:00:00", "2021-10-04 20:00:00-0700")]
    },
    "video_time_zone": {
        # IMG_6551.mov
        "parameters": [("-0400", "2021-10-04 23:00:00-0400", "-0400")]
    },
    "video_match": {
        # IMG_6551.mov
        "parameters": [("-0200", "2021-10-04 23:00:00-0200")]
    },
    "video_push_exif": {
        # IMG_6551.mov
        "pre": CompareValues(
            "IMG_6551.mov",
            "16BEC0BE-4188-44F1-A8F1-7250E978AD12",
            "2021-10-04 23:00:00",
            "2021-10-04 19:01:03",
            "-0200",
            "-0700",
        ),
        "post": CompareValues(
            "IMG_6551.mov",
            "16BEC0BE-4188-44F1-A8F1-7250E978AD12",
            "2021-10-04 23:00:00",
            "2021-10-04 23:00:00",
            "-0200",
            "-0200",
        ),
    },
    "video_pull_exif": {
        # IMG_6551.jpeg
        "pre": CompareValues(
            "IMG_6551.mov",
            "16BEC0BE-4188-44F1-A8F1-7250E978AD12",
            "2021-10-05 13:00:00",
            "2021-10-04 23:00:00",
            "-0500",
            "-0200",
        ),
        "post": CompareValues(
            "IMG_6551.mov",
            "16BEC0BE-4188-44F1-A8F1-7250E978AD12",
            "2021-10-04 23:00:00",
            "2021-10-04 23:00:00",
            "-0200",
            "-0200",
        ),
    },
    "function": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": InspectValues(
            "IMG_6501.jpeg",
            "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
            "2020-09-01 18:53:02-0700",
            "2020-09-01 18:53:02-0700",
            "-0700",
            "GMT-0700",
        ),
    },
}
