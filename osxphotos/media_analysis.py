"""Query media analysis data for photos"""

from __future__ import annotations

import datetime
import json
import logging
import os
import pathlib
import plistlib
import re
import sqlite3
from functools import cache
from typing import Any, TYPE_CHECKING


from .photos_datetime import photos_datetime_local

if TYPE_CHECKING:
    from .photoinfo import PhotoInfo

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
def _get_media_analysis_path(photosdb_path: str | os.PathLike) -> pathlib.Path:
    """Get path to media analysis database for a photo"""
    # media analysis is in private/com.apple.mediaanalysisd/MediaAnalysis
    # media analysis database is called MediaAnalysis.sqlite or mediaanalysis.db

    base_path = (
        pathlib.Path(photosdb_path).parent.parent
        / "private/com.apple.mediaanalysisd/MediaAnalysis"
    )

    # Check both possible database names
    for db_name in ("MediaAnalysis.sqlite", "mediaanalysis.db"):
        media_analysis_path = base_path / db_name
        if media_analysis_path.exists():
            return media_analysis_path

    # If neither exists, raise error with both possible paths
    raise FileNotFoundError(
        f"Media analysis database not found at {base_path / 'mediaanalysis.db'} or {base_path / 'MediaAnalysis.sqlite'}"
    )


def _get_media_analysis_db_path(photo: PhotoInfo) -> pathlib.Path | None:
    """Given a photo, return the correct media analysis db path"""
    try:
        return _get_media_analysis_path(photo._db.db_path)
    except FileNotFoundError:
        logger.warning(
            f"Media analysis database not found for photo {photo.original_filename}"
        )
        return None


def _local_identifier_for_photo(photo: PhotoInfo) -> str:
    """Return local identifier from photo's UUID"""
    return f"{photo.uuid}/L0/001"


def get_media_analysis_date(photo: PhotoInfo) -> datetime.datetime | None:
    """Get media analysis date for a photo"""
    sql = """
    SELECT dateAnalyzed from Assets
    WHERE Assets.localIdentifier = ?
    """

    media_analysis_db = _get_media_analysis_db_path(photo)
    if not media_analysis_db:
        return None

    try:
        conn = sqlite3.connect(media_analysis_db)
    except sqlite3.Error as e:
        logger.warning(f"Error connecting to media analysis database: {e}")
        return None

    if photo._db.photos_version < 11:
        sql = """
        SELECT dateAnalyzed
        FROM Assets
        WHERE localIdentifier = ?;
        """
    else:
        sql = """
        SELECT ZDATEANALYZED
        FROM ZASSET
        WHERE ZLOCALIDENTIFIER = ?;
        """

    # convert to with block
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (_local_identifier_for_photo(photo),))
        date_data = cursor.fetchone()
    except Exception as e:
        logger.warning(
            f"Error fetching media analysis date for photo {photo.original_filename}: {e}"
        )
        return None
    finally:
        conn.close()

    try:
        return photos_datetime_local(date_data[0])
    except Exception as e:
        logger.warning(
            f"Error converting media analysis date for photo {photo.original_filename}: {e}"
        )
        return None


