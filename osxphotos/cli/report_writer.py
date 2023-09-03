"""Report writer for the --report option of `osxphotos export`"""

from __future__ import annotations

import csv
import datetime
import json
import os
import os.path
import sqlite3
import sys
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Any, Dict, Union

from osxphotos._constants import SQLITE_CHECK_SAME_THREAD
from osxphotos.export_db import OSXPHOTOS_ABOUT_STRING
from osxphotos.exportoptions import ExportResults
from osxphotos.sqlite_utils import sqlite_columns

from .push_results import PushResults
from .sync_results import SyncResults

__all__ = [
    "ExportReportWriterCSV",
    "ExportReportWriterJSON",
    "ExportReportWriterSqlite",
    "PushExifReportWriterCSV",
    "PushExifReportWriterJSON",
    "PushExifReportWriterSqlite",
    "ReportWriterABC",
    "ReportWriterNoOp",
    "SyncReportWriterCSV",
    "SyncReportWriterJSON",
    "SyncReportWriterSqlite",
    "export_report_writer_factory",
    "push_exif_report_writer_factory",
    "sync_report_writer_factory",
]


# Abstract base class for report writers
class ReportWriterABC(ABC):
    """Abstract base class for report writers"""

    @abstractmethod
    def write(self, *args, **kwargs):
        """Write results to the output file"""
        pass

    @abstractmethod
    def close(self):
        """Close the output file"""
        pass


# Report writer that does nothing, used for --dry-run or when --report not specified


class ReportWriterNoOp(ABC):
    """Report writer that does nothing"""

    def __init__(self):
        pass

    def write(self, *args, **kwargs):
        """Write results to the output file"""
        pass

    def close(self):
        """Close the output file"""
        pass


# Classes for writing ExportResults to report file
class ExportReportWriterCSV(ReportWriterABC):
    """Write CSV report file for export results"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        report_columns = [
            "datetime",
            "filename",
            "exported",
            "new",
            "updated",
            "skipped",
            "exif_updated",
            "touched",
            "converted_to_jpeg",
            "sidecar_xmp",
            "sidecar_json",
            "sidecar_exiftool",
            "missing",
            "error",
            "exiftool_warning",
            "exiftool_error",
            "extended_attributes_written",
            "extended_attributes_skipped",
            "cleanup_deleted_file",
            "cleanup_deleted_directory",
            "exported_album",
            "sidecar_user",
            "sidecar_user_error",
            "user_written",
            "user_skipped",
            "user_error",
        ]

        mode = "a" if append else "w"
        self._output_fh = open(self.output_file, mode)

        self._csv_writer = csv.DictWriter(self._output_fh, fieldnames=report_columns)
        if not append:
            self._csv_writer.writeheader()

    def write(self, export_results: ExportResults):
        """Write results to the output file"""
        all_results = prepare_export_results_for_writing(export_results)
        for data in list(all_results.values()):
            self._csv_writer.writerow(data)
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self._output_fh.close()


class ExportReportWriterJSON(ReportWriterABC):
    """Write JSON report file for export results"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append
        self.indent = 4

        self._first_record_written = False
        if append:
            with open(self.output_file, "r") as fh:
                existing_data = json.load(fh)
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")
            for data in existing_data:
                self._output_fh.write(json.dumps(data, indent=self.indent))
                self._output_fh.write(",\n")
        else:
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")

    def write(self, export_results: ExportResults):
        """Write results to the output file"""
        all_results = prepare_export_results_for_writing(
            export_results, bool_values=True
        )
        for data in list(all_results.values()):
            if self._first_record_written:
                self._output_fh.write(",\n")
            else:
                self._first_record_written = True
            self._output_fh.write(json.dumps(data, indent=self.indent))
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.write("]")
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self.close()


