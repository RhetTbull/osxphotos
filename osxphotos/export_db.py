""" Helper class for managing a database used by 
    PhotoInfo.export for tracking state of exports and updates
"""

import datetime
import logging
import os
import pathlib
import sqlite3
import sys
from abc import ABC, abstractmethod
from io import StringIO
from sqlite3 import Error

from ._version import __version__

OSXPHOTOS_EXPORTDB_VERSION = "3.2"


class ExportDB_ABC(ABC):
    """ abstract base class for ExportDB """

    @abstractmethod
    def get_uuid_for_file(self, filename):
        pass

    @abstractmethod
    def set_uuid_for_file(self, filename, uuid):
        pass

    @abstractmethod
    def set_stat_orig_for_file(self, filename, stats):
        pass

    @abstractmethod
    def get_stat_orig_for_file(self, filename):
        pass

    @abstractmethod
    def set_stat_edited_for_file(self, filename, stats):
        pass

    @abstractmethod
    def get_stat_edited_for_file(self, filename):
        pass

    @abstractmethod
    def set_stat_converted_for_file(self, filename, stats):
        pass

    @abstractmethod
    def get_stat_converted_for_file(self, filename):
        pass

    @abstractmethod
    def set_stat_exif_for_file(self, filename, stats):
        pass

    @abstractmethod
    def get_stat_exif_for_file(self, filename):
        pass

    @abstractmethod
    def get_info_for_uuid(self, uuid):
        pass

    @abstractmethod
    def set_info_for_uuid(self, uuid, info):
        pass

    @abstractmethod
    def get_exifdata_for_file(self, uuid):
        pass

    @abstractmethod
    def set_exifdata_for_file(self, uuid, exifdata):
        pass

    @abstractmethod
    def set_sidecar_for_file(self, filename, sidecar_data, sidecar_sig):
        pass

    @abstractmethod
    def get_sidecar_for_file(self, filename):
        pass

    @abstractmethod
    def get_previous_uuids(self):
        pass

    @abstractmethod
    def set_data(
        self,
        filename,
        uuid,
        orig_stat,
        exif_stat,
        converted_stat,
        edited_stat,
        info_json,
        exif_json,
    ):
        pass


class ExportDBNoOp(ExportDB_ABC):
    """ An ExportDB with NoOp methods """

    def __init__(self):
        self.was_created = True
        self.was_upgraded = False
        self.version = OSXPHOTOS_EXPORTDB_VERSION

    def get_uuid_for_file(self, filename):
        pass

    def set_uuid_for_file(self, filename, uuid):
        pass

    def set_stat_orig_for_file(self, filename, stats):
        pass

    def get_stat_orig_for_file(self, filename):
        pass

    def set_stat_edited_for_file(self, filename, stats):
        pass

    def get_stat_edited_for_file(self, filename):
        pass

    def set_stat_converted_for_file(self, filename, stats):
        pass

    def get_stat_converted_for_file(self, filename):
        pass

    def set_stat_exif_for_file(self, filename, stats):
        pass

    def get_stat_exif_for_file(self, filename):
        pass

    def get_info_for_uuid(self, uuid):
        pass

    def set_info_for_uuid(self, uuid, info):
        pass

    def get_exifdata_for_file(self, uuid):
        pass

    def set_exifdata_for_file(self, uuid, exifdata):
        pass

    def set_sidecar_for_file(self, filename, sidecar_data, sidecar_sig):
        pass

    def get_sidecar_for_file(self, filename):
        return None, (None, None, None)

    def get_previous_uuids(self):
        return []

    def set_data(
        self,
        filename,
        uuid,
        orig_stat,
        exif_stat,
        converted_stat,
        edited_stat,
        info_json,
        exif_json,
    ):
        pass


