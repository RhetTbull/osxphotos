""" Disclaim the application when running on macOS so that permission requests come from the application itself
instead of the terminal.

To use this, the libdisclaim.dylib library must be built and placed in the same directory as this file
or provided as an argument to the disclaim function.

Reference: http://qt.io/blog/the-curious-case-of-the-responsible-process
"""

import ctypes
import os
import platform
import sys


def pyinstaller() -> bool:
    """Return True if the application is running from a PyInstaller bundle."""
    # PyInstaller bootloader sets a flag
    return hasattr(sys, "_MEIPASS")


def pyapp() -> bool:
    """Check if we are running in a pyapp environment."""
    return os.environ.get("PYAPP") == "1"


def disclaim(library_path: str | None = None):
    """Run this function to disclaim the application and set the responsible process to the caller.

    Args:
        library_path: The path to the libdisclaim.dylib library.
            If not provided, libdisclaim.dylib will be loaded from the the same directory as this file.
    """

    if sys.platform != "darwin":
        return

    # Avoid redundant disclaims
    env_marker = f"PY_DISCLAIMED-{sys.argv[0]}"
    if os.environ.get(env_marker):
        return
    os.environ[env_marker] = "1"

    if pyinstaller():
        # If running from pyinstaller, the _MEIPASS2 environment variable is set
        # The bootloader has cleared the _MEIPASS2 environment variable by the
        # time we get here, which means re-launching the executable disclaimed
        # will unpack the binary again. To avoid this we reset _MEIPASS2 again,
        # so that our re-launch will pick up at second stage of the bootstrap.
        os.environ["_MEIPASS2"] = sys._MEIPASS

    # Load the disclaim library and call the disclaim function
    machine = platform.machine()
    library_path = library_path or os.path.join(
        os.path.dirname(__file__), "lib", f"libdisclaim_{machine}.dylib"
    )
    libdisclaim = ctypes.cdll.LoadLibrary(library_path)
    libdisclaim.disclaim()