class ExportReportWriterSQLite(ReportWriterABC):
    """Write sqlite report file for export data"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        if not append:
            with suppress(FileNotFoundError):
                os.unlink(self.output_file)

        self._conn = sqlite3.connect(
            self.output_file, check_same_thread=SQLITE_CHECK_SAME_THREAD
        )
        self._create_tables()
        self.report_id = self._generate_report_id()

    def write(self, export_results: ExportResults):
        """Write results to the output file"""

        all_results = prepare_export_results_for_writing(export_results)
        for data in list(all_results.values()):
            data["report_id"] = self.report_id
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT INTO report "
                "(datetime, filename, exported, new, updated, skipped, exif_updated, touched, converted_to_jpeg, sidecar_xmp, sidecar_json, sidecar_exiftool, missing, error, exiftool_warning, exiftool_error, extended_attributes_written, extended_attributes_skipped, cleanup_deleted_file, cleanup_deleted_directory, exported_album, report_id, sidecar_user, sidecar_user_error, user_written, user_skipped, user_error) "  # noqa
                "VALUES "
                "(:datetime, :filename, :exported, :new, :updated, :skipped, :exif_updated, :touched, :converted_to_jpeg, :sidecar_xmp, :sidecar_json, :sidecar_exiftool, :missing, :error, :exiftool_warning, :exiftool_error, :extended_attributes_written, :extended_attributes_skipped, :cleanup_deleted_file, :cleanup_deleted_directory, :exported_album, :report_id, :sidecar_user, :sidecar_user_error, :user_written, :user_skipped, :user_error);",  # noqa
                data,
            )
        self._conn.commit()

    def close(self):
        """Close the output file"""
        self._conn.close()

    def _create_tables(self):
        c = self._conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report (
                datetime TEXT,
                filename TEXT,
                exported INTEGER,
                new INTEGER,
                updated INTEGER,
                skipped INTEGER,
                exif_updated INTEGER,
                touched INTEGER,
                converted_to_jpeg INTEGER,
                sidecar_xmp INTEGER,
                sidecar_json INTEGER,
                sidecar_exiftool INTEGER,
                missing INTEGER,
                error TEXT,
                exiftool_warning TEXT,
                exiftool_error TEXT,
                extended_attributes_written INTEGER,
                extended_attributes_skipped INTEGER,
                cleanup_deleted_file INTEGER,
                cleanup_deleted_directory INTEGER,
                exported_album TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS about (
                id INTEGER PRIMARY KEY,
                about TEXT
                );"""
        )
        c.execute(
            "INSERT INTO about(about) VALUES (?);",
            (f"OSXPhotos Export Report. {OSXPHOTOS_ABOUT_STRING}",),
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report_id (
                report_id INTEGER PRIMARY KEY,
                datetime TEXT
            );"""
        )
        self._conn.commit()

        # migrate report table to add report_id if needed (#731)
        if "report_id" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute("ALTER TABLE report ADD COLUMN report_id TEXT;")
            self._conn.commit()

        # migrate report table and add sidecar_user column if needed (#1123)
        if "sidecar_user" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute(
                "ALTER TABLE report ADD COLUMN sidecar_user INTEGER;"
            )
            self._conn.commit()

        # migrate report table and add sidecar_user_error if needed (#1123)
        if "sidecar_user_error" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute(
                "ALTER TABLE report ADD COLUMN sidecar_user_error TEXT;"
            )
            self._conn.commit()

        # migrate report table and add user_written, skipped, error if needed (#1136)
        if "user_written" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute(
                "ALTER TABLE report ADD COLUMN user_written INTEGER;"
            )
            self._conn.commit()

        if "user_skipped" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute(
                "ALTER TABLE report ADD COLUMN user_skipped INTEGER;"
            )
            self._conn.commit()

        if "user_error" not in sqlite_columns(self._conn, "report"):
            self._conn.cursor().execute(
                "ALTER TABLE report ADD COLUMN user_error TEXT;"
            )
            self._conn.commit()

        # create report_summary view
        c.execute(
            """
            CREATE VIEW IF NOT EXISTS report_summary AS
            SELECT
                report_id,
                datetime(MIN(datetime)) start_time,
                datetime(MAX(datetime)) end_time,
                STRFTIME('%s',MAX(datetime)) - STRFTIME('%s',MIN(datetime)) AS duration_s,
                SUM(exported) AS exported,
                sum(new) as new,
                SUM(updated) as updated,
                SUM(skipped) as skipped,
                SUM(sidecar_xmp) as sidecar_xmp,
                SUM(touched) as touched,
                SUM(converted_to_jpeg) as converted_to_jpeg,
                SUM(missing) as missing,
                SUM(CASE WHEN error = "" THEN 0 ELSE 1 END) as error,
                SUM(cleanup_deleted_file) as cleanup_deleted_file
            FROM report
            GROUP BY report_id;"""
        )
        self._conn.commit()

    def _generate_report_id(self) -> int:
        """Get a new report ID for this report"""
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO report_id(datetime) VALUES (?);",
            (datetime.datetime.now().isoformat(),),
        )
        report_id = c.lastrowid
        self._conn.commit()
        return report_id

    def __del__(self):
        with suppress(Exception):
            self.close()


def prepare_export_results_for_writing(
    export_results: ExportResults, bool_values: bool = False
) -> Dict:
    """Return all results for writing to report

    Args:
        export_results: ExportResults object
        bool_values: Return a boolean value instead of a integer (e.g. for use with JSON)

    Returns:
        Dict: All results
    """
    false = False if bool_values else 0
    true = True if bool_values else 1

    all_results = {}
    for result in (
        export_results.all_files()
        + export_results.deleted_files
        + export_results.deleted_directories
    ):
        result = str(result)
        if result not in all_results:
            all_results[str(result)] = {
                "datetime": export_results.datetime,
                "filename": str(result),
                "exported": false,
                "new": false,
                "updated": false,
                "skipped": false,
                "exif_updated": false,
                "touched": false,
                "converted_to_jpeg": false,
                "sidecar_xmp": false,
                "sidecar_json": false,
                "sidecar_exiftool": false,
                "missing": false,
                "error": "",
                "exiftool_warning": "",
                "exiftool_error": "",
                "extended_attributes_written": false,
                "extended_attributes_skipped": false,
                "cleanup_deleted_file": false,
                "cleanup_deleted_directory": false,
                "exported_album": "",
                "sidecar_user": false,
                "sidecar_user_error": "",
                "user_written": false,
                "user_skipped": false,
                "user_error": "",
            }

    for result in export_results.exported:
        all_results[str(result)]["exported"] = true

    for result in export_results.new:
        all_results[str(result)]["new"] = true

    for result in export_results.updated:
        all_results[str(result)]["updated"] = true

    for result in export_results.skipped:
        all_results[str(result)]["skipped"] = true

    for result in export_results.exif_updated:
        all_results[str(result)]["exif_updated"] = true

    for result in export_results.touched:
        all_results[str(result)]["touched"] = true

    for result in export_results.converted_to_jpeg:
        all_results[str(result)]["converted_to_jpeg"] = true

    for result in export_results.sidecar_xmp_written:
        all_results[str(result)]["sidecar_xmp"] = true
        all_results[str(result)]["exported"] = true

    for result in export_results.sidecar_xmp_skipped:
        all_results[str(result)]["sidecar_xmp"] = true
        all_results[str(result)]["skipped"] = true

    for result in export_results.sidecar_json_written:
        all_results[str(result)]["sidecar_json"] = true
        all_results[str(result)]["exported"] = true

    for result in export_results.sidecar_json_skipped:
        all_results[str(result)]["sidecar_json"] = true
        all_results[str(result)]["skipped"] = true

    for result in export_results.sidecar_exiftool_written:
        all_results[str(result)]["sidecar_exiftool"] = true
        all_results[str(result)]["exported"] = true

    for result in export_results.sidecar_exiftool_skipped:
        all_results[str(result)]["sidecar_exiftool"] = true
        all_results[str(result)]["skipped"] = true

    for result in export_results.missing:
        all_results[str(result)]["missing"] = true

    for result in export_results.error:
        all_results[str(result[0])]["error"] = result[1]

    for result in export_results.exiftool_warning:
        all_results[str(result[0])]["exiftool_warning"] = result[1]

    for result in export_results.exiftool_error:
        all_results[str(result[0])]["exiftool_error"] = result[1]

    for result in export_results.xattr_written:
        all_results[str(result)]["extended_attributes_written"] = true

    for result in export_results.xattr_skipped:
        all_results[str(result)]["extended_attributes_skipped"] = true

    for result in export_results.deleted_files:
        all_results[str(result)]["cleanup_deleted_file"] = true

    for result in export_results.deleted_directories:
        all_results[str(result)]["cleanup_deleted_directory"] = true

    for result, album in export_results.exported_album:
        all_results[str(result)]["exported_album"] = album

    for result in export_results.sidecar_user_written:
        all_results[str(result)]["sidecar_user"] = true
        all_results[str(result)]["exported"] = true

    for result in export_results.sidecar_user_skipped:
        all_results[str(result)]["sidecar_user"] = true
        all_results[str(result)]["skipped"] = true

    for result in export_results.sidecar_user_error:
        all_results[str(result[0])]["sidecar_user_error"] = result[1]

    for result in export_results.user_written:
        all_results[str(result)]["user_written"] = true
        all_results[str(result)]["exported"] = true

    for result in export_results.user_skipped:
        all_results[str(result)]["user_skipped"] = true
        all_results[str(result)]["skipped"] = true

    for result in export_results.user_error:
        all_results[str(result[0])]["user_error"] = result[1]

    return all_results


def export_report_writer_factory(
    output_file: Union[str, bytes, os.PathLike], append: bool = False
) -> ReportWriterABC:
    """Return a ReportWriter instance appropriate for the output file type"""
    output_type = os.path.splitext(output_file)[1]
    output_type = output_type.lower()[1:]
    if output_type == "csv":
        return ExportReportWriterCSV(output_file, append)
    elif output_type == "json":
        return ExportReportWriterJSON(output_file, append)
    elif output_type in ["sqlite", "db"]:
        return ExportReportWriterSQLite(output_file, append)
    else:
        raise ValueError(f"Unknown report file type: {output_file}")


# Classes for writing Sync results to a report file


class SyncReportWriterCSV(ReportWriterABC):
    """Write CSV report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append
        mode = "a" if append else "w"
        self._output_fh = open(self.output_file, mode)

    def write(self, sync_results: SyncResults):
        """Write results to the output file"""
        report_columns = sync_results.results_header
        self._csv_writer = csv.DictWriter(self._output_fh, fieldnames=report_columns)
        if not self.append:
            self._csv_writer.writeheader()

        for data in sync_results.results_list:
            self._csv_writer.writerow(dict(zip(report_columns, data)))
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self._output_fh.close()


class SyncReportWriterJSON(ReportWriterABC):
    """Write JSON SyncResults report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append
        self.indent = 4

        self._first_record_written = False
        if append:
            with open(self.output_file, "r") as fh:
                existing_data = json.load(fh)
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")
            for data in existing_data:
                self._output_fh.write(json.dumps(data, indent=self.indent))
                self._output_fh.write(",\n")
        else:
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")

    def write(self, results: SyncResults):
        """Write results to the output file"""

        # convert datetimes to strings
        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        for data in list(results.results_dict.values()):
            if self._first_record_written:
                self._output_fh.write(",\n")
            else:
                self._first_record_written = True
            self._output_fh.write(json.dumps(data, indent=self.indent, default=default))
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.write("]")
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self.close()


class SyncReportWriterSQLite(ReportWriterABC):
    """Write sqlite SyncResults report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        if not append:
            with suppress(FileNotFoundError):
                os.unlink(self.output_file)

        self._conn = sqlite3.connect(
            self.output_file, check_same_thread=SQLITE_CHECK_SAME_THREAD
        )
        self._create_tables()
        self.report_id = self._generate_report_id()

    def write(self, results: SyncResults):
        """Write results to the output file"""

        # insert rows of values into sqlite report table
        for row in list(results.results_list):
            report_id = self.report_id
            data = [str(v) if v else "" for v in row]
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT INTO report "
                "(report_id, uuid, filename, fingerprint, updated, "
                "albums_updated, albums_datetime, albums_before, albums_after, "
                "description_updated, description_datetime, description_before, description_after, "
                "favorite_updated, favorite_datetime, favorite_before, favorite_after, "
                "keywords_updated, keywords_datetime, keywords_before, keywords_after, "
                "title_updated, title_datetime, title_before, title_after)"
                "VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (report_id, *data),
            )
        self._conn.commit()

    def close(self):
        """Close the output file"""
        self._conn.close()

    def _create_tables(self):
        c = self._conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report (
                report_id TEXT, 
                uuid TEXT,
                filename TEXT,
                fingerprint TEXT,
                updated INT,
                albums_updated INT,
                albums_datetime TEXT,
                albums_before TEXT,
                albums_after TEXT,
                description_updated INT,
                description_datetime TEXT,
                description_before TEXT,
                description_after TEXT,
                favorite_updated INT,
                favorite_datetime TEXT,
                favorite_before TEXT,
                favorite_after TEXT,
                keywords_updated INT,
                keywords_datetime TEXT,
                keywords_before TEXT,
                keywords_after TEXT,
                title_updated INT,
                title_datetime TEXT,
                title_before TEXT,
                title_after TEXT
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS about (
                id INTEGER PRIMARY KEY,
                about TEXT
                );"""
        )
        c.execute(
            "INSERT INTO about(about) VALUES (?);",
            (f"OSXPhotos Sync Report. {OSXPHOTOS_ABOUT_STRING}",),
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report_id (
                report_id INTEGER PRIMARY KEY,
                datetime TEXT
            );"""
        )
        self._conn.commit()

        # create report_summary view
        c.execute("DROP VIEW IF EXISTS report_summary;")
        c.execute(
            """
            CREATE VIEW report_summary AS
            SELECT
                r.report_id,
                i.datetime AS report_datetime,
                COUNT(r.uuid) as processed,
                COUNT(CASE r.updated WHEN 'True' THEN 1 ELSE NULL END) as updated,
                COUNT(case r.albums_updated WHEN 'True' THEN 1 ELSE NULL END) as albums_updated,
                COUNT(case r.description_updated WHEN 'True' THEN 1 ELSE NULL END) as description_updated,
                COUNT(case r.favorite_updated WHEN 'True' THEN 1 ELSE NULL END) as favorite_updated,
                COUNT(case r.keywords_updated WHEN 'True' THEN 1 ELSE NULL END) as keywords_updated,
                COUNT(case r.title_updated WHEN 'True' THEN 1 ELSE NULL END) as title_updated
            FROM report as r
            INNER JOIN report_id as i ON r.report_id = i.report_id
            GROUP BY r.report_id;
            """
        )
        self._conn.commit()

    def _generate_report_id(self) -> int:
        """Get a new report ID for this report"""
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO report_id(datetime) VALUES (?);",
            (datetime.datetime.now().isoformat(),),
        )
        report_id = c.lastrowid
        self._conn.commit()
        return report_id

    def __del__(self):
        with suppress(Exception):
            self.close()


