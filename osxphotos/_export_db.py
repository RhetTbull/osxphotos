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

OSXPHOTOS_EXPORTDB_VERSION = "1.0"


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
    def set_data(self, filename, uuid, orig_stat, exif_stat, info_json, exif_json):
        pass


class ExportDBNoOp(ExportDB_ABC):
    """ An ExportDB with NoOp methods """

    def get_uuid_for_file(self, filename):
        pass

    def set_uuid_for_file(self, filename, uuid):
        pass

    def set_stat_orig_for_file(self, filename, stats):
        pass

    def get_stat_orig_for_file(self, filename):
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

    def set_data(self, filename, uuid, orig_stat, exif_stat, info_json, exif_json):
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
        logging.debug(f"get_uuid: {filename}")
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

        logging.debug(f"get_uuid: {uuid}")
        return uuid

    def set_uuid_for_file(self, filename, uuid):
        """ set UUID of filename to uuid in the database """
        filename = str(pathlib.Path(filename).relative_to(self._path))
        filename_normalized = filename.lower()
        logging.debug(f"set_uuid: {filename} {uuid}")
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

        logging.debug(f"set_stat_orig_for_file: {filename} {stats}")
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
            stats = results[0:3] if results else None
        except Error as e:
            logging.warning(e)
            stats = (None, None, None)

        logging.debug(f"get_stat_orig_for_file: {stats}")
        return stats

    def set_stat_exif_for_file(self, filename, stats):
        """ set stat info for filename (after exiftool has updated it)
            filename: filename to set the stat info for
            stat: a tuple of length 3: mode, size, mtime """
        filename = str(pathlib.Path(filename).relative_to(self._path)).lower()
        if len(stats) != 3:
            raise ValueError(f"expected 3 elements for stat, got {len(stats)}")

        logging.debug(f"set_stat_exif_for_file: {filename} {stats}")
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
            stats = results[0:3] if results else None
        except Error as e:
            logging.warning(e)
            stats = (None, None, None)

        logging.debug(f"get_stat_exif_for_file: {stats}")
        return stats

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

        logging.debug(f"get_info: {uuid}, {info}")
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

        logging.debug(f"set_info: {uuid}, {info}")

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

        logging.debug(f"get_exifdata: {filename}, {exifdata}")
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

        logging.debug(f"set_exifdata: {filename}, {exifdata}")

    def set_data(self, filename, uuid, orig_stat, exif_stat, info_json, exif_json):
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

    def _open_export_db(self, dbfile):
        """ open export database and return a db connection
            if dbfile does not exist, will create and initialize the database 
            returns: connection to the database 
        """

        if not os.path.isfile(dbfile):
            logging.debug(f"dbfile {dbfile} doesn't exist, creating it")
            conn = self._get_db_connection(dbfile)
            if conn:
                self._create_db_tables(conn)
            else:
                raise Exception("Error getting connection to database {dbfile}")
        else:
            logging.debug(f"dbfile {dbfile} exists, opening it")
            conn = self._get_db_connection(dbfile)

        return conn

    def _get_db_connection(self, dbfile):
        """ return db connection to dbname """
        try:
            conn = sqlite3.connect(dbfile)
        except Error as e:
            logging.warning(e)
            conn = None

        return conn

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
            "sql_files_idx": """ CREATE UNIQUE INDEX idx_files_filepath_normalized on files (filepath_normalized); """,
            "sql_info_idx": """ CREATE UNIQUE INDEX idx_info_uuid on info (uuid); """,
            "sql_exifdata_idx": """ CREATE UNIQUE INDEX idx_exifdata_filename on exifdata (filepath_normalized); """,
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
        if self._conn:
            try:
                self._conn.close()
            except Error as e:
                logging.warning(e)

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
            if dbfile does not exist, will create and initialize the database 
            returns: connection to the database 
        """
        if not os.path.isfile(dbfile):
            logging.debug(f"dbfile {dbfile} doesn't exist, creating in memory version")
            conn = self._get_db_connection()
            if conn:
                self._create_db_tables(conn)
            else:
                raise Exception("Error getting connection to in-memory database")
        else:
            logging.debug(f"dbfile {dbfile} exists, opening it and copying to memory")
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

        return conn

    def _get_db_connection(self):
        """ return db connection to in memory database """
        try:
            conn = sqlite3.connect(":memory:")
        except Error as e:
            logging.warning(e)
            conn = None

        return conn