class ExportDB(ExportDB_ABC):
    """ Interface to sqlite3 database used to store state information for osxphotos export command """

    def __init__(self, dbfile):
        """ dbfile: path to osxphotos export database file """
        self._dbfile = dbfile
        # _path is parent of the database
        # all files referenced by get_/set_uuid_for_file will be converted to
        # relative paths to this parent _path
        # this allows the entire export tree to be moved to a new disk/location
        # whilst preserving the UUID to filename mappping
        self._path = pathlib.Path(dbfile).parent
        self._conn = self._open_export_db(dbfile)
        self._insert_run_info()

    def get_uuid_for_file(self, filename):
        """ query database for filename and return UUID
            returns None if filename not found in database
        """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                f"SELECT uuid FROM files WHERE filepath_normalized = ?", (filename,)
            )
            results = c.fetchone()
            uuid = results[0] if results else None
        except Error as e:
            logging.warning(e)
            uuid = None

        return uuid

    def set_uuid_for_file(self, filename, uuid):
        """ set UUID of filename to uuid in the database """
        filename = str(pathlib.Path(filename).relative_to(self._path))
        filename_normalized = filename.lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                f"INSERT OR REPLACE INTO files(filepath, filepath_normalized, uuid) VALUES (?, ?, ?);",
                (filename, filename_normalized, uuid),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def set_stat_orig_for_file(self, filename, stats):
        """ set stat info for filename
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        if len(stats) != 3:
            raise ValueError(f"expected 3 elements for stat, got {len(stats)}")

        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE files "
                + "SET orig_mode = ?, orig_size = ?, orig_mtime = ? "
                + "WHERE filepath_normalized = ?;",
                (*stats, filename),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def get_stat_orig_for_file(self, filename):
        """ get stat info for filename
            returns: tuple of (mode, size, mtime) 
        """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "SELECT orig_mode, orig_size, orig_mtime FROM files WHERE filepath_normalized = ?",
                (filename,),
            )
            results = c.fetchone()
            if results:
                stats = results[0:3]
                mtime = int(stats[2]) if stats[2] is not None else None
                stats = (stats[0], stats[1], mtime)
            else:
                stats = (None, None, None)
        except Error as e:
            logging.warning(e)
            stats = (None, None, None)

        return stats

    def set_stat_edited_for_file(self, filename, stats):
        """ set stat info for edited version of image (in Photos' library)
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        return self._set_stat_for_file("edited", filename, stats)

    def get_stat_edited_for_file(self, filename):
        """ get stat info for edited version of image (in Photos' library)
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        return self._get_stat_for_file("edited", filename)

    def set_stat_exif_for_file(self, filename, stats):
        """ set stat info for filename (after exiftool has updated it)
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        if len(stats) != 3:
            raise ValueError(f"expected 3 elements for stat, got {len(stats)}")

        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE files "
                + "SET exif_mode = ?, exif_size = ?, exif_mtime = ? "
                + "WHERE filepath_normalized = ?;",
                (*stats, filename),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def get_stat_exif_for_file(self, filename):
        """ get stat info for filename (after exiftool has updated it)
            returns: tuple of (mode, size, mtime) 
        """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "SELECT exif_mode, exif_size, exif_mtime FROM files WHERE filepath_normalized = ?",
                (filename,),
            )
            results = c.fetchone()
            if results:
                stats = results[0:3]
                mtime = int(stats[2]) if stats[2] is not None else None
                stats = (stats[0], stats[1], mtime)
            else:
                stats = (None, None, None)
        except Error as e:
            logging.warning(e)
            stats = (None, None, None)

        return stats

    def set_stat_converted_for_file(self, filename, stats):
        """ set stat info for filename (after image converted to jpeg)
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        return self._set_stat_for_file("converted", filename, stats)

    def get_stat_converted_for_file(self, filename):
        """ get stat info for filename (after jpeg conversion)
            returns: tuple of (mode, size, mtime) 
        """
        return self._get_stat_for_file("converted", filename)

    def get_info_for_uuid(self, uuid):
        """ returns the info JSON struct for a UUID """
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute("SELECT json_info FROM info WHERE uuid = ?", (uuid,))
            results = c.fetchone()
            info = results[0] if results else None
        except Error as e:
            logging.warning(e)
            info = None

        return info

    def set_info_for_uuid(self, uuid, info):
        """ sets the info JSON struct for a UUID """
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO info(uuid, json_info) VALUES (?, ?);",
                (uuid, info),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def get_exifdata_for_file(self, filename):
        """ returns the exifdata JSON struct for a file """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "SELECT json_exifdata FROM exifdata WHERE filepath_normalized = ?",
                (filename,),
            )
            results = c.fetchone()
            exifdata = results[0] if results else None
        except Error as e:
            logging.warning(e)
            exifdata = None

        return exifdata

    def set_exifdata_for_file(self, filename, exifdata):
        """ sets the exifdata JSON struct for a file """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO exifdata(filepath_normalized, json_exifdata) VALUES (?, ?);",
                (filename, exifdata),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def get_sidecar_for_file(self, filename):
        """ returns the sidecar data and signature for a file """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "SELECT sidecar_data, mode, size, mtime FROM sidecar WHERE filepath_normalized = ?",
                (filename,),
            )
            results = c.fetchone()
            if results:
                sidecar_data = results[0]
                sidecar_sig = (
                    results[1],
                    results[2],
                    int(results[3]) if results[3] is not None else None,
                )
            else:
                sidecar_data = None
                sidecar_sig = (None, None, None)
        except Error as e:
            logging.warning(e)
            sidecar_data = None
            sidecar_sig = (None, None, None)

        return sidecar_data, sidecar_sig

    def set_sidecar_for_file(self, filename, sidecar_data, sidecar_sig):
        """ sets the sidecar data and signature for a file """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO sidecar(filepath_normalized, sidecar_data, mode, size, mtime) VALUES (?, ?, ?, ?, ?);",
                (filename, sidecar_data, *sidecar_sig),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def get_previous_uuids(self):
        """returns list of UUIDs of previously exported photos found in export database """
        conn = self._conn
        previous_uuids = []
        try:
            c = conn.cursor()
            c.execute("SELECT DISTINCT uuid FROM files")
            results = c.fetchall()
            previous_uuids = [row[0] for row in results]
        except Error as e:
            logging.warning(e)
        return previous_uuids

    def set_data(
        self,
        filename,
        uuid,
        orig_stat,
        exif_stat,
        converted_stat,
        edited_stat,
        info_json,
        exif_json,
    ):
        """ sets all the data for file and uuid at once 
        """
        filename = str(pathlib.Path(filename).relative_to(self._path))
        filename_normalized = filename.lower()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                f"INSERT OR REPLACE INTO files(filepath, filepath_normalized, uuid) VALUES (?, ?, ?);",
                (filename, filename_normalized, uuid),
            )
            c.execute(
                "UPDATE files "
                + "SET orig_mode = ?, orig_size = ?, orig_mtime = ? "
                + "WHERE filepath_normalized = ?;",
                (*orig_stat, filename_normalized),
            )
            c.execute(
                "UPDATE files "
                + "SET exif_mode = ?, exif_size = ?, exif_mtime = ? "
                + "WHERE filepath_normalized = ?;",
                (*exif_stat, filename_normalized),
            )
            c.execute(
                "INSERT OR REPLACE INTO converted(filepath_normalized, mode, size, mtime) VALUES (?, ?, ?, ?);",
                (filename_normalized, *converted_stat),
            )
            c.execute(
                "INSERT OR REPLACE INTO edited(filepath_normalized, mode, size, mtime) VALUES (?, ?, ?, ?);",
                (filename_normalized, *edited_stat),
            )
            c.execute(
                "INSERT OR REPLACE INTO info(uuid, json_info) VALUES (?, ?);",
                (uuid, info_json),
            )
            c.execute(
                "INSERT OR REPLACE INTO exifdata(filepath_normalized, json_exifdata) VALUES (?, ?);",
                (filename_normalized, exif_json),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def close(self):
        """ close the database connection """
        try:
            self._conn.close()
        except Error as e:
            logging.warning(e)

    def _set_stat_for_file(self, table, filename, stats):
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        if len(stats) != 3:
            raise ValueError(f"expected 3 elements for stat, got {len(stats)}")

        conn = self._conn
        c = conn.cursor()
        c.execute(
            f"INSERT OR REPLACE INTO {table}(filepath_normalized, mode, size, mtime) VALUES (?, ?, ?, ?);",
            (filename, *stats),
        )
        conn.commit()

    def _get_stat_for_file(self, table, filename):
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        conn = self._conn
        c = conn.cursor()
        c.execute(
            f"SELECT mode, size, mtime FROM {table} WHERE filepath_normalized = ?",
            (filename,),
        )
        results = c.fetchone()
        if results:
            stats = results[0:3]
            mtime = int(stats[2]) if stats[2] is not None else None
            stats = (stats[0], stats[1], mtime)
        else:
            stats = (None, None, None)

        return stats

    def _open_export_db(self, dbfile):
        """ open export database and return a db connection
            if dbfile does not exist, will create and initialize the database 
            returns: connection to the database 
        """

        if not os.path.isfile(dbfile):
            conn = self._get_db_connection(dbfile)
            if not conn:
                raise Exception("Error getting connection to database {dbfile}")
            self._create_db_tables(conn)
            self.was_created = True
            self.was_upgraded = ()
        else:
            conn = self._get_db_connection(dbfile)
            self.was_created = False
            version_info = self._get_database_version(conn)
            if version_info[1] < OSXPHOTOS_EXPORTDB_VERSION:
                self._create_db_tables(conn)
                self.was_upgraded = (version_info[1], OSXPHOTOS_EXPORTDB_VERSION)
            else:
                self.was_upgraded = ()
        self.version = OSXPHOTOS_EXPORTDB_VERSION
        return conn

    def _get_db_connection(self, dbfile):
        """ return db connection to dbname """
        try:
            conn = sqlite3.connect(dbfile)
        except Error as e:
            logging.warning(e)
            conn = None

        return conn

    def _get_database_version(self, conn):
        """ return tuple of (osxphotos, exportdb) versions for database connection conn """
        version_info = conn.execute(
            "SELECT osxphotos, exportdb, max(id) FROM version"
        ).fetchone()
        return (version_info[0], version_info[1])

    def _create_db_tables(self, conn):
        """ create (if not already created) the necessary db tables for the export database
            conn: sqlite3 db connection 
        """
        sql_commands = {
            "sql_version_table": """ CREATE TABLE IF NOT EXISTS version (
                                id INTEGER PRIMARY KEY,
                                osxphotos TEXT,
                                exportdb TEXT 
                                ); """,
            "sql_files_table": """ CREATE TABLE IF NOT EXISTS files (
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
            "sql_runs_table": """ CREATE TABLE IF NOT EXISTS runs (
                             id INTEGER PRIMARY KEY,
                             datetime TEXT,
                             python_path TEXT,
                             script_name TEXT,
                             args TEXT,
                             cwd TEXT 
                             ); """,
            "sql_info_table": """ CREATE TABLE IF NOT EXISTS info (
                             id INTEGER PRIMARY KEY,
                             uuid text NOT NULL,
                             json_info JSON 
                             ); """,
            "sql_exifdata_table": """ CREATE TABLE IF NOT EXISTS exifdata (
                             id INTEGER PRIMARY KEY,
                             filepath_normalized TEXT NOT NULL,
                             json_exifdata JSON 
                             ); """,
            "sql_edited_table": """ CREATE TABLE IF NOT EXISTS edited (
                              id INTEGER PRIMARY KEY,
                              filepath_normalized TEXT NOT NULL,
                              mode INTEGER,
                              size INTEGER,
                              mtime REAL
                              ); """,
            "sql_converted_table": """ CREATE TABLE IF NOT EXISTS converted (
                              id INTEGER PRIMARY KEY,
                              filepath_normalized TEXT NOT NULL,
                              mode INTEGER,
                              size INTEGER,
                              mtime REAL
                              ); """,
            "sql_sidecar_table": """ CREATE TABLE IF NOT EXISTS sidecar (
                              id INTEGER PRIMARY KEY,
                              filepath_normalized TEXT NOT NULL,
                              sidecar_data TEXT,
                              mode INTEGER,
                              size INTEGER,
                              mtime REAL
                              ); """,
            "sql_files_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_files_filepath_normalized on files (filepath_normalized); """,
            "sql_info_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_info_uuid on info (uuid); """,
            "sql_exifdata_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_exifdata_filename on exifdata (filepath_normalized); """,
            "sql_edited_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_edited_filename on edited (filepath_normalized);""",
            "sql_converted_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_converted_filename on converted (filepath_normalized);""",
            "sql_sidecar_idx": """ CREATE UNIQUE INDEX IF NOT EXISTS idx_sidecar_filename on sidecar (filepath_normalized);""",
        }
        try:
            c = conn.cursor()
            for cmd in sql_commands.values():
                c.execute(cmd)
            c.execute(
                "INSERT INTO version(osxphotos, exportdb) VALUES (?, ?);",
                (__version__, OSXPHOTOS_EXPORTDB_VERSION),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)

    def __del__(self):
        """ ensure the database connection is closed """
        try:
            self._conn.close()
        except:
            pass

    def _insert_run_info(self):
        dt = datetime.datetime.utcnow().isoformat()
        python_path = sys.executable
        cmd = sys.argv[0]
        args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        cwd = os.getcwd()
        conn = self._conn
        try:
            c = conn.cursor()
            c.execute(
                f"INSERT INTO runs (datetime, python_path, script_name, args, cwd) VALUES (?, ?, ?, ?, ?)",
                (dt, python_path, cmd, args, cwd),
            )
            conn.commit()
        except Error as e:
            logging.warning(e)