def sync_report_writer_factory(
    output_file: Union[str, bytes, os.PathLike], append: bool = False
) -> ReportWriterABC:
    """Return a ReportWriter instance appropriate for the output file type"""
    output_type = os.path.splitext(output_file)[1]
    output_type = output_type.lower()[1:]
    if output_type == "csv":
        return SyncReportWriterCSV(output_file, append)
    elif output_type == "json":
        return SyncReportWriterJSON(output_file, append)
    elif output_type in ["sqlite", "db"]:
        return SyncReportWriterSQLite(output_file, append)
    else:
        raise ValueError(f"Unknown report file type: {output_file}")


class PushExifReportWriterCSV(ReportWriterABC):
    """Write CSV report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        report_columns = [
            "uuid",
            "original_filename",
            "datetime",
            "filename",
            "written",
            "updated",
            "skipped",
            "missing",
            "warning",
            "error",
        ]
        self.output_file = output_file
        self.append = append
        mode = "a" if append else "w"
        self._output_fh = open(self.output_file, mode)
        self._csv_writer = csv.DictWriter(self._output_fh, fieldnames=report_columns)
        if not append:
            self._csv_writer.writeheader()

    def write(self, uuid: str, original_filename: str, push_results: PushResults):
        """Write results to the output file"""
        errors_by_filename = {e[0]: e[1] for e in push_results.error}
        warnings_by_filename = {w[0]: w[1] for w in push_results.warning}
        for filename in push_results.written:
            self._csv_writer.writerow(
                {
                    "uuid": uuid,
                    "original_filename": original_filename,
                    "datetime": push_results.datetime,
                    "filename": filename,
                    "written": True,
                    "updated": False,
                    "skipped": False,
                    "missing": "",
                    "warning": warnings_by_filename.get(filename, ""),
                    "error": errors_by_filename.get(filename, ""),
                }
            )
        for filename in push_results.updated:
            self._csv_writer.writerow(
                {
                    "uuid": uuid,
                    "original_filename": original_filename,
                    "datetime": push_results.datetime,
                    "filename": filename,
                    "written": False,
                    "updated": True,
                    "skipped": False,
                    "missing": "",
                    "warning": warnings_by_filename.get(filename, ""),
                    "error": errors_by_filename.get(filename, ""),
                }
            )
        for filename in push_results.skipped:
            self._csv_writer.writerow(
                {
                    "uuid": uuid,
                    "original_filename": original_filename,
                    "datetime": push_results.datetime,
                    "filename": filename,
                    "written": False,
                    "updated": False,
                    "skipped": True,
                    "missing": "",
                    "warning": warnings_by_filename.get(filename, ""),
                    "error": errors_by_filename.get(filename, ""),
                }
            )
        for missing in push_results.missing:
            self._csv_writer.writerow(
                {
                    "uuid": uuid,
                    "original_filename": original_filename,
                    "datetime": push_results.datetime,
                    "filename": "",
                    "written": False,
                    "updated": False,
                    "skipped": False,
                    "missing": missing,
                    "warning": "",
                    "error": "",
                }
            )
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self._output_fh.close()


class PushExifReportWriterJSON(ReportWriterABC):
    """Write JSON report file for push-exif results"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append
        self.indent = 4

        self._first_record_written = False
        if append:
            with open(self.output_file, "r") as fh:
                existing_data = json.load(fh)
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")
            for data in existing_data:
                self._output_fh.write(json.dumps(data, indent=self.indent))
                self._output_fh.write(",\n")
        else:
            self._output_fh = open(self.output_file, "w")
            self._output_fh.write("[")

    def write(self, uuid: str, original_filename: str, push_results: PushResults):
        """Write results to the output file"""
        record = {"uuid": uuid, "original_filename": original_filename}
        for field in [
            "datetime",
            "written",
            "updated",
            "skipped",
            "missing",
            "warning",
            "error",
        ]:
            record[field] = getattr(push_results, field)
        if self._first_record_written:
            self._output_fh.write(",\n")
        else:
            self._first_record_written = True
        self._output_fh.write(json.dumps(record, indent=self.indent))
        self._output_fh.flush()

    def close(self):
        """Close the output file"""
        self._output_fh.write("]")
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self.close()


