""" Helper class for managing database used by PhotoExporter for tracking state of exports and updates """

from __future__ import annotations

import datetime
import gzip
import json
import logging
import os
import os.path
import pathlib
import pickle
import re
import sqlite3
import sys
import threading
import time
from contextlib import suppress
from io import StringIO
from sqlite3 import Error
from typing import Any

from tenacity import retry, retry_if_not_exception_type, stop_after_attempt

import osxphotos

from ._constants import OSXPHOTOS_EXPORT_DB, SQLITE_CHECK_SAME_THREAD
from ._version import __version__
from .fileutil import FileUtil
from .sqlite_utils import (
    sqlite_backup_dbfiles,
    sqlite_delete_backup_files,
    sqlite_delete_dbfiles,
)
from .unicode import normalize_fs_path

__all__ = [
    "ExportDB",
    "ExportDBInMemory",
    "ExportDBTemp",
]

OSXPHOTOS_EXPORTDB_VERSION = "8.0"
OSXPHOTOS_ABOUT_STRING = f"Created by osxphotos version {__version__} (https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"

# max retry attempts for methods which use tenacity.retry
MAX_RETRY_ATTEMPTS = 3

# maximum number of export results rows to save
MAX_EXPORT_RESULTS_DATA_ROWS = 10


logger = logging.getLogger("osxphotos")


def retry_log_error_no_raise(retry_state):
    """Log error for retry but don't raise exception"""
    logger.debug(
        f"Error {retry_state.outcome} for {retry_state.fn.__name__}({retry_state.args}, {retry_state.kwargs}); retrying...",
    )


def pickle_and_zip(data: Any) -> bytes:
    """
    Pickle and gzip data.

    Args:
        data: data to pickle and gzip (must be pickle-able)

    Returns:
        bytes of gzipped pickled data
    """
    pickled = pickle.dumps(data)
    return gzip.compress(pickled)


def unzip_and_unpickle(data: bytes) -> Any:
    """
    Unzip and unpickle data.

    Args:
        data: data to unzip and unpickle

    Returns:
        unpickled data
    """
    return pickle.loads(gzip.decompress(data))


