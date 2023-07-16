"""Provide direct access to the database tables associated with a photo."""

from __future__ import annotations

import sqlite3
from typing import Any

import osxphotos

from ._constants import _DB_TABLE_NAMES


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


class PhotoTables:
    def __init__(self, photo: osxphotos.PhotoInfo):
        """Create a PhotoTables object.

        Args:
            db: PhotosDB object
            uuid: The UUID of the photo.
        """
        self.db = photo._db
        self.photo = photo
        self.uuid = photo.uuid
        self.version = self.db._photos_ver

    @property
    def ZASSET(self) -> Table:
        """Return the ZASSET table."""
        return AssetTable(self.db, self.version, self.uuid)

    @property
    def ZADDITIONALASSETATTRIBUTES(self) -> Table:
        """Return the ZADDITIONALASSETATTRIBUTES table."""
        return AdditionalAttributesTable(self.db, self.version, self.uuid)

    @property
    def ZDETECTEDFACE(self) -> Table:
        """Return the ZDETECTEDFACE table."""
        return DetectedFaceTable(self.db, self.version, self.uuid)

    @property
    def ZPERSON(self) -> Table:
        """Return the ZPERSON table."""
        return PersonTable(self.db, self.version, self.uuid)


class Table:
    def __init__(self, db: osxphotos.PhotosDB, version: int, uuid: str):
        """Create a Table object.

        Args:
            db: PhotosDB object
            table_name: The name of the table.
        """
        self.db = db
        self.conn, _ = self.db.get_db_connection()
        self.version = version
        self.uuid = uuid
        self.asset_table = _DB_TABLE_NAMES[self.version]["ASSET"]
        self.columns = []  # must be set in subclass
        self.table_name = ""  # must be set in subclass

    def rows(self) -> list[tuple[Any]]:
        """Return rows for this photo from the table."""
        # this should be implemented in the subclass
        raise NotImplementedError

    def rows_dict(self) -> list[dict[str, Any]]:
        """Return rows for this photo from the table as a list of dicts."""
        rows = self.rows()
        return [dict(zip(self.columns, row)) for row in rows] if rows else []

    def _get_column(self, column: str):
        """Get column value for this photo from the table."""
        # this should be implemented in the subclass
        raise NotImplementedError

    def __getattr__(self, name):
        """Get column value for this photo from the table."""
        if name not in self.__dict__ and name in self.columns:
            return self._get_column(name)
        else:
            raise AttributeError(f"Table {self.table_name} has no column {name}")


class AssetTable(Table):
    """ZASSET table."""

    def __init__(self, db: osxphotos.PhotosDB, version: int, uuid: str):
        """Create a Table object."""
        super().__init__(db, version, uuid)
        self.columns = get_table_columns(self.conn, self.asset_table)
        self.table_name = self.asset_table

    def rows(self) -> list[Any]:
        """Return row2 for this photo from the ZASSET table."""
        conn, cursor = self.db.get_db_connection()
        cursor.execute(
            f"SELECT * FROM {self.asset_table} WHERE ZUUID = ?", (self.uuid,)
        )
        return result if (result := cursor.fetchall()) else []

    def _get_column(self, column: str) -> tuple[Any]:
        """Get column value for this photo from the ZASSET table."""
        conn, cursor = self.db.get_db_connection()
        cursor.execute(
            f"SELECT {column} FROM {self.asset_table} WHERE ZUUID = ?",
            (self.uuid,),
        )
        return (
            tuple(result[0] for result in results)
            if (results := cursor.fetchall())
            else ()
        )


