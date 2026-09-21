"""Functions for multi-platform support"""

import logging
import platform
import sys

from ._constants import _TESTED_OS_VERSIONS

logger = logging.getLogger("osxphotos")

is_macos = sys.platform == "darwin"

if is_macos:
    # Load the Photos framework (PhotoKit) here, before any other osxphotos
    # module imports photoscript; see #2212.
    #
    # /System/Applications/Photos.app and /System/Library/Frameworks/Photos.framework
    # both declare the bundle identifier "com.apple.Photos". photoscript compiles a
    # `tell application "Photos"` AppleScript at import time, which registers the
    # Photos.app bundle under that identifier in this process. pyobjc >= 10 looks the
    # framework up by identifier before falling back to its path, so it finds the app
    # bundle, tries to dynamically load an app executable, and macOS logs
    # "Attempt to load executable of a type that cannot be dynamically loaded for
    # CFBundle ... </System/Applications/Photos.app>" to stderr. The fallback then
    # succeeds, so the warning is harmless but confusing. Loading the framework first
    # claims the identifier and avoids it entirely.
    try:
        import Photos
    except ImportError:
        # pyobjc-framework-Photos is missing; anything that needs PhotoKit will
        # raise a more useful error when it is actually used
        logger.debug("Could not import Photos framework")


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
