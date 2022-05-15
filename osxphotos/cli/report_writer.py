"""Report writer for the --report option of `osxphotos export`"""


import csv
import json
import os
import os.path
from abc import ABC, abstractmethod
from contextlib import suppress
from datetime import datetime
from typing import Union

from osxphotos.photoexporter import ExportResults

__all__ = [
    "report_writer_factory",
    "ReportWriterABC",
    "ReportWriterCSV",
    "ReportWriterNoOp",
]


class ReportWriterABC(ABC):
    """Abstract base class for report writers"""

    @abstractmethod
    def write(self, export_results: ExportResults):
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

    def write(self, export_results: ExportResults):
        """Write results to the output file"""
        pass

    def close(self):
        """Close the output file"""
        pass


class ReportWriterCSV(ReportWriterABC):
    """Write CSV report file"""

    def __init__(
        self, output_file: Union[str, bytes, os.PathLike], append: bool = False
    ):
        self.output_file = output_file
        self.append = append

        report_columns = [
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
        ]

        mode = "a" if append else "w"
        self._output_fh = open(self.output_file, mode)

        self._csv_writer = csv.DictWriter(self._output_fh, fieldnames=report_columns)
        if not append:
            self._csv_writer.writeheader()

    def write(self, export_results: ExportResults):
        """Write results to the output file"""
        all_results = {
            result: {
                "filename": result,
                "exported": 0,
                "new": 0,
                "updated": 0,
                "skipped": 0,
                "exif_updated": 0,
                "touched": 0,
                "converted_to_jpeg": 0,
                "sidecar_xmp": 0,
                "sidecar_json": 0,
                "sidecar_exiftool": 0,
                "missing": 0,
                "error": "",
                "exiftool_warning": "",
                "exiftool_error": "",
                "extended_attributes_written": 0,
                "extended_attributes_skipped": 0,
                "cleanup_deleted_file": 0,
                "cleanup_deleted_directory": 0,
                "exported_album": "",
            }
            for result in export_results.all_files()
            + export_results.deleted_files
            + export_results.deleted_directories
        }
        for result in export_results.exported:
            all_results[result]["exported"] = 1

        for result in export_results.new:
            all_results[result]["new"] = 1

        for result in export_results.updated:
            all_results[result]["updated"] = 1

        for result in export_results.skipped:
            all_results[result]["skipped"] = 1

        for result in export_results.exif_updated:
            all_results[result]["exif_updated"] = 1

        for result in export_results.touched:
            all_results[result]["touched"] = 1

        for result in export_results.converted_to_jpeg:
            all_results[result]["converted_to_jpeg"] = 1

        for result in export_results.sidecar_xmp_written:
            all_results[result]["sidecar_xmp"] = 1
            all_results[result]["exported"] = 1

        for result in export_results.sidecar_xmp_skipped:
            all_results[result]["sidecar_xmp"] = 1
            all_results[result]["skipped"] = 1

        for result in export_results.sidecar_json_written:
            all_results[result]["sidecar_json"] = 1
            all_results[result]["exported"] = 1

        for result in export_results.sidecar_json_skipped:
            all_results[result]["sidecar_json"] = 1
            all_results[result]["skipped"] = 1

        for result in export_results.sidecar_exiftool_written:
            all_results[result]["sidecar_exiftool"] = 1
            all_results[result]["exported"] = 1

        for result in export_results.sidecar_exiftool_skipped:
            all_results[result]["sidecar_exiftool"] = 1
            all_results[result]["skipped"] = 1

        for result in export_results.missing:
            all_results[result]["missing"] = 1

        for result in export_results.error:
            all_results[result[0]]["error"] = result[1]

        for result in export_results.exiftool_warning:
            all_results[result[0]]["exiftool_warning"] = result[1]

        for result in export_results.exiftool_error:
            all_results[result[0]]["exiftool_error"] = result[1]

        for result in export_results.xattr_written:
            all_results[result]["extended_attributes_written"] = 1

        for result in export_results.xattr_skipped:
            all_results[result]["extended_attributes_skipped"] = 1

        for result in export_results.deleted_files:
            all_results[result]["cleanup_deleted_file"] = 1

        for result in export_results.deleted_directories:
            all_results[result]["cleanup_deleted_directory"] = 1

        for result, album in export_results.exported_album:
            all_results[result]["exported_album"] = album

        for data in list(all_results.values()):
            self._csv_writer.writerow(data)

    def close(self):
        """Close the output file"""
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self._output_fh.close()


