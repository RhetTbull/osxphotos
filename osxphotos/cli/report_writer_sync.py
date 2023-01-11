"""Report writer for the --report option of `osxphotos sync`"""


import csv
import datetime
import json
import os
import os.path
import sqlite3
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Dict, Union

from osxphotos import __version__
from osxphotos.sqlite_utils import sqlite_columns

from .sync_results import SyncResults

# ZZZ
from osxphotos.photoexporter import ExportResults

OSXPHOTOS_ABOUT_STRING = f"Created by osxphotos version {__version__} (https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"

__all__ = [
    "sync_report_writer_factory",
    "ReportWriterABC",
    "SyncReportWriterCSV",
    "ReportWriterSqlite",
    "ReportWriterNoOp",
]


class ReportWriterABC(ABC):
    """Abstract base class for report writers"""

    @abstractmethod
    def write(self, sync_results: SyncResults):
        """Write results to the output file"""
        pass

    @abstractmethod
    def close(self):
        """Close the output file"""
        pass


class ReportWriterNoOp(ABC):
    """Report writer that does nothing"""

    def __init__(self):
        pass

    def write(self, sync_results: SyncResults):
        """Write results to the output file"""
        pass

    def close(self):
        """Close the output file"""
        pass


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
    """Write JSON report file"""

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
        all_results = prepare_results_for_writing(export_results, bool_values=True)
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


class SyncReportWriterSQLite(ReportWriterABC):
    """Write sqlite report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        if not append:
            with suppress(FileNotFoundError):
                os.unlink(self.output_file)

        self._conn = sqlite3.connect(self.output_file)
        self._create_tables()
        self.report_id = self._generate_report_id()

    def write(self, export_results: ExportResults):
        """Write results to the output file"""

        all_results = prepare_results_for_writing(export_results)
        for data in list(all_results.values()):
            data["report_id"] = self.report_id
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT INTO report "
                "(datetime, filename, exported, new, updated, skipped, exif_updated, touched, converted_to_jpeg, sidecar_xmp, sidecar_json, sidecar_exiftool, missing, error, exiftool_warning, exiftool_error, extended_attributes_written, extended_attributes_skipped, cleanup_deleted_file, cleanup_deleted_directory, exported_album, report_id) "
                "VALUES "
                "(:datetime, :filename, :exported, :new, :updated, :skipped, :exif_updated, :touched, :converted_to_jpeg, :sidecar_xmp, :sidecar_json, :sidecar_exiftool, :missing, :error, :exiftool_warning, :exiftool_error, :extended_attributes_written, :extended_attributes_skipped, :cleanup_deleted_file, :cleanup_deleted_directory, :exported_album, :report_id);",
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
