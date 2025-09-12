"""info command for osxphotos CLI"""

import datetime
import json
import sqlite3
import sys
from typing import Any

import click
import yaml

import osxphotos
from osxphotos import PhotosDB
from osxphotos._constants import (
    _DB_TABLE_NAMES,
    _PHOTOS_4_VERSION,
    _UNKNOWN_PERSON,
    BURST_KEY,
    BURST_PICK_TYPE_NONE,
    BURST_SELECTED,
)
from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.iphoto import iPhotoDB, is_iphoto_library
from osxphotos.photoquery import QueryOptions

from .cli_params import DB_ARGUMENT, DB_OPTION, JSON_OPTION
from .common import get_photos_db
from .list import _list_libraries

try:
    from osxphotos._constants import TIME_DELTA
except ImportError:
    # TIME_DELTA moved in v0.69.0
    from osxphotos.photos_datetime import TIME_DELTA


def get_non_analyzed_assets(photosdb: osxphotos.PhotosDB) -> list[osxphotos.PhotoInfo]:
    """Return list of all photosdb assets not yet analyzed"""
    if isinstance(photosdb, iPhotoDB):
        # not supported on iPhoto
        return []

    photos_version = photosdb.photos_version
    if int(photos_version) < 5:
        return []

    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    rows = photosdb.execute(
        f"""
        SELECT {asset_table}.ZUUID
        FROM {asset_table}
        WHERE ZASSET.ZANALYSISSTATEMODIFICATIONDATE IS NULL;
        """
    ).fetchall()
    uuids = [r[0] for r in rows]
    return [
        p
        for p in photosdb.photos(uuid=uuids)
        if not p.shared
        and not p.shared_moment
        and not p.hidden
        and not (p.syndicated and not p.saved_to_library)
    ]


def get_latest_analysis_date(photosdb: osxphotos.PhotosDB) -> datetime.datetime | None:
    """Return list of all photosdb assets not yet analyzed"""
    if isinstance(photosdb, iPhotoDB):
        # not supported on iPhoto
        return None

    photos_version = photosdb.photos_version
    if photos_version < 5:
        return None

    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    rows = photosdb.execute(
        f"""
        SELECT MAX(ZANALYSISSTATEMODIFICATIONDATE)
        FROM {asset_table};
        """
    ).fetchone()
    latest_date = rows[0]
    if latest_date is not None:
        return datetime.datetime.fromtimestamp(latest_date + TIME_DELTA)
    return None


def get_unnamed_person_photos(
    photosdb: osxphotos.PhotosDB,
) -> list[osxphotos.PhotoInfo]:
    """Get list of photos with unnamed persons"""
    if isinstance(photosdb, iPhotoDB):
        # not supported on iPhoto
        return []

    photos_version = photosdb.photos_version
    if photos_version < 5:
        return []
    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    asset_fk = _DB_TABLE_NAMES[photos_version]["DETECTED_FACE_ASSET_FK"]
    person_fk = _DB_TABLE_NAMES[photos_version]["DETECTED_FACE_PERSON_FK"]
    results = photosdb.execute(
        f""" SELECT {asset_table}.ZUUID
                FROM {asset_table}
                INNER JOIN ZDETECTEDFACE
                ON {asset_table}.Z_PK = {asset_fk}
                WHERE {person_fk} IS NULL;
            """
    ).fetchall()

    uuids = [r[0] for r in results]
    unnamed_faces = photosdb.photos(uuid=uuids)
    return unnamed_faces


def get_face_count(photosdb: osxphotos.PhotosDB, manual: bool) -> int:
    """Get count of faces in library"""

    if isinstance(photosdb, iPhotoDB):
        # not supported on iPhoto
        return 0

    manual_flag = 1 if manual else 0
    if photosdb.photos_version < 5:
        results = photosdb.execute(
            f""" SELECT COUNT(RKFACE.modelId)
                    FROM RKFace
                    WHERE RKFace.manual = {manual_flag};
            """
        ).fetchone()
        return results[0]

    results = photosdb.execute(
        f""" SELECT COUNT(ZDETECTEDFACE.Z_PK)
                FROM ZDETECTEDFACE
                WHERE ZDETECTEDFACE.ZMANUAL = {manual_flag};
            """
    ).fetchone()
    return results[0]


def get_manual_face_count(photosdb: osxphotos.PhotosDB) -> int:
    """Get count of manually added faces in library"""
    return get_face_count(photosdb, manual=True)


