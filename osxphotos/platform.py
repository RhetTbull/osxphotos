"""Functions for multi-platform support"""

import platform
import sys

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
