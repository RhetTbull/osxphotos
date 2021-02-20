""" AdjustmentsInfo class to read adjustments data for photos edited in Apple's Photos.app
    In Catalina and Big Sur, the adjustments data (data about edits done to the photo)
    is stored in a plist file in 
    ~/Pictures/Photos Library.photoslibrary/resources/renders/X/UUID.plist
    where X is first character of the photo's UUID string and UUID is the full UUID, 
    e.g.: ~/Pictures/Photos Library.photoslibrary/resources/renders/3/30362C1D-192F-4CCD-9A2A-968F436DC0DE.plist

    Thanks to @neilpa who figured out how to decode this information:
    Reference: https://github.com/neilpa/photohack/issues/4
"""

import datetime
import json
import plistlib
import zlib

from .datetime_utils import datetime_naive_to_utc


class AdjustmentsDecodeError(Exception):
    """Could not decode adjustments plist file"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class AdjustmentsInfo:
    def __init__(self, plist_file):
        self._plist_file = plist_file
        self._plist = self._load_plist_file(plist_file)

        self._base_version = self._plist.get("adjustmentBaseVersion", None)
        self._data = self._plist.get("adjustmentData", None)
        self._editor_bundle_id = self._plist.get("adjustmentEditorBundleID", None)
        self._format_identifier = self._plist.get("adjustmentFormatIdentifier", None)
        self._format_version = self._plist.get("adjustmentFormatVersion")
        self._timestamp = self._plist.get("adjustmentTimestamp", None)
        if self._timestamp and type(self._timestamp) == datetime.datetime:
            self._timestamp = datetime_naive_to_utc(self._timestamp)

        try:
            self._adjustments = self._decode_adjustments_from_plist(self._plist)
        except Exception as e:
            self._adjustments = None

    def _decode_adjustments_from_plist(self, plist):
        """decode adjustmentData from Apple Photos adjustments

        Args:
            plist: a plist dict as loaded by plistlib

        Returns:
            decoded adjustmentsData as dict
        """

        return json.loads(
            zlib.decompress(plist["adjustmentData"], -zlib.MAX_WBITS).decode()
        )

    def _load_plist_file(self, plist_file):
        """Load plist file from disk

        Args:
            plist_file: full path to plist file

        Returns:
            plist as dict
        """
        with open(str(plist_file), "rb") as fd:
            plist_dict = plistlib.load(fd)
        return plist_dict

    @property
    def plist(self):
        """The actual adjustments plist content as a dict """
        return self._plist

    @property
    def data(self):
        """The raw adjustments data as a binary blob """
        return self._data

    @property
    def editor(self):
        """The editor bundle ID for app/plug-in which made the adjustments """
        return self._editor_bundle_id

    @property
    def format_id(self):
        """The value of the adjustmentFormatIdentifier field in the plist """
        return self._format_identifier

    @property
    def base_version(self):
        """Value of adjustmentBaseVersion field """
        return self._base_version

    @property
    def format_version(self):
        """The value of the adjustmentFormatVersion in the plist """
        return self._format_version

    @property
    def timestamp(self):
        """The time stamp of the adjustment as timezone aware datetime.datetime object or None if no timestamp """
        return self._timestamp

    @property
    def adjustments(self):
        """List of adjustment dictionaries (or empty list if none or could not be decoded)"""
        try:
            return self._adjustments["adjustments"] if self._adjustments else []
        except KeyError:
            return []

    @property
    def adj_metadata(self):
        """Metadata dictionary or None if adjustment data could not be decoded"""
        try:
            return self._adjustments["metadata"] if self._adjustments else None
        except KeyError:
            return None

    @property
    def adj_orientation(self):
        """EXIF orientation of image or 0 if none specified or None if adjustments could not be decoded"""
        try:
            return self._adjustments["metadata"]["orientation"]
        except KeyError:
            # no orientation field
            return 0
        except TypeError:
            # adjustments is None
            return 0

    @property
    def adj_format_version(self):
        """Format version for adjustments data (formatVersion field from adjustmentData) or None if adjustments could not be decoded"""
        try:
            return self._adjustments["formatVersion"] if self._adjustments else None
        except KeyError:
            return None

    @property
    def adj_version_info(self):
        """version info for adjustments data or None if adjustments data could not be decoded"""
        try:
            return self._adjustments["versionInfo"] if self._adjustments else None
        except KeyError:
            return None

    def asdict(self):
        """Returns all adjustments info as dictionary"""
        timestamp = self.timestamp
        if type(timestamp) == datetime.datetime:
            timestamp = timestamp.isoformat()

        return {
            "data": self.data,
            "editor": self.editor,
            "format_id": self.format_id,
            "base_version": self.base_version,
            "format_version": self.format_version,
            "adjustments": self.adjustments,
            "metadata": self.adj_metadata,
            "orientation": self.adj_orientation,
            "adjustment_format_version": self.adj_format_version,
            "version_info": self.adj_version_info,
            "timestamp": timestamp,
        }

    def __repr__(self):
        return f"AdjustmentsInfo(plist_file='{self._plist_file}')"