def get_detected_face_count(photosdb: osxphotos.PhotosDB) -> int:
    """Get count of detected faces in library"""
    return get_face_count(photosdb, manual=False)


def get_persons_count(photosdb: osxphotos.PhotosDB) -> int:
    """Get count of named persons in the database"""

    if isinstance(photosdb, iPhotoDB):
        return len(photosdb.persons_as_dict)

    return len(list(p for p in photosdb.person_info if p.name != _UNKNOWN_PERSON))


def get_non_selected_bursts(photosdb: osxphotos.PhotosDB) -> list[osxphotos.PhotoInfo]:
    """Return list of all non-selected burst images"""

    if isinstance(photosdb, iPhotoDB):
        # not supported for iPhoto
        return []

    # This requires knowledge of inner workings of PhotosDB and uses private data structs subject to change
    non_selected_uuid = []
    for p in photosdb._dbphotos:
        if photosdb._dbphotos[p]["burst"] and not (
            photosdb._dbphotos[p]["burstPickType"] & BURST_SELECTED
            or photosdb._dbphotos[p]["burstPickType"] & BURST_KEY
            or photosdb._dbphotos[p]["burstPickType"] == BURST_PICK_TYPE_NONE
        ):
            # not a key/selected burst photo
            non_selected_uuid.append(p)
    return [
        osxphotos.PhotoInfo(db=photosdb, uuid=p, info=photosdb._dbphotos[p])
        for p in non_selected_uuid
    ]


