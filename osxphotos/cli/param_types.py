"""Click parameter types for osxphotos CLI"""
import datetime
import pathlib

import bitmath
import click

from osxphotos.export_db_utils import export_db_get_version
from osxphotos.utils import expand_and_validate_filepath, load_function

__all__ = [
    "BitMathSize",
    "DateTimeISO8601",
    "ExportDBType",
    "FunctionCall",
    "TimeISO8601",
]


class DateTimeISO8601(click.ParamType):

    name = "DATETIME"

    def convert(self, value, param, ctx):
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            self.fail(
                f"Invalid datetime format {value}. "
                "Valid format: YYYY-MM-DD[*HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]]"
            )


class BitMathSize(click.ParamType):

    name = "BITMATH"

    def convert(self, value, param, ctx):
        try:
            value = bitmath.parse_string(value)
        except ValueError:
            # no units specified
            try:
                value = int(value)
                value = bitmath.Byte(value)
            except ValueError as e:
                self.fail(
                    f"{value} must be specified as bytes or using SI/NIST units. "
                    + "For example, the following are all valid and equivalent sizes: '1048576' '1.048576MB', '1 MiB'."
                )
        return value


class TimeISO8601(click.ParamType):

    name = "TIME"

    def convert(self, value, param, ctx):
        try:
            return datetime.time.fromisoformat(value).replace(tzinfo=None)
        except Exception:
            self.fail(
                f"Invalid time format {value}. "
                "Valid format: HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]] "
                "however, note that timezone will be ignored."
            )


class FunctionCall(click.ParamType):
    name = "FUNCTION"

    def convert(self, value, param, ctx):
        if "::" not in value:
            self.fail(
                f"Could not parse function name from '{value}'. "
                "Valid format filename.py::function"
            )

        filename, funcname = value.split("::")

        filename_validated = expand_and_validate_filepath(filename)
        if not filename_validated:
            self.fail(f"'{filename}' does not appear to be a file")

        try:
            function = load_function(filename_validated, funcname)
        except Exception as e:
            self.fail(f"Could not load function {funcname} from {filename_validated}")

        return (function, value)


class ExportDBType(click.ParamType):

    name = "EXPORTDB"

    def convert(self, value, param, ctx):
        try:
            export_db_name = pathlib.Path(value)
            if export_db_name.is_dir():
                raise click.BadParameter(f"{value} is a directory")
            if export_db_name.is_file():
                # verify it's actually an osxphotos export_db
                # export_db_get_version will raise an error if it's not valid
                osxphotos_ver, export_db_ver = export_db_get_version(value)
            return value
        except Exception:
            self.fail(f"{value} exists but is not a valid osxphotos export database. ")
