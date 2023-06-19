""" Methods for PhotosDB to add Photos 5 search info such as machine learning labels 
    Kudos to Simon Willison who figured out how to extract this data from psi.sql
    ref: https://github.com/dogsheep/photos-to-sqlite/issues/16
"""

import logging
import pathlib
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

    search_db_path = pathlib.Path(self._dbfile).parent / "search" / "psi.sqlite"
    if not search_db_path.exists():
        logging.warning(f"could not find search db: {search_db_path}")
        return None

    if sqlite_db_is_locked(search_db_path):
        search_db = self._copy_db_file(search_db_path)
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
            _db_searchinfo_uuid[uuid].append(record)
        except KeyError:
            _db_searchinfo_uuid[uuid] = [record]

        category = record["category"]
        try:
            _db_searchinfo_categories[category].append(record["normalized_string"])
        except KeyError:
            _db_searchinfo_categories[category] = [record["normalized_string"]]

        categories = search_category_factory(self._photos_ver)
        if category == categories.LABEL:
            label = record["content_string"]
            label_norm = record["normalized_string"]
            try:
                _db_searchinfo_labels[label].append(uuid)
                _db_searchinfo_labels_normalized[label_norm].append(uuid)
            except KeyError:
                _db_searchinfo_labels[label] = [uuid]
                _db_searchinfo_labels_normalized[label_norm] = [uuid]

    conn.close()


@property
def labels(self):
    """return list of all search info labels found in the library"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logging.warning("SearchInfo not implemented for this library version")
        return []

    return list(self._db_searchinfo_labels.keys())


@property
def labels_normalized(self):
    """return list of all normalized search info labels found in the library"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logging.warning("SearchInfo not implemented for this library version")
        return []

    return list(self._db_searchinfo_labels_normalized.keys())


@property
def labels_as_dict(self):
    """return labels as dict of label: count in reverse sorted order (descending)"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logging.warning("SearchInfo not implemented for this library version")
        return {}

    labels = {k: len(v) for k, v in self._db_searchinfo_labels.items()}
    labels = dict(sorted(labels.items(), key=lambda kv: kv[1], reverse=True))
    return labels


@property
def labels_normalized_as_dict(self):
    """return normalized labels as dict of label: count in reverse sorted order (descending)"""
    if self._db_version <= _PHOTOS_4_VERSION:
        logging.warning("SearchInfo not implemented for this library version")
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