class ExportDB:
    """Interface to sqlite3 database used to store state information for osxphotos export command"""

    def __init__(self, dbfile: pathlib.Path | str, export_dir: pathlib.Path | str):
        """create a new ExportDB object

        Args:
            dbfile: path to osxphotos export database file
            export_dir: path to directory where exported files are stored
            memory: if True, use in-memory database
        """

        self._dbfile: str = str(dbfile)
        # export_dir is required as all files referenced by get_/set_uuid_for_file will be converted to
        # relative paths to this path
        # this allows the entire export tree to be moved to a new disk/location
        # whilst preserving the UUID to filename mapping
        self._path: str = str(export_dir)
        self.was_upgraded: tuple[str, str] | tuple = ()
        self.was_created = False

        self.lock = threading.Lock()

        self._conn = self._open_export_db(self._dbfile)
        self._perform_db_maintenance(self._conn)
        self._insert_run_info()

    @property
    def path(self) -> str:
        """returns path to export database"""
        return self._dbfile

    @property
    def export_dir(self) -> str:
        """returns path to export directory"""
        return self._path

    @property
    def connection(self) -> sqlite3.Connection:
        """returns sqlite3 connection"""
        return self._conn or self._get_db_connection(self._dbfile)

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_file_record(self, filename: pathlib.Path | str) -> "ExportRecord" | None:
        """get info for filename

        Returns: an ExportRecord object or None if filename not found
        """
        filename = self._relative_filepath(filename)
        filename_normalized = self._normalize_filepath(filename)

        with self.lock:
            conn = self.connection
            c = conn.cursor()
            result = c.execute(
                "SELECT uuid FROM export_data WHERE filepath_normalized = ?;",
                (filename_normalized,),
            ).fetchone()
        return ExportRecord(conn, self.lock, filename_normalized) if result else None

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry=retry_if_not_exception_type(sqlite3.IntegrityError),
    )
    def create_file_record(
        self, filename: pathlib.Path | str, uuid: str
    ) -> "ExportRecord":
        """create a new record for filename and uuid

        Returns: an ExportRecord object
        """
        filename = self._relative_filepath(filename)
        filename_normalized = self._normalize_filepath(filename)

        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "INSERT INTO export_data (filepath, filepath_normalized, uuid) VALUES (?, ?, ?);",
                (filename, filename_normalized, uuid),
            )
            conn.commit()
        return ExportRecord(conn, self.lock, filename_normalized)

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry=retry_if_not_exception_type(sqlite3.IntegrityError),
    )
    def create_or_get_file_record(
        self, filename: pathlib.Path | str, uuid: str
    ) -> "ExportRecord":
        """create a new record for filename and uuid or return existing record

        Returns: an ExportRecord object
        """
        filename = self._relative_filepath(filename)
        filename_normalized = self._normalize_filepath(filename)

        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO export_data (filepath, filepath_normalized, uuid) VALUES (?, ?, ?);",
                (filename, filename_normalized, uuid),
            )
            conn.commit()
        return ExportRecord(conn, self.lock, filename_normalized)

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_uuid_for_file(self, filename: str) -> str | None:
        """query database for filename and return UUID
        returns None if filename not found in database
        """
        filepath_normalized = self._normalize_filepath_relative(filename)

        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "SELECT uuid FROM export_data WHERE filepath_normalized = ?",
                (filepath_normalized,),
            )
            results = c.fetchone()
            return results[0] if results else None

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_files_for_uuid(self, uuid: str) -> list[str]:
        """query database for UUID and return list of files associated with UUID or empty list"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "SELECT filepath FROM export_data WHERE uuid = ?",
                (uuid,),
            )
            results = c.fetchall()
            return [os.path.join(self.export_dir, r[0]) for r in results]

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_photoinfo_for_uuid(self, uuid: str) -> str | None:
        """returns the photoinfo JSON string for a UUID or None if not found"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute("SELECT photoinfo FROM photoinfo WHERE uuid = ?", (uuid,))
            results = c.fetchone()
            return results[0] if results else None

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry=retry_if_not_exception_type(sqlite3.IntegrityError),
    )
    def set_photoinfo_for_uuid(self, uuid: str, info: str):
        """sets the photoinfo JSON string for a UUID"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO photoinfo(uuid, photoinfo) VALUES (?, ?);",
                (uuid, info),
            )
            conn.commit()

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_target_for_file(
        self, uuid: str, filename: pathlib.Path | str
    ) -> str | None:
        """query database for file matching file name and return the matching filename if there is one;
           otherwise return None; looks for file.ext, file (1).ext, file (2).ext and so on to find the
           actual target name that was used to export filename

        Returns: the matching filename or None if no match found
        """
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            filepath_normalized = self._normalize_filepath_relative(filename)
            filepath_stem = os.path.splitext(filepath_normalized)[0]
            c.execute(
                "SELECT uuid, filepath, filepath_normalized FROM export_data WHERE uuid = ? AND filepath_normalized LIKE ?",
                (
                    uuid,
                    f"{filepath_stem}%",
                ),
            )
            results = c.fetchall()

            for result in results:
                filepath_normalized = os.path.splitext(result[2])[0]
                if re.match(
                    re.escape(filepath_stem) + r"(\s\(\d+\))?$", filepath_normalized
                ):
                    return os.path.join(self.export_dir, result[1])

            return None

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_previous_uuids(self):
        """returns list of UUIDs of previously exported photos found in export database"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute("SELECT DISTINCT uuid FROM export_data")
            results = c.fetchall()
            return [row[0] for row in results]

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry=retry_if_not_exception_type(sqlite3.IntegrityError),
    )
    def set_config(self, config_data: str):
        """set config in the database"""
        with self.lock:
            conn = self.connection
            dt = datetime.datetime.now().isoformat()
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO config(datetime, config) VALUES (?, ?);",
                (dt, config_data),
            )
            conn.commit()

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry=retry_if_not_exception_type(sqlite3.IntegrityError),
    )
    def set_export_results(self, results: "osxphotos.photoexporter.ExportResults"):
        """Store export results in database; data is pickled and gzipped for storage"""

        results_data = pickle_and_zip(results)

        with self.lock:
            conn = self.connection
            dt = datetime.datetime.now().isoformat()
            c = conn.cursor()
            c.execute(
                """
                UPDATE export_results_data
                SET datetime = ?,
                    export_results = ?
                WHERE datetime = (SELECT MIN(datetime) FROM export_results_data);
                """,
                (dt, results_data),
            )
            conn.commit()

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_export_results(
        self, run: int = 0
    ) -> "osxphotos.photoexporter.ExportResults" | None:
        """Retrieve export results from database

        Args:
            run: which run to retrieve results for;
            0 = most recent run, -1 = previous run, -2 = run prior to that, etc.

        Returns:
            ExportResults object or None if no results found
        """
        if run > 0:
            raise ValueError("run must be 0 or negative")
        run = -run

        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                """
                SELECT export_results
                FROM export_results_data
                ORDER BY datetime DESC
                """,
            )
            rows = c.fetchall()
            try:
                data = rows[run][0]
                results = unzip_and_unpickle(data) if data else None
            except IndexError:
                results = None
            return results

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def get_exported_files(self):
        """Returns tuple of (uuid, filepath) for all paths of all exported files tracked in the database"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute("SELECT uuid, filepath FROM export_data")

            while row := c.fetchone():
                yield row[0], os.path.join(self.export_dir, row[1])
            return

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def delete_data_for_uuid(self, uuid: str):
        """Delete all exportdb data for given UUID"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            count = 0
            c.execute("DELETE FROM export_data WHERE uuid = ?;", (uuid,))
            count += c.execute("SELECT CHANGES();").fetchone()[0]
            c.execute("DELETE FROM photoinfo WHERE uuid = ?;", (uuid,))
            count += c.execute("SELECT CHANGES();").fetchone()[0]
            conn.commit()
            return count

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def delete_data_for_filepath(self, filepath: pathlib.Path | str):
        """Delete all exportdb data for given filepath"""
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            filepath_normalized = self._normalize_filepath_relative(filepath)
            results = c.execute(
                "SELECT uuid FROM export_data WHERE filepath_normalized = ?;",
                (filepath_normalized,),
            ).fetchall()
            return sum(self.delete_data_for_uuid(row[0]) for row in results)

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def close(self):
        """close the database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def _open_export_db(self, dbfile: str) -> sqlite3.Connection:
        """open export database and return a db connection
        if dbfile does not exist, will create and initialize the database
        if dbfile needs to be upgraded, will perform needed migrations
        returns: connection to the database
        """

        if not os.path.isfile(dbfile):
            conn = self._get_db_connection(dbfile)
            self._create_or_migrate_db_tables(conn)
            self.was_created = True
            self.was_upgraded = ()
        else:
            conn = self._get_db_connection(dbfile)
            self.was_created = False
            version_info = self._get_database_version(conn)
            if version_info[1] < OSXPHOTOS_EXPORTDB_VERSION:
                self._create_or_migrate_db_tables(conn)
                self.was_upgraded = (version_info[1], OSXPHOTOS_EXPORTDB_VERSION)
            else:
                self.was_upgraded = ()
        self.version = OSXPHOTOS_EXPORTDB_VERSION

        # turn on performance optimizations
        with self.lock:
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
            c.execute("PRAGMA cache_size=-100000;")
            c.execute("PRAGMA temp_store=MEMORY;")

        return conn

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def _get_db_connection(self, dbfile: str) -> sqlite3.Connection:
        """return db connection to dbname"""
        return sqlite3.connect(dbfile, check_same_thread=SQLITE_CHECK_SAME_THREAD)

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def _get_database_version(self, conn: sqlite3.Connection) -> tuple[str, str]:
        """return tuple of (osxphotos, exportdb) versions for database connection conn"""
        with self.lock:
            version_info = conn.execute(
                "SELECT osxphotos, exportdb, max(id) FROM version"
            ).fetchone()
            return (version_info[0], version_info[1])

    def _create_or_migrate_db_tables(self, conn: sqlite3.Connection):
        """create (if not already created) the necessary db tables for the export database and apply any needed migrations

        Args:
            conn: sqlite3 db connection
        """
        try:
            version = self._get_database_version(conn)
        except Exception as e:
            version = (__version__, "4.3")

        # Current for version 4.3, for anything greater, do a migration after creation
        sql_commands = [
            """ CREATE TABLE IF NOT EXISTS version (
                    id INTEGER PRIMARY KEY,
                    osxphotos TEXT,
                    exportdb TEXT 
                    ); """,
            """ CREATE TABLE IF NOT EXISTS about (
                    id INTEGER PRIMARY KEY,
                    about TEXT
                    );""",
            """ CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT NOT NULL,
                    filepath_normalized TEXT NOT NULL,
                    uuid TEXT,
                    orig_mode INTEGER,
                    orig_size INTEGER,
                    orig_mtime REAL,
                    exif_mode INTEGER,
                    exif_size INTEGER,
                    exif_mtime REAL
                    ); """,
            """ CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY,
                    datetime TEXT,
                    python_path TEXT,
                    script_name TEXT,
                    args TEXT,
                    cwd TEXT 
                    ); """,
            """ CREATE TABLE IF NOT EXISTS info (
                    id INTEGER PRIMARY KEY,
                    uuid text NOT NULL,
                    json_info JSON 
                    ); """,
            """ CREATE TABLE IF NOT EXISTS exifdata (
                    id INTEGER PRIMARY KEY,
                    filepath_normalized TEXT NOT NULL,
                    json_exifdata JSON 
                    ); """,
            """ CREATE TABLE IF NOT EXISTS edited (
                    id INTEGER PRIMARY KEY,
                    filepath_normalized TEXT NOT NULL,
                    mode INTEGER,
                    size INTEGER,
                    mtime REAL
                    ); """,
            """ CREATE TABLE IF NOT EXISTS converted (
                    id INTEGER PRIMARY KEY,
                    filepath_normalized TEXT NOT NULL,
                    mode INTEGER,
                    size INTEGER,
                    mtime REAL
                    ); """,
            """ CREATE TABLE IF NOT EXISTS sidecar (
                    id INTEGER PRIMARY KEY,
                    filepath_normalized TEXT NOT NULL,
                    sidecar_data TEXT,
                    mode INTEGER,
                    size INTEGER,
                    mtime REAL
                    ); """,
            """ CREATE TABLE IF NOT EXISTS detected_text (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT NOT NULL,
                    text_data JSON
                    ); """,
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_files_filepath_normalized on files (filepath_normalized); """,
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_info_uuid on info (uuid); """,
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_exifdata_filename on exifdata (filepath_normalized); """,
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_edited_filename on edited (filepath_normalized);""",
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_converted_filename on converted (filepath_normalized);""",
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_sidecar_filename on sidecar (filepath_normalized);""",
            """ CREATE UNIQUE INDEX IF NOT EXISTS idx_detected_text on detected_text (uuid);""",
        ]
        # create the tables if needed
        with self.lock:
            c = conn.cursor()
            for cmd in sql_commands:
                c.execute(cmd)
            c.execute(
                "INSERT INTO version(osxphotos, exportdb) VALUES (?, ?);",
                (__version__, OSXPHOTOS_EXPORTDB_VERSION),
            )
            c.execute("INSERT INTO about(about) VALUES (?);", (OSXPHOTOS_ABOUT_STRING,))
            conn.commit()

        # perform needed migrations
        if version[1] < "4.3":
            self._migrate_normalized_filepath(conn)

        if version[1] < "5.0":
            self._migrate_4_3_to_5_0(conn)

        if version[1] < "6.0":
            # create export_data table
            self._migrate_5_0_to_6_0(conn)

        if version[1] < "7.0":
            # create report_data table
            self._migrate_6_0_to_7_0(conn)

        if version[1] < "7.1":
            # add timestamp to export_data
            self._migrate_7_0_to_7_1(conn)

        if version[1] < "8.0":
            # add error to export_data
            self._migrate_7_1_to_8_0(conn)

        with self.lock:
            conn.execute("VACUUM;")
            conn.commit()

    def __del__(self):
        """ensure the database connection is closed"""
        with suppress(Exception):
            self._conn.close()

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def _insert_run_info(self):
        dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
        python_path = sys.executable
        cmd = sys.argv[0]
        args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        cwd = os.getcwd()
        with self.lock:
            conn = self.connection
            c = conn.cursor()
            c.execute(
                "INSERT INTO runs (datetime, python_path, script_name, args, cwd) VALUES (?, ?, ?, ?, ?)",
                (dt, python_path, cmd, args, cwd),
            )
            conn.commit()

    def _relative_filepath(self, filepath: pathlib.Path | str) -> str:
        """return filepath relative to self._path"""
        return str(pathlib.Path(filepath).relative_to(self._path))

    def _normalize_filepath(self, filepath: pathlib.Path | str) -> str:
        """normalize filepath for unicode, lower case"""
        return normalize_fs_path(str(filepath)).lower()

    def _normalize_filepath_relative(self, filepath: pathlib.Path | str) -> str:
        """normalize filepath for unicode, relative path (to export dir), lower case"""
        filepath = self._relative_filepath(filepath)
        return normalize_fs_path(str(filepath)).lower()

    def _migrate_normalized_filepath(self, conn: sqlite3.Connection):
        """Fix all filepath_normalized columns for unicode normalization"""
        # Prior to database version 4.3, filepath_normalized was not normalized for unicode
        migration_sql = [
            """ CREATE TABLE IF NOT EXISTS files_migrate (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT NOT NULL,
                    filepath_normalized TEXT NOT NULL,
                    uuid TEXT,
                    orig_mode INTEGER,
                    orig_size INTEGER,
                    orig_mtime REAL,
                    exif_mode INTEGER,
                    exif_size INTEGER,
                    exif_mtime REAL,
                    UNIQUE(filepath_normalized)
                    ); """,
            """ INSERT INTO files_migrate SELECT * FROM files;""",
            """ DROP TABLE files;""",
            """ ALTER TABLE files_migrate RENAME TO files;""",
        ]

        with self.lock:
            c = conn.cursor()
            for sql in migration_sql:
                c.execute(sql)
            conn.commit()

            for table in ["converted", "edited", "exifdata", "files", "sidecar"]:
                old_values = c.execute(
                    f"SELECT filepath_normalized, id FROM {table}"
                ).fetchall()
                new_values = [
                    (self._normalize_filepath(filepath_normalized), id_)
                    for filepath_normalized, id_ in old_values
                ]
                c.executemany(
                    f"UPDATE {table} SET filepath_normalized=? WHERE id=?", new_values
                )
            conn.commit()

    def _migrate_4_3_to_5_0(self, conn: sqlite3.Connection):
        """Migrate database from version 4.3 to 5.0"""
        with self.lock:
            c = conn.cursor()
            # add metadata column to files to support --force-update
            c.execute("ALTER TABLE files ADD COLUMN metadata TEXT;")
            conn.commit()

    def _migrate_5_0_to_6_0(self, conn: sqlite3.Connection):
        with self.lock:
            c = conn.cursor()
            # add export_data table
            c.execute(
                """ CREATE TABLE IF NOT EXISTS export_data(
                        id INTEGER PRIMARY KEY,
                        filepath_normalized TEXT NOT NULL,
                        filepath TEXT NOT NULL,
                        uuid TEXT NOT NULL,
                        src_mode INTEGER,
                        src_size INTEGER,
                        src_mtime REAL,
                        dest_mode INTEGER,
                        dest_size INTEGER,
                        dest_mtime REAL,
                        digest TEXT,
                        exifdata JSON,
                        export_options INTEGER,
                        UNIQUE(filepath_normalized)
                    ); """,
            )
            c.execute(
                """ CREATE UNIQUE INDEX IF NOT EXISTS idx_export_data_filepath_normalized on export_data (filepath_normalized); """,
            )

            # migrate data
            c.execute(
                """ INSERT INTO export_data (filepath_normalized, filepath, uuid) SELECT filepath_normalized, filepath, uuid FROM files;""",
            )
            c.execute(
                """ UPDATE export_data 
                    SET (src_mode, src_size, src_mtime) = 
                    (SELECT mode, size, mtime 
                    FROM edited 
                    WHERE export_data.filepath_normalized = edited.filepath_normalized);
                """,
            )
            c.execute(
                """ UPDATE export_data 
                    SET (dest_mode, dest_size, dest_mtime) = 
                    (SELECT orig_mode, orig_size, orig_mtime 
                    FROM files 
                    WHERE export_data.filepath_normalized = files.filepath_normalized);
                """,
            )
            c.execute(
                """ UPDATE export_data SET digest = 
                            (SELECT metadata FROM files 
                            WHERE files.filepath_normalized = export_data.filepath_normalized
                            ); """
            )
            c.execute(
                """ UPDATE export_data SET exifdata = 
                            (SELECT json_exifdata FROM exifdata 
                            WHERE exifdata.filepath_normalized = export_data.filepath_normalized
                            ); """
            )

            # create config table
            c.execute(
                """ CREATE TABLE IF NOT EXISTS config (
                        id INTEGER PRIMARY KEY,
                        datetime TEXT,
                        config TEXT 
                ); """
            )

            # create photoinfo table
            c.execute(
                """ CREATE TABLE IF NOT EXISTS photoinfo (
                        id INTEGER PRIMARY KEY,
                        uuid TEXT NOT NULL,
                        photoinfo JSON,
                        UNIQUE(uuid)
                ); """
            )
            c.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_photoinfo_uuid on photoinfo (uuid);"""
            )
            c.execute(
                """ INSERT INTO photoinfo (uuid, photoinfo) SELECT uuid, json_info FROM info;"""
            )

            # drop indexes no longer needed
            c.execute("DROP INDEX IF EXISTS idx_files_filepath_normalized;")
            c.execute("DROP INDEX IF EXISTS idx_exifdata_filename;")
            c.execute("DROP INDEX IF EXISTS idx_edited_filename;")
            c.execute("DROP INDEX IF EXISTS idx_converted_filename;")
            c.execute("DROP INDEX IF EXISTS idx_sidecar_filename;")
            c.execute("DROP INDEX IF EXISTS idx_detected_text;")

            # drop tables no longer needed
            c.execute("DROP TABLE IF EXISTS files;")
            c.execute("DROP TABLE IF EXISTS info;")
            c.execute("DROP TABLE IF EXISTS exifdata;")
            c.execute("DROP TABLE IF EXISTS edited;")
            c.execute("DROP TABLE IF EXISTS converted;")
            c.execute("DROP TABLE IF EXISTS sidecar;")
            c.execute("DROP TABLE IF EXISTS detected_text;")

            conn.commit()

    def _migrate_6_0_to_7_0(self, conn: sqlite3.Connection):
        with self.lock:
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS export_results_data (
                        id INTEGER PRIMARY KEY,
                        datetime TEXT,
                        export_results BLOB
                );"""
            )
            # pre-populate report_data table with blank fields
            # ExportDB will use these as circular buffer always writing to the oldest record
            for _ in range(MAX_EXPORT_RESULTS_DATA_ROWS):
                c.execute(
                    """INSERT INTO export_results_data (datetime, export_results) VALUES (?, ?);""",
                    (datetime.datetime.now().isoformat(), b""),
                )
                # sleep a tiny bit just to ensure time stamps increment
                time.sleep(0.001)
            conn.commit()

    def _migrate_7_0_to_7_1(self, conn: sqlite3.Connection):
        """Add timestamp column to export_data table and triggers to update it on insert and update."""
        with self.lock:
            c = conn.cursor()
            # timestamp column should not exist but this prevents error if migration is run on an already migrated database
            # reference #794
            results = c.execute(
                "SELECT COUNT(*) FROM pragma_table_info('export_data') WHERE name='timestamp';"
            ).fetchone()
            if results[0] == 0:
                c.execute("""ALTER TABLE export_data ADD COLUMN timestamp DATETIME;""")
            c.execute(
                """
                CREATE TRIGGER IF NOT EXISTS insert_timestamp_trigger
                AFTER INSERT ON export_data
                BEGIN
                    UPDATE export_data SET timestamp = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE id = NEW.id;
                END;
                """
            )
            c.execute(
                """
                CREATE TRIGGER IF NOT EXISTS update_timestamp_trigger
                AFTER UPDATE On export_data
                BEGIN
                    UPDATE export_data SET timestamp = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE id = NEW.id;
                END;
                """
            )
            conn.commit()

    def _migrate_7_1_to_8_0(self, conn: sqlite3.Connection):
        """Add error column to export_data table"""
        with self.lock:
            c = conn.cursor()
            results = c.execute(
                "SELECT COUNT(*) FROM pragma_table_info('export_data') WHERE name='error';"
            ).fetchone()
            if results[0] == 0:
                c.execute("""ALTER TABLE export_data ADD COLUMN error JSON;""")
            conn.commit()

    def _perform_db_maintenance(self, conn: sqlite3.Connection):
        """Perform database maintenance"""
        with self.lock:
            c = conn.cursor()
            c.execute(
                """DELETE FROM config
                    WHERE id < (
                        SELECT MIN(id)
                        FROM (SELECT id FROM config ORDER BY id DESC LIMIT 9)
                    );
                """
            )
            conn.commit()


class ExportDBInMemory(ExportDB):
    """In memory version of ExportDB
    Copies the on-disk database into memory so it may be operated on without
    modifying the on-disk version
    """

    def __init__(self, dbfile: pathlib.Path | str, export_dir: pathlib.Path | str):
        """ "Initialize ExportDBInMemory

        Args:
            dbfile (str): path to database file
            export_dir (str): path to export directory
            write_back (bool): whether to write changes back to disk when closing; if False (default), changes are not written to disk
        """
        self._dbfile = str(dbfile) or f"./{OSXPHOTOS_EXPORT_DB}"
        # export_dir is required as all files referenced by get_/set_uuid_for_file will be converted to
        # relative paths to this path
        # this allows the entire export tree to be moved to a new disk/location
        # whilst preserving the UUID to filename mapping
        self._path = str(export_dir)

        self.was_upgraded: tuple[str, str] | tuple = ()
        self.was_created = False

        self.lock = threading.Lock()

        self._conn = self._open_export_db(self._dbfile)
        self._insert_run_info()

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def write_to_disk(self):
        """Write changes from in-memory database back to disk"""

        # dump the database
        with self.lock:
            conn = self.connection
            conn.commit()

            # backup the old database to disk
            # this is just in case the write fails
            # so the user can recover the database
            sqlite_backup_dbfiles(self._dbfile)

            # delete the old database if it exists
            if os.path.isfile(self._dbfile):
                sqlite_delete_dbfiles(self._dbfile)

            # write the new database to disk
            conn_on_disk = sqlite3.connect(
                str(self._dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD
            )
            conn.backup(conn_on_disk, pages=1)
            conn_on_disk.commit()
            conn_on_disk.close()

            # delete the backup
            sqlite_delete_backup_files(self._dbfile)

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        retry_error_callback=retry_log_error_no_raise,  # #999
    )
    def close(self):
        """close the database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    @retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS))
    def _open_export_db(self, dbfile: str):  # sourcery skip: raise-specific-error
        """open export database and return a db connection
        returns: connection to the database
        """
        if not os.path.isfile(dbfile):
            # database doesn't exist so create it in-memory
            src = self._get_db_connection()
            if not src:
                raise Exception("Error getting connection to in-memory database")
            self._create_or_migrate_db_tables(src)
            self.was_created = True
            self.was_upgraded = ()
            self.version = OSXPHOTOS_EXPORTDB_VERSION
            return src

        # database exists so copy it to memory
        src = sqlite3.connect(dbfile, check_same_thread=SQLITE_CHECK_SAME_THREAD)

        # Create a database in memory by backing up the on-disk database
        dst = sqlite3.connect(":memory:", check_same_thread=SQLITE_CHECK_SAME_THREAD)
        with dst:
            src.backup(dst, pages=1)
        src.close()

        self.was_created = False
        version_info = self._get_database_version(dst)
        if version_info[1] < OSXPHOTOS_EXPORTDB_VERSION:
            self._create_or_migrate_db_tables(dst)
            self.was_upgraded = (version_info[1], OSXPHOTOS_EXPORTDB_VERSION)
        else:
            self.was_upgraded = ()
        self.version = OSXPHOTOS_EXPORTDB_VERSION

        return dst

    def _get_db_connection(self):
        """return db connection to in memory database"""
        return sqlite3.connect(":memory:", check_same_thread=SQLITE_CHECK_SAME_THREAD)

    def _dump_db(self, conn: sqlite3.Connection) -> StringIO:
        """dump sqlite db to a string buffer"""

        dbdump = StringIO()
        for line in conn.iterdump():
            dbdump.write("%s\n" % line)
        dbdump.seek(0)
        return dbdump

    def __del__(self):
        """close the database connection"""
        with suppress(Error):
            self.close()