class ReportWriterJSON(ReportWriterABC):
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
        all_results = {
            result: {
                "filename": str(result),
                "datetime": export_results.datetime,
                "exported": False,
                "new": False,
                "updated": False,
                "skipped": False,
                "exif_updated": False,
                "touched": False,
                "converted_to_jpeg": False,
                "sidecar_xmp": False,
                "sidecar_json": False,
                "sidecar_exiftool": False,
                "missing": False,
                "error": "",
                "exiftool_warning": "",
                "exiftool_error": "",
                "extended_attributes_written": False,
                "extended_attributes_skipped": False,
                "cleanup_deleted_file": False,
                "cleanup_deleted_directory": False,
                "exported_album": "",
            }
            for result in export_results.all_files()
            + export_results.deleted_files
            + export_results.deleted_directories
        }
        for result in export_results.exported:
            all_results[result]["exported"] = True

        for result in export_results.new:
            all_results[result]["new"] = True

        for result in export_results.updated:
            all_results[result]["updated"] = True

        for result in export_results.skipped:
            all_results[result]["skipped"] = True

        for result in export_results.exif_updated:
            all_results[result]["exif_updated"] = True

        for result in export_results.touched:
            all_results[result]["touched"] = True

        for result in export_results.converted_to_jpeg:
            all_results[result]["converted_to_jpeg"] = True

        for result in export_results.sidecar_xmp_written:
            all_results[result]["sidecar_xmp"] = True
            all_results[result]["exported"] = True

        for result in export_results.sidecar_xmp_skipped:
            all_results[result]["sidecar_xmp"] = True
            all_results[result]["skipped"] = True

        for result in export_results.sidecar_json_written:
            all_results[result]["sidecar_json"] = True
            all_results[result]["exported"] = True

        for result in export_results.sidecar_json_skipped:
            all_results[result]["sidecar_json"] = True
            all_results[result]["skipped"] = True

        for result in export_results.sidecar_exiftool_written:
            all_results[result]["sidecar_exiftool"] = True
            all_results[result]["exported"] = True

        for result in export_results.sidecar_exiftool_skipped:
            all_results[result]["sidecar_exiftool"] = True
            all_results[result]["skipped"] = True

        for result in export_results.missing:
            all_results[result]["missing"] = True

        for result in export_results.error:
            all_results[result[0]]["error"] = result[1]

        for result in export_results.exiftool_warning:
            all_results[result[0]]["exiftool_warning"] = result[1]

        for result in export_results.exiftool_error:
            all_results[result[0]]["exiftool_error"] = result[1]

        for result in export_results.xattr_written:
            all_results[result]["extended_attributes_written"] = True

        for result in export_results.xattr_skipped:
            all_results[result]["extended_attributes_skipped"] = True

        for result in export_results.deleted_files:
            all_results[result]["cleanup_deleted_file"] = True

        for result in export_results.deleted_directories:
            all_results[result]["cleanup_deleted_directory"] = True

        for result, album in export_results.exported_album:
            all_results[result]["exported_album"] = album

        for data in list(all_results.values()):
            if self._first_record_written:
                self._output_fh.write(",\n")
            else:
                self._first_record_written = True
            self._output_fh.write(json.dumps(data, indent=self.indent))

    def close(self):
        """Close the output file"""
        self._output_fh.write("]")
        self._output_fh.close()

    def __del__(self):
        with suppress(Exception):
            self.close()


def report_writer_factory(
    output_file: Union[str, bytes, os.PathLike], append: bool = False
) -> ReportWriterABC:
    """Return a ReportWriter instance appropriate for the output file type"""
    output_type = os.path.splitext(output_file)[1]
    output_type = output_type.lower()[1:]
    if output_type == "csv":
        return ReportWriterCSV(output_file, append)
    elif output_type == "json":
        return ReportWriterJSON(output_file, append)
    else:
        raise ValueError(f"Unknown report file type: {output_file}")