def get_photo_categories(
    photosdb: osxphotos.PhotosDB,
) -> dict[str, list[osxphotos.PhotoInfo]]:
    """Return dict of photo categories"""

    in_trash = photosdb.query(QueryOptions(deleted_only=True))

    # osxphotos includes all assets in the library including things like shared albums
    # which aren't reported by the Photos app in the totals
    all_assets = photosdb.photos()
    all_photos = [p for p in all_assets if p.isphoto]
    all_videos = [p for p in all_assets if p.ismovie]

    # filter out photos that are shared, shared moments, hidden, or syndicated
    # so we can get counts that match Photos.app
    photos = [
        p
        for p in all_photos
        if not p.shared
        and not p.shared_moment
        and not p.hidden
        and not (p.syndicated and not p.saved_to_library)
    ]
    videos = [
        p
        for p in all_videos
        if not p.shared
        and not p.shared_moment
        and not p.hidden
        and not (p.syndicated and not p.saved_to_library)
    ]
    all_photos_app = photos + videos

    missing = [
        p
        for p in all_assets
        if p.ismissing
        and not p.shared
        and not p.shared_moment
        and not (p.syndicated and not p.saved_to_library)
    ]
    missing_photos = [
        p for p in all_assets if p.ismissing and p.isphoto and not p.shared
    ]
    missing_videos = [
        p for p in all_assets if p.ismissing and p.ismovie and not p.shared
    ]

    all_non_shared_assets = [
        p
        for p in all_assets
        if not p.shared
        and not p.shared_moment
        and not (p.syndicated and not p.saved_to_library)
    ]

    cloud_asset = [p for p in all_non_shared_assets if p.iscloudasset]
    incloud = [p for p in cloud_asset if p.incloud]
    not_incloud = [p for p in cloud_asset if not p.incloud]
    not_downloaded = [p for p in cloud_asset if p.ismissing]

    isreference = [p for p in all_assets if p.isreference]
    isreference_photos = [p for p in all_assets if p.isreference and p.isphoto]
    isreference_videos = [p for p in all_assets if p.isreference and p.ismovie]

    shared_library = [p for p in all_assets if p.shared_library]
    shared_library_photos = [p for p in all_photos if p.shared_library]
    shared_library_videos = [p for p in all_videos if p.shared_library]

    shared = [p for p in all_assets if p.shared]
    shared_photos = [p for p in all_photos if p.shared]
    shared_videos = [p for p in all_videos if p.shared]
    shared_moment = [p for p in all_assets if p.shared and p.shared_moment]
    syndicated = [p for p in all_assets if p.syndicated]
    syndicated_saved_to_library = [
        p for p in all_assets if p.syndicated and p.saved_to_library
    ]
    syndicated_not_saved_to_library = [
        p for p in all_assets if p.syndicated and not p.saved_to_library
    ]

    hidden = [p for p in all_assets if p.hidden]
    hidden_photos = [p for p in all_assets if p.hidden and p.isphoto]
    hidden_videos = [p for p in all_assets if p.hidden and p.ismovie]

    favorite = [p for p in all_assets if p.favorite]
    favorite_photos = [p for p in all_assets if p.favorite and p.isphoto]
    favorite_videos = [p for p in all_assets if p.favorite and p.ismovie]

    has_raw = [p for p in all_assets if p.has_raw]
    is_raw = [p for p in all_assets if p.israw]

    hasadjustments = [p for p in all_assets if p.hasadjustments]
    hasadjustments_photos = [p for p in all_assets if p.hasadjustments and p.isphoto]
    hasadjustments_videos = [p for p in all_assets if p.hasadjustments and p.ismovie]
    external_edit = [p for p in all_assets if p.external_edit]

    # non-selected bursts are not visible
    visible = [p for p in all_non_shared_assets if p.visible]
    not_visible = [p for p in all_non_shared_assets if not p.visible]

    location = [p for p in all_assets if p.location != (None, None)]
    no_location = [p for p in all_non_shared_assets if p.location == (None, None)]
    reverse_geo = [p for p in all_assets if p.place is not None]

    burst = [p for p in all_assets if p.burst]
    burst_key = [p for p in burst if p.burst_key]
    burst_selected = [p for p in burst if p.burst_selected]
    burst_default_pick = [p for p in burst if p.burst_default_pick]
    burst_non_selected = get_non_selected_bursts(photosdb)

    live = [p for p in all_assets if p.live_photo]
    hdr = [p for p in all_assets if p.hdr]
    selfie = [p for p in all_assets if p.selfie]
    panorama = [p for p in all_assets if p.panorama]
    slow_mo = [p for p in all_assets if p.slow_mo]
    time_lapse = [p for p in all_assets if p.time_lapse]
    screenshot = [p for p in all_assets if p.screenshot]
    # screen_recording = [p for p in all_assets if p.screen_recording]
    portrait = [p for p in all_assets if p.portrait]

    has_keywords = [p for p in all_assets if p.keywords]
    no_keywords = [p for p in all_assets if not p.keywords]
    has_title = [p for p in all_assets if p.title]
    no_title = [p for p in all_assets if not p.title]
    has_caption = [p for p in all_assets if p.description]
    no_caption = [p for p in all_assets if not p.description]

    # only non-shared photos are analyzed
    has_persons = [p for p in all_photos_app if p.persons]
    no_persons = [p for p in all_photos_app if not p.persons]
    has_ai_labels = [p for p in all_photos_app if p.labels]
    no_ai_labels = [p for p in all_photos_app if not p.labels]

    has_unnamed_persons = get_unnamed_person_photos(photosdb)

    categories = {}
    categories["all"] = all_assets
    categories["all_photos"] = all_photos
    categories["all_videos"] = all_videos
    categories["all_photos_app"] = all_photos_app
    categories["photos"] = photos
    categories["videos"] = videos
    categories["in_trash"] = in_trash
    categories["missing"] = missing
    categories["missing_photos"] = missing_photos
    categories["missing_videos"] = missing_videos
    categories["cloud_asset"] = cloud_asset
    categories["incloud"] = incloud
    categories["not_incloud"] = not_incloud
    categories["not_downloaded"] = not_downloaded
    categories["isreference"] = isreference
    categories["isreference_photos"] = isreference_photos
    categories["isreference_videos"] = isreference_videos
    categories["shared_library"] = shared_library
    categories["shared_library_photos"] = shared_library_photos
    categories["shared_library_videos"] = shared_library_videos
    categories["shared"] = shared
    categories["shared_photos"] = shared_photos
    categories["shared_videos"] = shared_videos
    categories["shared_moment"] = shared_moment
    categories["syndicated"] = syndicated
    categories["syndicated_saved_to_library"] = syndicated_saved_to_library
    categories["syndicated_not_saved_to_library"] = syndicated_not_saved_to_library
    categories["hidden"] = hidden
    categories["hidden_photos"] = hidden_photos
    categories["hidden_videos"] = hidden_videos
    categories["favorite"] = favorite
    categories["favorite_photos"] = favorite_photos
    categories["favorite_videos"] = favorite_videos
    categories["hasadjustments"] = hasadjustments
    categories["hasadjustments_photos"] = hasadjustments_photos
    categories["hasadjustments_videos"] = hasadjustments_videos
    categories["external_edit"] = external_edit
    categories["visible"] = visible
    categories["not_visible"] = not_visible
    categories["location"] = location
    categories["no_location"] = no_location
    categories["reverse_geo"] = reverse_geo
    categories["burst"] = burst
    categories["burst_key"] = burst_key
    categories["burst_selected"] = burst_selected
    categories["burst_default_pick"] = burst_default_pick
    categories["burst_non_selected"] = burst_non_selected
    categories["live"] = live
    categories["hdr"] = hdr
    categories["selfie"] = selfie
    categories["panorama"] = panorama
    categories["slow_mo"] = slow_mo
    categories["time_lapse"] = time_lapse
    categories["screenshot"] = screenshot
    # categories["screen_recording"] = screen_recording
    categories["portrait"] = portrait

    categories["has_raw"] = has_raw
    categories["is_raw"] = is_raw
    categories["has_keywords"] = has_keywords
    categories["no_keywords"] = no_keywords
    categories["has_title"] = has_title
    categories["no_title"] = no_title
    categories["has_caption"] = has_caption
    categories["no_caption"] = no_caption
    categories["has_ai_labels"] = has_ai_labels
    categories["no_ai_labels"] = no_ai_labels
    categories["has_persons"] = has_persons
    categories["no_persons"] = no_persons
    categories["has_unnamed_persons"] = has_unnamed_persons

    return categories