class ExportDBTemp(ExportDBInMemory):
    """Temporary in-memory version of ExportDB"""

    def __init__(self):
        self._dbfile = ":memory:"
        self._path = "./"

        self.lock = threading.Lock()

        self.was_upgraded = ()
        self.was_created = False

        self._conn = self._open_export_db(self._dbfile)
        self._insert_run_info()

    def _relative_filepath(self, filepath: pathlib.Path | str) -> str:
        """Overrides _relative_filepath to return a path for use in the temp db"""
        filepath = str(filepath)
        return filepath[1:] if filepath[0] == "/" else filepath


class ExportRecord:
    """ExportRecord class"""

    # Implementation note:all properties and setters must be aware of whether or not running
    # as a context manager. If running as a context manager, the lock is not acquired by the
    # getter/setter as the lock is acquired by the context manager.  If not running as a
    # context manager, the lock is acquired by the getter/setter.

    __slots__ = [
        "_conn",
        "_context_manager",
        "_filepath_normalized",
        "lock",
    ]

    def __init__(
        self, conn: sqlite3.Connection, lock: threading.Lock, filepath_normalized: str
    ):
        self._conn = conn
        self.lock = lock
        self._filepath_normalized = filepath_normalized
        self._context_manager = False

    @property
    def connection(self) -> sqlite3.Connection:
        """return connection"""
        return self._conn

    @property
    def filepath(self) -> str:
        """return filepath"""
        if self._context_manager:
            return self._filepath()
        with self.lock:
            return self._filepath()

    def _filepath(self) -> str:
        """return filepath"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT filepath FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return row[0]

        raise ValueError(
            f"No filepath found in database for {self._filepath_normalized}"
        )

    @property
    def filepath_normalized(self) -> str:
        """return filepath_normalized"""
        return self._filepath_normalized

    @property
    def uuid(self) -> str:
        """return uuid"""
        if self._context_manager:
            return self._uuid()
        with self.lock:
            return self._uuid()

    def _uuid(self) -> str:
        """return uuid"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT uuid FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return row[0]

        raise ValueError(f"No uuid found in database for {self._filepath_normalized}")

    @property
    def digest(self) -> str:
        """returns the digest value"""
        if self._context_manager:
            return self._digest()
        with self.lock:
            return self._digest()

    @digest.setter
    def digest(self, value: str):
        """set digest value"""
        if self._context_manager:
            self._digest_setter(value)
        else:
            with self.lock:
                self._digest_setter(value)

    def _digest(self) -> str:
        """returns the digest value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT digest FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return row[0]

        raise ValueError(f"No digest found in database for {self._filepath_normalized}")

    def _digest_setter(self, value: str):
        """set digest value"""
        conn = self.connection
        c = conn.cursor()
        c.execute(
            "UPDATE export_data SET digest = ? WHERE filepath_normalized = ?;",
            (value, self._filepath_normalized),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def exifdata(self) -> str:
        """returns exifdata value for record"""
        if self._context_manager:
            return self._exifdata()
        with self.lock:
            return self._exifdata()

    @exifdata.setter
    def exifdata(self, value: str):
        """set exifdata value"""
        if self._context_manager:
            self._exifdata_setter(value)
        else:
            with self.lock:
                self._exifdata_setter(value)

    def _exifdata(self) -> str:
        """returns exifdata value for record"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT exifdata FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return row[0]

        raise ValueError(
            f"No exifdata found in database for {self._filepath_normalized}"
        )

    def _exifdata_setter(self, value: str):
        """set exifdata value"""
        conn = self.connection
        c = conn.cursor()
        c.execute(
            "UPDATE export_data SET exifdata = ? WHERE filepath_normalized = ?;",
            (
                value,
                self._filepath_normalized,
            ),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def src_sig(self) -> tuple[int, int, int | None]:
        """return source file signature value"""
        if self._context_manager:
            return self._src_sig()
        with self.lock:
            return self._src_sig()

    @src_sig.setter
    def src_sig(self, value: tuple[int, int, int | None]):
        """set source file signature value"""
        if self._context_manager:
            self._src_sig_setter(value)
        else:
            with self.lock:
                self._src_sig_setter(value)

    def _src_sig(self) -> tuple[int, int, int | None]:
        """return source file signature value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT src_mode, src_size, src_mtime FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            mtime = int(row[2]) if row[2] is not None else None
            return (row[0], row[1], mtime)

        raise ValueError(
            f"No src_sig found in database for {self._filepath_normalized}"
        )

    def _src_sig_setter(self, value: tuple[int, int, int | None]):
        """set source file signature value"""
        conn = self.connection
        c = conn.cursor()
        c.execute(
            "UPDATE export_data SET src_mode = ?, src_size = ?, src_mtime = ? WHERE filepath_normalized = ?;",
            (
                value[0],
                value[1],
                value[2],
                self._filepath_normalized,
            ),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def dest_sig(self) -> tuple[int, int, int | None]:
        """return destination file signature"""
        if self._context_manager:
            return self._dest_sig()
        with self.lock:
            return self._dest_sig()

    @dest_sig.setter
    def dest_sig(self, value: tuple[int, int, int | None]):
        """set destination file signature"""
        if self._context_manager:
            self._dest_sig_setter(value)
        else:
            with self.lock:
                self._dest_sig_setter(value)

    def _dest_sig(self) -> tuple[int, int, int | None]:
        """return destination file signature"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT dest_mode, dest_size, dest_mtime FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            mtime = int(row[2]) if row[2] is not None else None
            return (row[0], row[1], mtime)

        raise ValueError(
            f"No dest_sig found in database for {self._filepath_normalized}"
        )

    def _dest_sig_setter(self, value: tuple[int, int, int | None]):
        """set destination file signature"""
        conn = self.connection
        c = conn.cursor()
        c.execute(
            "UPDATE export_data SET dest_mode = ?, dest_size = ?, dest_mtime = ? WHERE filepath_normalized = ?;",
            (
                value[0],
                value[1],
                value[2],
                self._filepath_normalized,
            ),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def photoinfo(self) -> str:
        """Returns info value"""
        if self._context_manager:
            return self._photoinfo()
        with self.lock:
            return self._photoinfo()

    @photoinfo.setter
    def photoinfo(self, value: str):
        """Sets info value"""
        if self._context_manager:
            self._photoinfo_setter(value)
        else:
            with self.lock:
                self._photoinfo_setter(value)

    def _photoinfo(self) -> str:
        """Returns info value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT uuid FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            uuid = row[0]
        else:
            raise ValueError(
                f"No uuid found in database for {self._filepath_normalized}"
            )
        row = c.execute(
            "SELECT photoinfo from photoinfo where uuid = ?;",
            (uuid,),
        ).fetchone()
        return row[0] if row else None

    def _photoinfo_setter(self, value: str):
        """Sets info value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT uuid FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            uuid = row[0]
        else:
            raise ValueError(
                f"No uuid found in database for {self._filepath_normalized}"
            )
        c.execute(
            "INSERT OR REPLACE INTO photoinfo (uuid, photoinfo) VALUES (?, ?);",
            (uuid, value),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def export_options(self) -> str:
        """Get export_options value"""
        if self._context_manager:
            return self._export_options()
        with self.lock:
            return self._export_options()

    @export_options.setter
    def export_options(self, value: str):
        """Set export_options value"""
        if self._context_manager:
            self._export_options_setter(value)
        else:
            with self.lock:
                self._export_options_setter(value)

    def _export_options(self) -> str:
        """Get export_options value"""
        conn = self.connection
        c = conn.cursor()
        row = c.execute(
            "SELECT export_options from export_data where filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone()
        return row[0] if row else None

    def _export_options_setter(self, value: str):
        """Set export_options value"""
        conn = self.connection
        c = conn.cursor()
        c.execute(
            "UPDATE export_data SET export_options = ? WHERE filepath_normalized = ?;",
            (value, self._filepath_normalized),
        )
        if not self._context_manager:
            conn.commit()

    @property
    def timestamp(self) -> str:
        """returns the timestamp value"""
        if self._context_manager:
            return self._timestamp()
        with self.lock:
            return self._timestamp()

    def _timestamp(self) -> str:
        """returns the timestamp value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT timestamp FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return row[0]

        raise ValueError(
            f"No timestamp found in database for {self._filepath_normalized}"
        )

    @property
    def error(self) -> dict[str, Any] | None:
        """Return error value"""
        if self._context_manager:
            return self._error()
        with self.lock:
            return self._error()

    @error.setter
    def error(self, value: dict[str, str] | None):
        """Set error value"""
        if self._context_manager:
            self._error_setter(value)
        else:
            with self.lock:
                self._error_setter(value)

    def _error(self) -> dict[str, Any] | None:
        """Return error value"""
        conn = self.connection
        c = conn.cursor()
        if row := c.execute(
            "SELECT error FROM export_data WHERE filepath_normalized = ?;",
            (self._filepath_normalized,),
        ).fetchone():
            return json.loads(row[0]) if row[0] else None

        raise ValueError(f"No error found in database for {self._filepath_normalized}")

    def _error_setter(self, value: dict[str, str] | None):
        """Set error value"""
        value = value or {}
        conn = self.connection
        c = conn.cursor()
        # use default=str because some of the values are Path objects
        error = json.dumps(value, default=str)
        c.execute(
            "UPDATE export_data SET error = ? WHERE filepath_normalized = ?;",
            (error, self._filepath_normalized),
        )
        if not self._context_manager:
            conn.commit()

    def asdict(self) -> dict[str, Any]:
        """Return dict of self"""
        exifdata = json.loads(self.exifdata) if self.exifdata else None
        photoinfo = json.loads(self.photoinfo) if self.photoinfo else None
        return {
            "filepath": self.filepath,
            "filepath_normalized": self.filepath_normalized,
            "uuid": self.uuid,
            "timestamp": self.timestamp,
            "digest": self.digest,
            "src_sig": self.src_sig,
            "dest_sig": self.dest_sig,
            "export_options": self.export_options,
            "exifdata": exifdata,
            "error": self.error,
            "photoinfo": photoinfo,
        }

    def json(self, indent=None) -> str:
        """Return json string of self"""
        return json.dumps(self.asdict(), indent=indent)

    def __enter__(self):
        self._context_manager = True
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and self._conn.in_transaction:
            self._conn.rollback()
        elif self._conn.in_transaction:
            self._conn.commit()
        self._context_manager = False
        self.lock.release()