class ExportDBInMemory(ExportDB):
    """ In memory version of ExportDB
        Copies the on-disk database into memory so it may be operated on without 
        modifying the on-disk verison 
    """

    def init(self, dbfile):
        self._dbfile = dbfile
        # _path is parent of the database
        # all files referenced by get_/set_uuid_for_file will be converted to
        # relative paths to this parent _path
        # this allows the entire export tree to be moved to a new disk/location
        # whilst preserving the UUID to filename mappping
        self._path = pathlib.Path(dbfile).parent
        self._conn = self._open_export_db(dbfile)
        self._insert_run_info()

    def _open_export_db(self, dbfile):
        """ open export database and return a db connection
            returns: connection to the database 
        """
        if not os.path.isfile(dbfile):
            conn = self._get_db_connection()
            if conn:
                self._create_db_tables(conn)
                self.was_created = True
                self.was_upgraded = ()
                self.version = OSXPHOTOS_EXPORTDB_VERSION
            else:
                raise Exception("Error getting connection to in-memory database")
        else:
            try:
                conn = sqlite3.connect(dbfile)
            except Error as e:
                logging.warning(e)
                raise e

            tempfile = StringIO()
            for line in conn.iterdump():
                tempfile.write("%s\n" % line)
            conn.close()
            tempfile.seek(0)

            # Create a database in memory and import from tempfile
            conn = sqlite3.connect(":memory:")
            conn.cursor().executescript(tempfile.read())
            conn.commit()
            self.was_created = False
            _, exportdb_ver = self._get_database_version(conn)
            if exportdb_ver < OSXPHOTOS_EXPORTDB_VERSION:
                self._create_db_tables(conn)
                self.was_upgraded = (exportdb_ver, OSXPHOTOS_EXPORTDB_VERSION)
            else:
                self.was_upgraded = ()
            self.version = OSXPHOTOS_EXPORTDB_VERSION

        return conn

    def _get_db_connection(self):
        """ return db connection to in memory database """
        try:
            conn = sqlite3.connect(":memory:")
        except Error as e:
            logging.warning(e)
            conn = None

        return conn