def _get_media_analysis_data(
    photo: PhotoInfo,
) -> tuple[datetime.datetime | None, list[list[dict]]]:
    """Get media analysis data for a photo"""

    try:
        media_analysis_db = _get_media_analysis_path(photo._db.db_path)
    except FileNotFoundError:
        logger.warning(f"Media analysis database not found for photo {photo.filename}")
        return None, []

    try:
        conn = sqlite3.connect(media_analysis_db)
    except sqlite3.Error as e:
        logger.warning(f"Error connecting to media analysis database: {e}")
        return None, []

    if photo._db.photos_version < 11:
        sql = """
        SELECT Results.results FROM Results
        JOIN Assets ON Results.assetID = Assets.id
        WHERE Assets.localIdentifier = ?;
        """
    else:
        sql = """
        SELECT ZRESULT.ZRESULTS FROM ZRESULT
        JOIN ZASSET ON ZRESULT.ZASSET = ZASSET.Z_PK
        WHERE ZASSET.ZLOCALIDENTIFIER = ?;
        """

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (_local_identifier_for_photo(photo),))
        data = cursor.fetchall()
    except Exception as e:
        logger.warning(
            f"Error fetching media analysis data for photo {photo.filename}: {e}"
        )
        data = []
    finally:
        conn.close()

    if not data:
        return None, []

    analysis_date = get_media_analysis_date(photo)

    results = []
    for row in data:
        try:
            plist_data = plistlib.loads(row[0], fmt=plistlib.FMT_BINARY)
        except Exception as e:
            logger.warning(
                f"Error parsing media analysis data for photo {photo.filename}: {e}"
            )
            plist_data = None
        results.append(plist_data)
    return analysis_date, results


def _get_key_from_attributes(d: dict) -> str:
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


def _parse_bounds(bounds_str):
    match = re.match(r"\{\{([^}]+)\}, \{([^}]+)\}\}", bounds_str)
    if match:
        p1 = tuple(float(x.strip()) for x in match.group(1).split(","))
        p2 = tuple(float(x.strip()) for x in match.group(2).split(","))
        return (p1, p2)
    return bounds_str


def _process_dict(d):
    result = {}
    if "flags" in d:
        result["flags"] = d["flags"]
    if "attributes" in d:
        attrs = d["attributes"]
        for k, v in attrs.items():
            if k in ["faceBounds", "humanBounds"]:
                result[k] = _parse_bounds(v)
            else:
                result[k] = v
    else:
        for k, v in d.items():
            result[k] = v
    return result


def _media_analysis_result_to_dict(data: list[list[dict]]) -> dict:
    result = {}
    for sublist in data:
        if not sublist:
            continue
        key = _get_key_from_attributes(sublist[0])
        processed = [_process_dict(d) for d in sublist]
        if len(processed) == 1:
            result[key] = processed[0]
        else:
            result[key] = processed
    return result


def _remove_byte_keys(obj):
    if isinstance(obj, dict):
        return {
            k: _remove_byte_keys(v) for k, v in obj.items() if not isinstance(v, bytes)
        }
    elif isinstance(obj, list):
        return [_remove_byte_keys(i) for i in obj if not isinstance(i, bytes)]
    else:
        return obj


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return "<bytes>"  # or base64.b64encode(obj).decode('ascii')
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


def get_media_analysis_results(photo: PhotoInfo) -> dict[str, Any]:
    """Get media analysis results dictionary for a photo"""
    date_analyzed, results = _get_media_analysis_data(photo)
    results_dict = _media_analysis_result_to_dict(results)
    results_dict["uuid"] = photo.uuid
    results_dict["filename"] = photo.original_filename
    results_dict["date_analyzed"] = date_analyzed
    return results_dict


def get_caption(results: dict[str, Any]) -> str | None:
    if caption_dict := results.get(IMAGE_CAPTION_KEY):
        if isinstance(caption_dict, list):
            caption_dict = max(
                caption_dict,
                key=lambda item: item.get("imageCaptionConfidence", float("-inf")),
                default=None,
            )
            if not isinstance(caption_dict, dict):
                return None
        return caption_dict.get("imageCaptionText")
    if caption_dict := results.get(VIDEO_CAPTION_KEY):
        if isinstance(caption_dict, list):
            caption_dict = max(
                caption_dict,
                key=lambda item: item.get("videoCaptionConfidence", float("-inf")),
                default=None,
            )
            if not isinstance(caption_dict, dict):
                return None
        return caption_dict.get("videoCaptionText")
    return None


def media_analysis_results_to_json(
    results: dict[str, Any] | list[dict[str, Any]], indent: int = 4
) -> str:
    """Convert media analysis results or list of results to JSON str"""
    json_str = json.dumps(results, indent=indent, cls=BytesEncoder)
    return json_str
