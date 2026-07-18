"""Methods for PhotosDB to add Photos 5 search info such as machine learning labels
Kudos to Simon Willison who figured out how to extract this data from psi.sql
ref: https://github.com/dogsheep/photos-to-sqlite/issues/16
"""

import logging
import pathlib
import struct
import uuid as uuidlib
from functools import lru_cache

from .._constants import _PHOTOS_4_VERSION, search_category_factory
from ..sqlite_utils import sqlite_db_is_locked, sqlite_open_ro
from ..unicode import normalize_unicode

"""
    This module should be imported in the class defintion of PhotosDB in photosdb.py
    Do not import this module directly
    This module adds the following method to PhotosDB:
        _process_searchinfo: process search terms from psi.sqlite 

    The following properties are added to PhotosDB    
        labels: list of all labels in the library
        labels_normalized: list of all labels normalized in the library  
        labels_as_dict: dict of {label: count of photos} in reverse sorted order (most photos first)
        labels_normalized_as_dict: dict of {normalized label: count of photos} in reverse sorted order (most photos first)

    The following data structures are added to PhotosDB
        self._db_searchinfo_categories
        self._db_searchinfo_uuid
        self._db_searchinfo_labels 
        self._db_searchinfo_labels_normalized 
    
    These methods only work on Photos 5 databases.  Will print warning on earlier library versions.
"""

logger = logging.getLogger("osxphotos")

LEO_CATEGORY_TO_PHOTOS8 = {
    1010: 1100,  # MONTH
    1020: 1101,  # YEAR
    1030: 1103,  # HOLIDAY
    1040: 1104,  # SEASON
    1050: 1106,  # TIME_OF_DAY
    1060: 1107,  # WEEKPART
    2030: 1701,  # VENUE_TYPE
    2050: 2,  # STREET
    2060: 1,  # PLACE_NAME
    2070: 3,  # NEIGHBORHOOD
    2090: 5,  # CITY
    2110: 7,  # NAMED_AREA
    2140: 10,  # STATE
    2150: 11,  # STATE_ABBREVIATION
    2160: 12,  # COUNTRY
    3001: 1300,  # PERSON
    4000: 1500,  # LABEL
    4010: 1510,  # RICH_LABEL
    4120: 1203,  # DETECTED_TEXT
    5000: 1900,  # PHOTO_TYPE_PHOTO
    5020: 1902,  # PHOTO_TYPE_RAW
    6000: 2300,  # CAMERA
    7000: 1201,  # TITLE
    7010: 1400,  # ALBUM
    8000: 2000,  # PHOTO_TYPE_FAVORITES
    8050: 2100,  # PHOTO_NAME
    8070: 1200,  # KEYWORDS
    8080: 1202,  # DESCRIPTION / caption
}


def _process_searchinfo(self):
    """load machine learning/search term label info from a Photos library
    db_connection: a connection to the SQLite database file containing the
    search terms.  In Photos 5, this is called psi.sqlite
    Note: Only works on Photos version == 5.0"""

    # _db_searchinfo_uuid is dict in form {uuid : [list of associated search info records]
    self._db_searchinfo_uuid = _db_searchinfo_uuid = {}

    # _db_searchinfo_categories is dict in form {search info category id: list normalized strings for the category
    # right now, this is mostly for debugging to easily see which search terms are in the library
    self._db_searchinfo_categories = _db_searchinfo_categories = {}

    # _db_searchinfo_labels is dict in form {normalized label: [list of photo uuids]}
    # this serves as a reverse index from label to photos containing the label
    # _db_searchinfo_labels_normalized is the same but with normalized (lower case) version of the label
    self._db_searchinfo_labels = _db_searchinfo_labels = {}
    self._db_searchinfo_labels_normalized = _db_searchinfo_labels_normalized = {}

    if self._skip_searchinfo:
        logger.debug("Skipping search info processing")
        return

    if self._db_version <= _PHOTOS_4_VERSION:
        raise NotImplementedError(
            "search info not implemented for this database version"
        )

    search_dir = pathlib.Path(self._dbfile).parent / "search"
    psi_db_path = search_dir / "psi.sqlite"
    leo_db_path = search_dir / "leo.sqlite"

    if psi_db_path.exists() and psi_db_path.stat().st_size:
        _process_psi_searchinfo(
            self,
            psi_db_path,
            _db_searchinfo_uuid,
            _db_searchinfo_categories,
            _db_searchinfo_labels,
            _db_searchinfo_labels_normalized,
        )
        return None

    if leo_db_path.exists() and leo_db_path.stat().st_size:
        _process_leo_searchinfo(
            self,
            leo_db_path,
            _db_searchinfo_uuid,
            _db_searchinfo_categories,
            _db_searchinfo_labels,
            _db_searchinfo_labels_normalized,
        )
        return None

    logger.warning(f"could not find search db: {psi_db_path} or {leo_db_path}")
    return None


