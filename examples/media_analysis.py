"""Query media analysis data for photos"""

import json
import logging
import os
import pathlib
import plistlib
import re
import sqlite3
from functools import cache

import click

import osxphotos
from osxphotos.cli import query_command, verbose

logger = logging.getLogger("osxphotos")

# Constants for keys
FACE_KEY = "faces"
HUMAN_KEY = "humans"
QUALITY_KEY = "quality"
IMAGE_CAPTION_KEY = "image_caption"
VIDEO_CAPTION_KEY = "video_caption"
SHARPNESS_KEY = "sharpness"
JUNK_KEY = "junk"
FEATURE_VECTOR_KEY = "feature_vector"
SHOT_TYPE_KEY = "shot_type"
QUALITY_SEGMENTS_KEY = "quality_segments"
FLAG_SEGMENTS_KEY = "flag_segments"
SCENE_SEGMENTS_KEY = "scene_segments"
SEGMENTS_KEY = "segments"
UNKNOWN_KEY = "unknown"


@cache
def get_media_analysis_path(photosdb_path: str | os.PathLike) -> pathlib.Path:
    """Get path to media analysis database for a photo"""
    # media analysis is in private/com.apple.mediaanalysisd/MediaAnalysis
    media_analysis_path = (
        pathlib.Path(photosdb_path).parent.parent
        / "private/com.apple.mediaanalysisd/MediaAnalysis/mediaanalysis.db"
    )
    if not media_analysis_path.exists():
        raise FileNotFoundError(
            f"Media analysis database not found at {media_analysis_path}"
        )
    return media_analysis_path


def get_media_analysis(photo: osxphotos.PhotoInfo) -> dict:
    """Get media analysis data for a photo"""
    media_analysis_db = get_media_analysis_path(photo._db.db_path)

    try:
        conn = sqlite3.connect(media_analysis_db)
    except sqlite3.Error as e:
        print(f"Error connecting to media analysis database: {e}")
        return {}

    local_identifier = f"{photo.uuid}/L0/001"
    sql = """
    SELECT results FROM Results
    JOIN Assets ON Results.assetID = Assets.id
    WHERE Assets.localIdentifier = ?
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (local_identifier,))
        data = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.warning(
            f"Error fetching media analysis data for photo {photo.filename}: {e}"
        )
        return []

    if not data:
        return []
    return [plistlib.loads(row[0], fmt=plistlib.FMT_BINARY) for row in data]


def get_caption(results: list[list[dict]]) -> str | None:
    for result in results:
        if result and result[0] and result[0].get("attributes"):
            attrs = result[0]["attributes"]
            if "imageCaptionText" in attrs:
                return attrs["imageCaptionText"]
            elif "videoCaptionText" in attrs:
                return attrs["videoCaptionText"]
    return None


def get_key(d: dict) -> str:
    if "attributes" in d:
        attrs = d["attributes"]
        if "faceBounds" in attrs:
            return FACE_KEY
        elif "humanBounds" in attrs:
            return HUMAN_KEY
        elif "imageCaptionText" in attrs:
            return IMAGE_CAPTION_KEY
        elif "videoCaptionText" in attrs:
            return VIDEO_CAPTION_KEY
        elif "sharpness" in attrs:
            return SHARPNESS_KEY
        elif "junk" in attrs:
            return JUNK_KEY
        elif "featureVector" in attrs:
            return FEATURE_VECTOR_KEY
        elif "shotType" in attrs:
            return SHOT_TYPE_KEY
        elif "sceneprintDistance" in attrs:
            return SCENE_SEGMENTS_KEY
    if "quality" in d and "start" not in d:
        return QUALITY_KEY
    if "start" in d and "duration" in d:
        if "quality" in d:
            return QUALITY_SEGMENTS_KEY
        elif "flags" in d:
            return FLAG_SEGMENTS_KEY
        else:
            return SEGMENTS_KEY
    return UNKNOWN_KEY


def parse_bounds(bounds_str):
    match = re.match(r"\{\{([^}]+)\}, \{([^}]+)\}\}", bounds_str)
    if match:
        p1 = tuple(float(x.strip()) for x in match.group(1).split(","))
        p2 = tuple(float(x.strip()) for x in match.group(2).split(","))
        return (p1, p2)
    return bounds_str


def process_dict(d):
    result = {}
    if "flags" in d:
        result["flags"] = d["flags"]
    if "attributes" in d:
        attrs = d["attributes"]
        for k, v in attrs.items():
            if k in ["faceBounds", "humanBounds"]:
                result[k] = parse_bounds(v)
            else:
                result[k] = v
    else:
        for k, v in d.items():
            result[k] = v
    return result


def media_analysis_result_to_dict(data: list[list[dict]]) -> dict:
    result = {}
    for sublist in data:
        if not sublist:
            continue
        key = get_key(sublist[0])
        processed = [process_dict(d) for d in sublist]
        if len(processed) == 1:
            result[key] = processed[0]
        else:
            result[key] = processed
    return result


def remove_byte_keys(obj):
    if isinstance(obj, dict):
        return {
            k: remove_byte_keys(v) for k, v in obj.items() if not isinstance(v, bytes)
        }
    elif isinstance(obj, list):
        return [remove_byte_keys(i) for i in obj if not isinstance(i, bytes)]
    else:
        return obj


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return "<bytes>"  # or base64.b64encode(obj).decode('ascii')
        return super().default(obj)


@query_command
@click.option(
    "--json", "-j", "json_option", is_flag=True, help="Output results in JSON format"
)
def media_analysis(photos: list[osxphotos.PhotoInfo], json_option: bool, **kwargs):
    """Sample query command for osxphotos. Prints out the filename and date of each photo.

    Whatever text you put in the function's docstring here, will be used as the command's
    help text when run via `osxphotos run cli_example_1.py --help` or `python cli_example_1.py --help`
    """

    # verbose() will print to stdout if --verbose option is set
    # you can optionally provide a level (default is 1) to print only if --verbose is set to that level
    # for example: -VV or --verbose --verbose == level 2
    verbose(f"Found {len(photos)} photo(s)")

    # do something with photos here
    for photo in photos:
        results = get_media_analysis(photo)
        results_dict = media_analysis_result_to_dict(results)
        if json_option:
            results_dict["uuid"] = photo.uuid
            results_dict["filename"] = photo.original_filename
            print(json.dumps(results_dict, cls=BytesEncoder, indent=4))
        else:
            caption = get_caption(results)
            print(f"{photo.original_filename}, {photo.uuid}, {caption}")


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    media_analysis()