def get_photosdb_counts(photosdb: osxphotos.PhotosDB) -> dict[str, Any]:
    """Return dict of various counts in PhotosDB"""
    counts = {}
    counts["persons_count"] = get_persons_count(photosdb)
    counts["detected_faces"] = get_detected_face_count(photosdb)
    counts["manual_faces"] = get_manual_face_count(photosdb)
    counts["keywords_count"] = (
        len(photosdb.keywords)
        if not isinstance(photosdb, iPhotoDB)
        else len(photosdb.keywords_as_dict)
    )
    counts["albums_count"] = len(photosdb.album_info)
    counts["folders"] = (
        len(photosdb.folder_info) if not isinstance(photosdb, iPhotoDB) else 0
    )
    counts["shared_albums"] = (
        len(photosdb.album_info_shared) if not isinstance(photosdb, iPhotoDB) else 0
    )
    counts["import_groups"] = (
        len(photosdb.import_info) if not isinstance(photosdb, iPhotoDB) else 0
    )

    counts["keywords"] = photosdb.keywords_as_dict
    counts["albums"] = photosdb.albums_as_dict
    counts["persons"] = photosdb.persons_as_dict
    counts["labels"] = (
        photosdb.labels_as_dict if not isinstance(photosdb, iPhotoDB) else dict()
    )

    # moment_info is not implemented for PhotosDB (#1496)
    # so count unique momentID in each photo._info
    moment_ids = set()
    if not isinstance(photosdb, iPhotoDB):
        for p in photosdb.photos():
            moment_ids.add(p._info["momentID"])
    counts["moments"] = len(moment_ids)
    return counts


def get_photo_counts(photosdb: osxphotos.PhotosDB) -> dict[str, int]:
    """Return dict of photo counts"""
    categories = get_photo_categories(photosdb)
    counts = {k: len(v) for k, v in categories.items()}
    counts |= get_photosdb_counts(photosdb)
    counts["non_analyzed"] = len(get_non_analyzed_assets(photosdb))
    counts["analyzed"] = counts["all_photos_app"] - counts["non_analyzed"]
    counts["latest_analysis_date"] = get_latest_analysis_date(photosdb)
    counts |= {
        "database_path": photosdb.db_path,
        "database_version": photosdb.db_version,
        "database_model_version": photosdb._model_ver,
        "photos_version": photosdb.photos_version,
    }
    return counts


def print_counts_json(counts: dict[str, Any]):
    """Print counts as JSON"""

    def _default(o):
        if isinstance(o, (datetime.datetime)):
            return o.isoformat()

    print(json.dumps(counts, default=_default, indent=4))


def num(n: int) -> str:
    """Return number as string rich tags"""
    return f"[num]{n}[/]"


def header(s: str, extra: str = "") -> str:
    """Return header formatted with rich tags"""
    h = f"[b]{s}[/]"
    if extra:
        h = f"{h} ([i]{extra}[/])"
    return h