def _process_psi_searchinfo(
    photosdb,
    search_db_path,
    db_searchinfo_uuid,
    db_searchinfo_categories,
    db_searchinfo_labels,
    db_searchinfo_labels_normalized,
):
    """Process Photos search data from psi.sqlite."""

    if sqlite_db_is_locked(search_db_path):
        search_db = photosdb._copy_db_file(search_db_path)
    else:
        search_db = search_db_path

    (conn, c) = sqlite_open_ro(search_db)

    result = c.execute(
        """
        select
        ga.rowid,
        assets.uuid_0,
        assets.uuid_1,
        groups.rowid as groupid,
        groups.category,
        groups.owning_groupid,
        groups.content_string,
        groups.normalized_string,
        groups.lookup_identifier
        from
        ga
        join groups on groups.rowid = ga.groupid
        join assets on ga.assetid = assets.rowid
        order by
        ga.rowid
        """
    )

    # 0: ga.rowid,
    # 1: assets.uuid_0,
    # 2: assets.uuid_1,
    # 3: groups.rowid as groupid,
    # 4: groups.category,
    # 5: groups.owning_groupid,
    # 6: groups.content_string,
    # 7: groups.normalized_string,
    # 8: groups.lookup_identifier

    for row in result:
        uuid = ints_to_uuid(row[1], row[2])
        # strings have null character appended, so strip it
        record = {
            "uuid": uuid,
            "rowid": row[0],
            "uuid_0": row[1],
            "uuid_1": row[2],
            "groupid": row[3],
            "category": row[4],
            "owning_groupid": row[5],
            "content_string": normalize_unicode(row[6].replace("\x00", "")),
        }

        record["normalized_string"] = normalize_unicode(row[7].replace("\x00", ""))
        record["lookup_identifier"] = normalize_unicode(row[8].replace("\x00", ""))

        try:
            db_searchinfo_uuid[uuid].append(record)
        except KeyError:
            db_searchinfo_uuid[uuid] = [record]

        category = record["category"]
        try:
            db_searchinfo_categories[category].append(record["normalized_string"])
        except KeyError:
            db_searchinfo_categories[category] = [record["normalized_string"]]

        categories = search_category_factory(photosdb._photos_ver)
        if category == categories.LABEL:
            label = record["content_string"]
            label_norm = record["normalized_string"]
            try:
                db_searchinfo_labels[label].append(uuid)
                db_searchinfo_labels_normalized[label_norm].append(uuid)
            except KeyError:
                db_searchinfo_labels[label] = [uuid]
                db_searchinfo_labels_normalized[label_norm] = [uuid]

    conn.close()


