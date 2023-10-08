"""Compute fingerprint of a file using the same algorithm as Photos.app.

I assume this uses some sort of hash to compute the fingerprint but I don't know
which algorithm is used. This code uses a private API to compute the fingerprint and
can be used to compare the fingerprint of a file to the fingerprint of a photo in the
Photos library.

Note that loading the private framework is slow so you should only do it once and
then call the fingerprint() function as needed.
"""

from __future__ import annotations

import os
import pathlib

from .platform import assert_macos

assert_macos()

import objc
from Foundation import NSURL

# Load the CloudPhotoLibrary private framework
# Use scan_classes=False to avoid loading all the classes in the framework (which is slow)
bundle = objc.loadBundle(
    "CPLResourceIdentity",
    bundle_path=objc.pathForFramework(
        "/System/Library/PrivateFrameworks/CloudPhotoLibrary.framework"
    ),
    module_globals=globals(),
    scan_classes=False,
)
CPLResourceIdentity = bundle.classNamed_("CPLResourceIdentity")


def fingerprint(filepath: str | pathlib.Path | os.PathLike) -> str:
    """Compute fingerprint of a file using the same algorithm as Photos.app

    Args:
        filepath: path to file to compute fingerprint for

    Returns: fingerprint of file

    Raises:
        FileNotFoundError if file not found
    """

    # Convert the file URL to an NSURL object
    filepath = (
        pathlib.Path(filepath) if not isinstance(filepath, pathlib.Path) else filepath
    )
    if not filepath.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")

    with objc.autorelease_pool():
        url = NSURL.fileURLWithPath_(str(filepath))

        # the method name is different on different versions of macOS
        # so try both, starting with the current version
        try:
            # this works on Ventura but not Catalina
            return CPLResourceIdentity.fingerPrintForFileAtURL_error_(url, None)
        except AttributeError:
            # this works on Catalina
            return CPLResourceIdentity.fingerPrintForFileAtURL_typeIdentifier_error_(
                url, None, None
            )