class AdditionalAttributesTable(Table):
    """ZADDITIONALASSETATTRIBUTES table."""

    def __init__(self, db: osxphotos.PhotosDB, version: int, uuid: str):
        """Create a Table object."""
        super().__init__(db, version, uuid)
        self.columns = get_table_columns(self.conn, "ZADDITIONALASSETATTRIBUTES")
        self.table_name = "ZADDITIONALASSETATTRIBUTES"

    def rows(self) -> list[tuple[Any]]:
        """Return rows for this photo from the ZADDITIONALASSETATTRIBUTES table."""
        conn, cursor = self.db.get_db_connection()
        sql = f"""  SELECT ZADDITIONALASSETATTRIBUTES.*
                    FROM ZADDITIONALASSETATTRIBUTES
                    JOIN {self.asset_table} ON {self.asset_table}.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSET
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return result if (result := cursor.fetchall()) else []

    def _get_column(self, column: str) -> tuple[Any]:
        """Get column value for this photo from the ZADDITIONALASSETATTRIBUTES table."""
        conn, cursor = self.db.get_db_connection()
        sql = f"""  SELECT ZADDITIONALASSETATTRIBUTES.{column}
                    FROM ZADDITIONALASSETATTRIBUTES
                    JOIN {self.asset_table} ON {self.asset_table}.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSET
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return (
            tuple(result[0] for result in results)
            if (results := cursor.fetchall())
            else ()
        )


class DetectedFaceTable(Table):
    """ZDETECTEDFACE table."""

    def __init__(self, db: osxphotos.PhotosDB, version: int, uuid: str):
        """Create a Table object."""
        super().__init__(db, version, uuid)
        self.columns = get_table_columns(self.conn, "ZDETECTEDFACE")
        self.table_name = "ZDETECTEDFACE"

    def rows(self) -> list[tuple[Any]]:
        """Return rows for this photo from the ZDETECTEDFACE table."""
        conn, cursor = self.db.get_db_connection()
        sql = f"""  SELECT ZDETECTEDFACE.*
                    FROM ZDETECTEDFACE
                    JOIN {self.asset_table} ON {self.asset_table}.Z_PK = ZDETECTEDFACE.ZASSET
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return result if (result := cursor.fetchall()) else []

    def _get_column(self, column: str) -> tuple[Any]:
        """Get column value for this photo from the ZDETECTEDFACE table."""
        conn, cursor = self.db.get_db_connection()
        sql = f"""  SELECT ZDETECTEDFACE.{column}
                    FROM ZDETECTEDFACE
                    JOIN {self.asset_table} ON {self.asset_table}.Z_PK = ZDETECTEDFACE.ZASSET
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return (
            tuple(result[0] for result in results)
            if (results := cursor.fetchall())
            else ()
        )


class PersonTable(Table):
    """ZPERSON table."""

    def __init__(self, db: osxphotos.PhotosDB, version: int, uuid: str):
        """Create a Table object."""
        super().__init__(db, version, uuid)
        self.columns = get_table_columns(self.conn, "ZPERSON")
        self.table_name = "ZPERSON"

    def rows(self) -> list[tuple[Any]]:
        """Return rows for this photo from the ZPERSON table."""
        conn, cursor = self.db.get_db_connection()
        person_fk = _DB_TABLE_NAMES[self.version]["DETECTED_FACE_PERSON_FK"]
        asset_fk = _DB_TABLE_NAMES[self.version]["DETECTED_FACE_ASSET_FK"]
        sql = f"""  SELECT ZPERSON.*
                    FROM ZPERSON 
                    JOIN ZDETECTEDFACE ON {person_fk} = ZPERSON.Z_PK
                    JOIN ZASSET ON ZASSET.Z_PK = {asset_fk}
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return result if (result := cursor.fetchall()) else []

    def _get_column(self, column: str) -> tuple[Any]:
        """Get column value for this photo from the ZPERSON table."""
        conn, cursor = self.db.get_db_connection()
        person_fk = _DB_TABLE_NAMES[self.version]["DETECTED_FACE_PERSON_FK"]
        asset_fk = _DB_TABLE_NAMES[self.version]["DETECTED_FACE_ASSET_FK"]
        sql = f"""  SELECT ZPERSON.{column}
                    FROM ZPERSON 
                    JOIN ZDETECTEDFACE ON {person_fk} = ZPERSON.Z_PK
                    JOIN ZASSET ON ZASSET.Z_PK = {asset_fk}
                    WHERE {self.asset_table}.ZUUID = ?;
            """
        cursor.execute(sql, (self.uuid,))
        return (
            tuple(result[0] for result in results)
            if (results := cursor.fetchall())
            else ()
        )
