"""Results class for osxphotos push-exif command"""

from datetime import datetime


class PushResults:
    """Results class which holds export results for push-exif

    Args:
        written: (list[str] | None = None) list of files that were successfully written to
        updated: (list[str] | None = None) list of files that were updated
        skipped: (list[str] | None = None) list of files that were skipped
        missing: (list[str] | None = None)list of files that were skipped due to missing file
        error: (list[tuple[str, str]] | None = None) list of tuples of (filename, error) where filename is the file that caused the error and error is the error message.
        warning: (list[tuple[str, str]] | None = None) list of tuples of (filename, warning) where filename is the file that caused the warning and warning is the warning message.

    Notes:
        Attributes are a list of files or None if no files for that attribute.
        Error and warning attributes are a list of tuples of (filename, error) where filename is the file that caused the error and error is the error message.
        PushResults can be added together with the += operator to combine results as the push-exif command progresses.
    """

    # Note: __init__ docs above added in the class docstring so they are picked up by sphinx

    __slots__ = [
        "_datetime",
        "written",
        "updated",
        "skipped",
        "missing",
        "error",
        "warning",
    ]

    def __init__(
        self,
    ):
        """PushResults data class to hold results of push-exif.

        See class docstring for details.
        """
        local_vars = locals()
        self._datetime = datetime.now().isoformat()
        for attr in self.attributes:
            setattr(self, attr, local_vars.get(attr) or [])

    @property
    def attributes(self) -> list[str]:
        """Return list of attributes tracked by ExportResults"""
        return [attr for attr in self.__slots__ if not attr.startswith("_")]

    @property
    def datetime(self) -> str:
        """Return datetime when ExportResults was created"""
        return self._datetime

    def __iadd__(self, other) -> "PushResults":
        if type(other) != PushResults:
            raise TypeError("Can only add PushResults to PushResults")

        for attribute in self.attributes:
            setattr(
                self, attribute, getattr(self, attribute) + getattr(other, attribute)
            )
        return self

    def __str__(self) -> str:
        return (
            "PushResults("
            + f"datetime={self._datetime}, "
            + ", ".join([f"{attr}={getattr(self, attr)}" for attr in self.attributes])
            + ")"
        )

    def __repr__(self) -> str:
        return self.__str__()
