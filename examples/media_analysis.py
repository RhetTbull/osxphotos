"""Query media analysis data for photos"""

import json
import logging
import os
import pathlib
import plistlib
import sqlite3
from functools import cache

import osxphotos
from osxphotos.cli import query_command, verbose

logger = logging.getLogger("osxphotos")


@cache
def get_media_analysis_path(photosdb_path: str | os.PathLike) -> pathlib.Path:
    """Get path to media analysis database for a photo"""
    # media analysis is in private/com.apple.mediaanalysisd/MediaAnalysis
    media_analysis_path = pathlib.Path(photosdb_path).parent.parent / "private/com.apple.mediaanalysisd/MediaAnalysis/mediaanalysis.db"
    if not media_analysis_path.exists():
        raise FileNotFoundError(f"Media analysis database not found at {media_analysis_path}")
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
        logger.warning(f"Error fetching media analysis data for photo {photo.filename}: {e}")
        return []

    if not data:
        return []
    return [plistlib.loads(row[0], fmt=plistlib.FMT_BINARY) for row in data]


def get_caption(results: list[dict]) -> str | None:
    for result in results:
        if result and result[0] and result[0].get("attributes"):
            if "imageCaptionText" in result[0]["attributes"]:
                return result[0]["attributes"]["imageCaptionText"]
    return None


@query_command
def media_analysis(photos: list[osxphotos.PhotoInfo], **kwargs):
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
        caption = get_caption(results)
        print(f"{photo.original_filename}, {photo.uuid}, {caption}")


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    media_analysis()