class PushExifReportWriterSQLite(ReportWriterABC):
    """Write SQLite PushResults report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        if not append:
            with suppress(FileNotFoundError):
                os.unlink(self.output_file)

        self._conn = sqlite3.connect(
            self.output_file, check_same_thread=SQLITE_CHECK_SAME_THREAD
        )
        self._create_tables()
        self.report_id = self._generate_report_id()

    def write(self, uuid: str, original_filename: str, results: PushResults):
        """Write results to the output file"""

        errors_by_filename = {e[0]: e[1] for e in results.error}
        warnings_by_filename = {w[0]: w[1] for w in results.warning}

        # insert rows of values into sqlite report table
        for filename in results.written:
            self._write_row(
                uuid,
                original_filename,
                results.datetime,
                filename,
                1,
                0,
                0,
                "",
                warnings_by_filename.get(filename, ""),
                errors_by_filename.get(filename, ""),
            )
        for filename in results.updated:
            self._write_row(
                uuid,
                original_filename,
                results.datetime,
                filename,
                0,
                1,
                0,
                "",
                warnings_by_filename.get(filename, ""),
                errors_by_filename.get(filename, ""),
            )
        for filename in results.skipped:
            self._write_row(
                uuid,
                original_filename,
                results.datetime,
                filename,
                0,
                0,
                1,
                "",
                "",
                "",
            )
        for missing in results.missing:
            self._write_row(
                uuid,
                original_filename,
                results.datetime,
                "",
                0,
                0,
                0,
                missing,
                "",
                "",
            )

    def _write_row(self, *data: Any):
        """Write a row to the report table"""
        report_id = self.report_id
        # data = [str(v) if v else "" for v in row]
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO report "
            "(report_id, uuid, original_filename, datetime, filename, written, updated, skipped, missing, warning, error)"
            "VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (report_id, *data),
        )
        self._conn.commit()

    def close(self):
        """Close the output file"""
        self._conn.close()

    def _create_tables(self):
        c = self._conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report (
                report_id TEXT, 
                uuid TEXT,
                original_filename TEXT,
                filename TEXT,
                datetime TEXT,
                written INT,
                updated INT,
                skipped INT,
                missing TEXT,
                warning TEXT,
                error TEXT
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS about (
                id INTEGER PRIMARY KEY,
                about TEXT
                );"""
        )
        about_str = f"OSXPhotos push-exif Report. {OSXPHOTOS_ABOUT_STRING}"
        c.execute(
            """
            INSERT INTO about(about)
            SELECT :about_str
            FROM sqlite_master
            WHERE type = 'table' AND name = 'about'
            AND (SELECT COUNT(*) FROM about) = 0;""",
            {"about_str": about_str},
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report_id (
                report_id INTEGER PRIMARY KEY,
                datetime TEXT,
                command_line TEXT
            );"""
        )
        self._conn.commit()

    def _generate_report_id(self) -> int:
        """Get a new report ID for this report"""
        command_line = " ".join(sys.argv)
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO report_id(datetime, command_line) VALUES (?, ?);",
            (datetime.datetime.now().isoformat(), command_line),
        )
        report_id = c.lastrowid
        self._conn.commit()
        return report_id

    def __del__(self):
        with suppress(Exception):
            self.close()


def push_exif_report_writer_factory(
    output_file: Union[str, bytes, os.PathLike], append: bool = False
) -> ReportWriterABC:
    """Return a ReportWriter instance appropriate for the output file type"""
    output_type = os.path.splitext(output_file)[1]
    output_type = output_type.lower()[1:]
    if output_type == "csv":
        return PushExifReportWriterCSV(output_file, append)
    elif output_type == "json":
        return PushExifReportWriterJSON(output_file, append)
    elif output_type in ["sqlite", "db"]:
        return PushExifReportWriterSQLite(output_file, append)
    else:
        raise ValueError(f"Unknown report file type: {output_file}")