def _process_leo_searchinfo(
    photosdb,
    search_db_path,
    db_searchinfo_uuid,
    db_searchinfo_categories,
    db_searchinfo_labels,
    db_searchinfo_labels_normalized,
):
    """Process macOS 27 Photos search data from leo.sqlite."""

    if sqlite_db_is_locked(search_db_path):
        search_db = photosdb._copy_db_file(search_db_path)
    else:
        search_db = search_db_path

    (conn, c) = sqlite_open_ro(search_db)
    categories = search_category_factory(photosdb._photos_ver)

    lexeme_category = {}
    lexeme_content = {}
    result = c.execute("SELECT lexeme_id, type, category, content FROM lexicon")
    for lexeme_id, lexeme_type, leo_category, content in result:
        mapped_category = LEO_CATEGORY_TO_PHOTOS8.get(leo_category)
        if mapped_category is None:
            continue
        lexeme_category[lexeme_id] = mapped_category
        if lexeme_type == 1 and content:
            lexeme_content[lexeme_id] = normalize_unicode(content.replace("\x00", ""))

    result = c.execute(
        """
        SELECT identifier, lexeme_ids
        FROM items
        WHERE type = 1
        ORDER BY rowid
        """
    )

    rowid = 0
    for identifier, lexeme_ids_blob in result:
        if not identifier:
            continue
        uuid = identifier.upper()
        records = []
        for lexeme_id in decode_leo_lexeme_ids(lexeme_ids_blob):
            category = lexeme_category.get(lexeme_id)
            content_string = lexeme_content.get(lexeme_id)
            if category is None or not content_string:
                continue

            rowid += 1
            normalized_string = normalize_unicode(content_string.lower())
            record = {
                "uuid": uuid,
                "rowid": rowid,
                "uuid_0": 0,
                "uuid_1": 0,
                "groupid": lexeme_id,
                "category": category,
                "owning_groupid": None,
                "content_string": content_string,
                "normalized_string": normalized_string,
                "lookup_identifier": "",
            }
            records.append(record)

            try:
                db_searchinfo_categories[category].append(normalized_string)
            except KeyError:
                db_searchinfo_categories[category] = [normalized_string]

            if category == categories.LABEL:
                try:
                    db_searchinfo_labels[content_string].append(uuid)
                    db_searchinfo_labels_normalized[normalized_string].append(uuid)
                except KeyError:
                    db_searchinfo_labels[content_string] = [uuid]
                    db_searchinfo_labels_normalized[normalized_string] = [uuid]

        if records:
            db_searchinfo_uuid[uuid] = sorted(records, key=lambda rec: rec["rowid"])

    conn.close()


@property
def labels(self):
    """return list of all search info labels found in the library"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logger.warning("SearchInfo not implemented for this library version")
        return []

    return list(self._db_searchinfo_labels.keys())


@property
def labels_normalized(self):
    """return list of all normalized search info labels found in the library"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logger.warning("SearchInfo not implemented for this library version")
        return []

    return list(self._db_searchinfo_labels_normalized.keys())


@property
def labels_as_dict(self):
    """return labels as dict of label: count in reverse sorted order (descending)"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logger.warning("SearchInfo not implemented for this library version")
        return {}

    labels = {k: len(v) for k, v in self._db_searchinfo_labels.items()}
    labels = dict(sorted(labels.items(), key=lambda kv: kv[1], reverse=True))
    return labels


@property
def labels_normalized_as_dict(self):
    """return normalized labels as dict of label: count in reverse sorted order (descending)"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logger.warning("SearchInfo not implemented for this library version")
        return {}
    labels = {k: len(v) for k, v in self._db_searchinfo_labels_normalized.items()}
    labels = dict(sorted(labels.items(), key=lambda kv: kv[1], reverse=True))
    return labels


# The following method is not imported into PhotosDB


@lru_cache(maxsize=128)
def ints_to_uuid(uuid_0, uuid_1):
    """convert two signed ints into a UUID strings
    uuid_0, uuid_1: the two int components of an RFC 4122 UUID"""

    # assumes uuid imported as uuidlib (to avoid namespace conflict with other uses of uuid)

    bytes_ = uuid_0.to_bytes(8, "little", signed=True) + uuid_1.to_bytes(
        8, "little", signed=True
    )
    return str(uuidlib.UUID(bytes=bytes_)).upper()


def decode_leo_lexeme_ids(data):
    """Decode leo.sqlite little-endian UInt32 lexeme IDs."""
    if not data:
        return []
    count = len(data) // 4
    return list(struct.unpack(f"<{count}I", data[: count * 4]))