def bold(s: str) -> str:
    """Add rich tags to bold an item"""
    return f"[b]{s}[/]"


def total_photo_video(all: int, photos: int, videos: int) -> str:
    """Return formatted string for all, photos, videos"""
    return f"total: {num(all)}, photos: {num(photos)}, videos: {num(videos)}"


def echo_dict_counts(data: dict[str, int]):
    """Print out key, value for dicts such as persons"""
    for k, v in data.items():
        echo(f"{k}: [num]{v}[/]")


def print_counts(counts: dict[str, int], photosdb: osxphotos.PhotosDB, verbose: bool):
    """Print counts report"""
    echo(f"[b]Library:[/] [filepath]{photosdb.library_path}[/]")
    echo(
        "[b]DB Version:[/] "
        + num(photosdb.db_version)
        + ", [b]DB Model Version:[/] "
        + num(photosdb._model_ver)
        + ", [b]Photos version: [/]"
        + num(photosdb.photos_version)
    )
    if isinstance(photosdb, iPhotoDB):
        echo(
            "[i]Note: this is an iPhoto library; not all info data is available for iPhoto libraries"
        )
    echo(
        header(
            "Total Assets",
            "includes hidden, shared, syndicated which do not appear in Photos.app counts",
        )
    )
    echo(total_photo_video(counts["all"], counts["all_photos"], counts["all_videos"]))
    echo(header("Photo App Totals", "excludes hidden, shared, syndicated"))
    echo(
        total_photo_video(counts["all_photos_app"], counts["photos"], counts["videos"])
    )

    echo(header("In Trash", "Recently Deleted album"))
    echo("total: " + num(counts["in_trash"]))
    echo(header("Hidden", "assets in hidden albums"))
    echo(
        total_photo_video(
            counts["hidden"], counts["hidden_photos"], counts["hidden_videos"]
        )
    )
    echo(
        header(
            "Missing",
            "assets which are missing from the library, for example, not downloaded from iCloud",
        )
    )
    echo(
        total_photo_video(
            counts["missing"], counts["missing_photos"], counts["missing_videos"]
        )
    )

    echo(
        header(
            "Cloud Assets",
            "includes assets tracked by iCloud but not shared albums; includes hidden iCloud assets",
        )
    )
    echo(
        "total: "
        + num(counts["cloud_asset"])
        + ", in iCloud: "
        + num(counts["incloud"])
        + ", not uploaded to iCloud: "
        + num(counts["not_incloud"])
        + ", not downloaded to this Mac: "
        + num(counts["not_downloaded"])
    )

    echo(
        header(
            "Referenced Files", "files which have not been copied to the Photos library"
        )
    )
    echo(
        total_photo_video(
            counts["isreference"],
            counts["isreference_photos"],
            counts["isreference_videos"],
        )
    )

    echo(header("Shared Library", "photos shared via iCloud shared library"))
    echo(
        total_photo_video(
            counts["shared_library"],
            counts["shared_library_photos"],
            counts["shared_library_videos"],
        )
    )

    echo(header("Shared", "photos shared via iCloud shared albums"))
    echo(
        total_photo_video(
            counts["shared"], counts["shared_photos"], counts["shared_videos"]
        )
    )
    echo(header("Shared Moments", "moments shared in Messages"))
    echo("total: " + num(counts["shared_moment"]))
    echo(header("Syndicated", "photos shared via Messages or other apps"))
    echo(
        "total: "
        + num(counts["syndicated"])
        + ", saved to library: "
        + num(counts["syndicated_saved_to_library"])
        + ", not saved to library: "
        + num(counts["syndicated_not_saved_to_library"])
    )

    echo(header("Favorite", "photos marked as favorites"))
    echo(
        total_photo_video(
            counts["favorite"], counts["favorite_photos"], counts["favorite_videos"]
        )
    )

    echo(header("Edited"))
    echo(
        total_photo_video(
            counts["hasadjustments"],
            counts["hasadjustments_photos"],
            counts["hasadjustments_videos"],
        )
    )
    echo("edited in external application: " + num(counts["external_edit"]))

    echo(
        header(
            "Location",
            "location information (excludes shared assets which do not have location data)",
        )
    )
    echo(
        "total with location: "
        + num(counts["location"])
        + ", valid reverse geolocation data: "
        + num(counts["reverse_geo"])
        + ", no location: "
        + num(counts["no_location"])
    )

    echo(header("Bursts", "non-selected bursts are not included in total photo counts"))
    echo(
        "total: "
        + num(counts["burst"])
        + ", key photos: "
        + num(counts["burst_key"])
        + ", selected by user: "
        + num(counts["burst_selected"])
        + ", default selected by Photos: "
        + num(counts["burst_default_pick"])
        + ", non-selected images: "
        + num(counts["burst_non_selected"])
    )

    echo(header("Media Types"))
    echo(
        "live photos: "
        + num(counts["live"])
        + ", HDR: "
        + num(counts["hdr"])
        + ", selfies: "
        + num(counts["selfie"])
        + ", panoramas: "
        + num(counts["panorama"])
        + ", slow motion: "
        + num(counts["slow_mo"])
        + ", time lapse: "
        + num(counts["time_lapse"])
        + ", screenshots: "
        + num(counts["screenshot"])
        # + ", screen recordings: "
        # + num(counts["screen_recording"])
        + ", portrait: "
        + num(counts["portrait"])
    )

    echo(header("RAW Photos"))
    echo(
        "RAW photos: "
        + num(counts["is_raw"])
        + ", RAW+JPEG pairs: "
        + num(counts["has_raw"])
    )

    echo(header("Metadata"))
    echo(
        "has keywords: "
        + num(counts["has_keywords"])
        + ", no keywords: "
        + num(counts["no_keywords"])
    )
    echo(
        "has title: "
        + num(counts["has_title"])
        + ", no title: "
        + num(counts["no_title"])
    )
    echo(
        "has caption: "
        + num(counts["has_caption"])
        + ", no caption: "
        + num(counts["no_caption"])
    )

    echo(header("AI Analysis", "statistics for AI analysis, face detection, etc."))
    echo(f"last analysis date: [time]{counts['latest_analysis_date']}[/]")
    echo(
        "analyzed: "
        + num(counts["analyzed"])
        + ", not yet analyzed: "
        + num(counts["non_analyzed"])
    )
    echo(
        "has persons: "
        + num(counts["has_persons"])
        + ", no persons: "
        + num(counts["no_persons"])
    )
    echo("has unnamed persons: " + num(counts["has_unnamed_persons"]))
    echo(
        "has AI labels: "
        + num(counts["has_ai_labels"])
        + ", no AI labels: "
        + num(counts["no_ai_labels"])
    )

    echo(
        header(
            "Library Statistics",
            "counts of persons, keywords, albums, etc. in the Photos library",
        )
    )
    echo("named persons: " + num(counts["persons_count"]))
    echo("detected faces: " + num(counts["detected_faces"]))
    echo("manually added faces: " + num(counts["manual_faces"]))

    echo("keywords: " + num(counts["keywords_count"]))

    echo(
        "albums: "
        + num(counts["albums_count"])
        + ", shared albums: "
        + num(counts["shared_albums"])
        + ", folders: "
        + num(counts["folders"])
    )

    echo("import groups: " + num(counts["import_groups"]))
    echo("moments: " + num(counts["moments"]))

    if not verbose:
        return
    echo(
        header(
            "Person Details ",
            "photos with detected faces/persons; persons with duplicate names are shown combined",
        )
    )
    echo_dict_counts(counts["persons"])

    echo(header("Album Details ", "photo counts by albums"))
    echo_dict_counts(counts["albums"])

    echo(header("Keyword Details ", "photo counts by keywords"))
    echo_dict_counts(counts["keywords"])

    echo(
        header(
            "Labels/Categories Details ",
            "photo counts by AI-generated labels/categories",
        )
    )
    echo_dict_counts(counts["labels"])


@click.command()
@click.option("--verbose", "-V", count=True, help="Print verbose output.")
@DB_OPTION
@JSON_OPTION
@click.pass_obj
@click.pass_context
def info(ctx, cli_obj, verbose, db, json_):
    """Print out descriptive info of the Photos library database.

    Use --verbose to see additional details such as detailed counts of keywords, etc.
    """

    # needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(db, cli_db)
    if db is None:
        click.echo(ctx.obj.group.commands["info"].get_help(ctx), err=True)
        click.echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    echo(f"Loading library: {db}", err=True)
    photosdb = iPhotoDB(db) if is_iphoto_library(db) else PhotosDB(dbfile=db)
    counts = get_photo_counts(photosdb)

    if json_:
        print_counts_json(counts)
    else:
        print_counts(counts, photosdb, verbose)
