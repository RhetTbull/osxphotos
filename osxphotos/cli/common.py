"""Globals and constants use by the CLI commands"""

import datetime
import os
from typing import Callable

import click

# global variable to control debug output
# set via --debug
DEBUG = False

# used to show/hide hidden commands
OSXPHOTOS_HIDDEN = not bool(os.getenv("OSXPHOTOS_SHOW_HIDDEN", default=False))

# used by snap and diff commands
OSXPHOTOS_SNAPSHOT_DIR = "/private/tmp/osxphotos_snapshots"

# where to write the crash report if osxphotos crashes
OSXPHOTOS_CRASH_LOG = os.getcwd() + "/osxphotos_crash.log"

CLI_COLOR_ERROR = "red"
CLI_COLOR_WARNING = "yellow"


def set_debug(debug: bool):
    """set debug flag"""
    global DEBUG
    DEBUG = debug


def noop(*args, **kwargs):
    """no-op function"""
    pass


def verbose_print(verbose: bool = True, timestamp: bool = False) -> Callable:
    """Create verbose function to print output

    Args:
        verbose: if True, returns verbose print function otherwise returns no-op function
        timestamp: if True, includes timestamp in verbose output

    Returns:
        function to print output
    """
    if not verbose:
        return noop

    # closure to capture timestamp
    def verbose_(*args, **kwargs):
        """print output if verbose flag set"""
        styled_args = []
        timestamp_str = str(datetime.datetime.now()) + " -- " if timestamp else ""
        for arg in args:
            if type(arg) == str:
                arg = timestamp_str + arg
                if "error" in arg.lower():
                    arg = click.style(arg, fg=CLI_COLOR_ERROR)
                elif "warning" in arg.lower():
                    arg = click.style(arg, fg=CLI_COLOR_WARNING)
            styled_args.append(arg)
        click.echo(*styled_args, **kwargs)

    return verbose_