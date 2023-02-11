"""Error logger/crash reporter decorator"""

import datetime
import functools
import platform
import sys
import traceback

from rich import print

from ._version import __version__

# store data to print out in crash log, set by set_crash_data
CRASH_DATA = {}


def set_crash_data(key_, data):
    """Set data to be printed in crash log"""
    CRASH_DATA[key_] = data


def crash_reporter(filename, message, title, postamble, *extra_args):
    """Create a crash dump file on error named filename

    On error, create a crash dump file named filename with exception and stack trace.
    message is printed to stderr
    title is printed at beginning of crash dump file
    postamble is printed to stderr after crash dump file is created
    If extra_args is not None, any additional arguments to the function will be printed to the file.
    """

    def decorated(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(message, file=sys.stderr)
                print(f"[red]{e}[/red]", file=sys.stderr)
                with open(filename, "w") as f:
                    f.write(f"{title}\n")
                    f.write(f"Created: {datetime.datetime.now()}\n")
                    f.write(f"osxphotos version: {__version__}\n")
                    f.write(f"Platform: {platform.platform()}\n")
                    f.write(f"Python version: {sys.version}\n")
                    f.write(f"sys.argv: {sys.argv}\n")
                    f.write("CRASH_DATA:\n")
                    for k, v in CRASH_DATA.items():
                        f.write(f"{k}: {v}\n")
                    for arg in extra_args:
                        f.write(f"{arg}\n")
                    f.write(f"Error: {e}\n")
                    traceback.print_exc(file=f)
                print(f"Crash log written to '{filename}'", file=sys.stderr)
                print(f"{postamble}", file=sys.stderr)
                sys.exit(1)

        return wrapped

    return decorated
