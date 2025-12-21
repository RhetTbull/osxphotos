""" Common utilities for PhotoInfo variations """

from typing import Any

# These are PhotoInfo.asdict() keys that that are removed from the output
# by the PhotoExporter for comparing PhotoInfo objects.

FULL_KEYS = [
    "album_info",
    "path_derivatives",
    "adjustments",
    "burst_album_info",
    "burst_albums",
    "burst_default_pick",
    "burst_key",
    "burst_photos",
    "burst_selected",
    "cloud_metadata",
    "import_info",
    "labels_normalized",
    "person_info",
    "project_info",
    "search_info",
    "search_info_normalized",
    "syndicated",
    "saved_to_library",
    "shared_moment",
    "shared_library",
    "rating",
    "screen_recording",
    "date_original",
    "tzname",
    "media_analysis",
]


def photoinfo_minify_dict(info: dict[str, Any]) -> dict[str, Any]:
    """Convert a full PhotoInfo dict to a minimum PhotoInfo dict"""
    return {k: v for k, v in info.items() if k not in FULL_KEYS}
