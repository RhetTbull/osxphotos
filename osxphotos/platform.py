"""Functions for multi-platform support"""

import logging
import platform
import sys

from ._constants import _TESTED_OS_VERSIONS

logger = logging.getLogger("osxphotos")

is_macos = sys.platform == "darwin"


def assert_macos():
    assert is_macos, "This feature only runs on macOS"


def get_macos_version():
    assert_macos()
    # returns tuple of str containing OS version
    # e.g. 10.13.6 = ("10", "13", "6")
    version = platform.mac_ver()[0].split(".")
    if len(version) == 2:
        (ver, major) = version
        minor = "0"
    elif len(version) == 3:
        (ver, major, minor) = version
    else:
        raise (
            ValueError(
                f"Could not parse version string: {platform.mac_ver()} {version}"
            )
        )
    return (ver, major, minor)


def check_and_warn_macos_version():
    """Check OS version and warn if not tested"""
    system = platform.system()
    (ver, major, _) = get_macos_version() if is_macos else (None, None, None)
    if system == "Darwin" and (
        ((ver, major) not in _TESTED_OS_VERSIONS)
        and (ver, None) not in _TESTED_OS_VERSIONS
    ):
        tested_versions = ", ".join(
            f"{v}.{m}" for (v, m) in _TESTED_OS_VERSIONS if m is not None
        )
        logger.warning(
            f"WARNING: This module has only been tested with macOS versions [{tested_versions}]: you have {system}, OS version: {ver}.{major}"
        )
