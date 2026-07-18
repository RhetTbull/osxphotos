"""Error logger/crash reporter decorator"""

from __future__ import annotations

import datetime
import functools
import platform
import sys
import time
import traceback
from typing import Any, Callable

import click
from rich import print

from ._version import __version__

# store data to print out in crash log, set by set_crash_data
_global_crash_data = {}

# store callback functions to execute if a crash is handled
_global_callbacks = {}


def set_crash_data(key_: Any, data: Any):
    """Set data to be printed in crash log"""
    _global_crash_data[key_] = data


def register_crash_callback(func: Callable, message: str | None = None) -> int:
    """Register callback to be run if crash is caught.

    Args:
        func: callable that will be called (with no args) by crash_reporter
        message: optional message

    Returns:
        id for callback which may be used with unregister_crash_callback() to remove the callback.

    Note: Multiple callabacks may be registered by calling this function repeatedly.
        Callbacks will be executed in order they are registered.
    """

    callback_id = time.monotonic_ns()
    _global_callbacks[callback_id] = (func, message)
    return callback_id


def unregister_crash_callback(callback_id: int):
    """Unregister a crash callback previously registered with register_crash_callback().

    Args:
        callback_id: the ID of the callback to unregister as returned by register_crash_callback()

    Raises:
        ValueError if the callback_id is not valid
    """
    try:
        del _global_callbacks[callback_id]
    except KeyError:
        raise ValueError(f"Invalid callback_id: {callback_id}")


def crash_reporter(
    filename: str, message: str, title: str, postamble: str, *extra_args: Any
):
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
            except (click.ClickException, click.Abort, click.exceptions.Exit):
                raise
            except Exception as e:
                print(message, file=sys.stderr)
                print(f"[red]{e}[/red]", file=sys.stderr)

                # Run any registered crash callbacks. These are one-shot crash
                # handlers, so unregister each after running it; otherwise a
                # callback lingers in the global registry after the crash is
                # handled and fires again on a later, unrelated crash in the same
                # process. For example, an interrupted `export --ramdb` registers
                # a "write database" callback (osxphotos/cli/export.py) that is
                # only unregistered on the success path, so a crashed export would
                # leak it and break crash handling in a reused interpreter such as
                # the test suite. Iterate over a snapshot since we mutate the
                # registry, and don't let a failing callback prevent the crash log
                # from being written.
                for callback_id, (callback_func, msg) in list(
                    _global_callbacks.items()
                ):
                    _global_callbacks.pop(callback_id, None)
                    if msg:
                        print(msg)
                    try:
                        callback_func()
                    except Exception as callback_error:  # noqa: BLE001
                        print(
                            f"[red]Error running crash callback: {callback_error}[/red]",
                            file=sys.stderr,
                        )

                with open(filename, "w") as f:
                    f.write(f"{title}\n")
                    f.write(f"Created: {datetime.datetime.now()}\n")
                    f.write(f"osxphotos version: {__version__}\n")
                    f.write(f"Platform: {platform.platform()}\n")
                    f.write(f"Python version: {sys.version}\n")
                    f.write(f"sys.argv: {sys.argv}\n")
                    f.write("CRASH_DATA:\n")
                    for k, v in _global_crash_data.items():
                        f.write(f"{k}: {v}\n")
                    for arg in extra_args:
                        f.write(f"{arg}\n")
                    f.write(f"Error: {e}\n")
                    traceback.print_exc(file=f)
                print(f"Crash log written to '{filename}'", file=sys.stderr)
                print(f"{postamble}", file=sys.stderr)
                sys.exit(1)

        wrapped.__osxphotos_crash_reporter__ = True
        return wrapped

    return decorated
