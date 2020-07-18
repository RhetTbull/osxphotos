""" Implementation for PhotoInfo.exiftool property which returns ExifTool object for a photo """

import logging
import os

from ..exiftool import ExifTool, get_exiftool_path


@property
def exiftool(self):
    """ Returns an ExifTool object for the photo
        requires that exiftool (https://exiftool.org/) be installed
        If exiftool not installed, logs warning and returns None
        If photo path is missing, returns None
    """
    try:
        # return the memoized instance if it exists
        return self._exiftool
    except AttributeError:
        try:
            exiftool_path = get_exiftool_path()
            if self.path is not None and os.path.isfile(self.path):
                exiftool = ExifTool(self.path)
            else:
                exiftool = None
                logging.debug(f"exiftool: missing path {self.uuid}")
        except FileNotFoundError:
            # get_exiftool_path raises FileNotFoundError if exiftool not found
            exiftool = None
            logging.warning(
                f"exiftool not in path; download and install from https://exiftool.org/"
            )

        self._exiftool = exiftool
        return self._exiftool
