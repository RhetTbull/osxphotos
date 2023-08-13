"""helper functions for printing verbose output"""

from __future__ import annotations

import os
from datetime import datetime
from typing import IO, Any, Callable, Optional

import click
from rich.console import Console
from rich.theme import Theme

from .click_rich_echo import (
    rich_click_echo,
    set_rich_console,
    set_rich_theme,
    set_rich_timestamp,
)
from .color_themes import get_theme
from .common import CLI_COLOR_ERROR, CLI_COLOR_WARNING, time_stamp

# set to 1 if running tests
OSXPHOTOS_IS_TESTING = bool(os.getenv("OSXPHOTOS_IS_TESTING", default=False))

# include error/warning emoji's in verbose output
ERROR_EMOJI = True

# global to store verbose level
__verbose_level = 1

# global verbose function
__verbose_function: Callable[..., None] | None = None


__all__ = [
    "get_verbose_console",
    "get_verbose_level",
    "set_verbose_level",
    "verbose_print",
    "verbose",
]


def _reset_verbose_globals():
    """Reset globals for testing"""
    global __verbose_level
    global __verbose_function
    global _console
    __verbose_level = 1
    __verbose_function = None
    _console = _Console()


def noop(*args, **kwargs):
    """no-op function"""
    pass


def verbose(*args, level: int = 1):
    """Print verbose output

    Args:
        *args: arguments to pass to verbose function for printing
        level: verbose level; if level > get_verbose_level(), output is suppressed
    """

    # Notes:
    #     Normally you should use verbose_print() to get the verbose function instead of calling this directly
    #     This is here so that verbose can be directly imported and used in other modules without calling verbose_print()
    #     Use of verbose_print() will set the verbose function so that calling verbose() will work as expected
    global __verbose_function
    if __verbose_function is None:
        return
    __verbose_function(*args, level=level)


def set_verbose_level(level: int):
    """Set verbose level"""
    global __verbose_level
    global __verbose_function
    __verbose_level = level
    if level > 0 and __verbose_function is None:
        # if verbose level set but verbose function not set, set it to default
        # verbose_print sets the global __verbose_function
        __verbose_function = _verbose_print_function(level)
    elif level == 0 and __verbose_function is not None:
        # if verbose level set to 0 but verbose function is set, set it to no-op
        __verbose_function = noop


def get_verbose_level() -> int:
    """Get verbose level"""
    global __verbose_level
    return __verbose_level


class _Console:
    """Store console object for verbose output"""

    def __init__(self):
        self._console: Optional[Console] = None

    @property
    def console(self):
        return self._console

    @console.setter
    def console(self, console: Console):
        self._console = console


_console = _Console()


def get_verbose_console(theme: Optional[Theme] = None) -> Console:
    """Get console object or create one if not already created

    Args:
        theme: optional rich.theme.Theme object to use for formatting

    Returns:
        Console object
    """
    global _console
    if _console.console is None:
        _console.console = Console(force_terminal=True, theme=theme)
    return _console.console


def verbose_print(
    verbose: int = 1,
    timestamp: bool = False,
    rich: bool = True,
    theme: str | None = None,
    highlight: bool = False,
    file: Optional[IO] = None,
    **kwargs: Any,
) -> Callable[..., None]:
    """Configure verbose printing and create verbose function to print output

    Args:
        verbose: if > 0, returns verbose print function otherwise returns no-op function; the value of verbose is the verbose level
        timestamp: if True, includes timestamp in verbose output
        rich: use rich.print instead of click.echo
        highlight: if True, use automatic rich.print highlighting
        theme: optional name of theme to use for formatting (will be loaded by get_theme())
        file: optional file handle to write to instead of stdout
        kwargs: any extra arguments to pass to click.echo or rich.print depending on whether rich==True

    Returns:
        function to print output

    Note: sets the console for rich_echo to be the same as the console used for verbose output
    """

    set_verbose_level(verbose)
    color_theme = get_theme(theme)
    verbose_function = _verbose_print_function(
        verbose=verbose,
        timestamp=timestamp,
        rich=rich,
        theme=color_theme,
        highlight=highlight,
        file=file,
        **kwargs,
    )

    # set console for rich_echo to be same as for verbose
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

    # set global verbose function to match
    global __verbose_function
    __verbose_function = verbose_function

    return verbose_function


def _verbose_print_function(
    verbose: bool = True,
    timestamp: bool = False,
    rich: bool = False,
    highlight: bool = False,
    theme: Optional[Theme] = None,
    file: Optional[IO] = None,
    **kwargs: Any,
) -> Callable[..., None]:
    """Create verbose function to print output

    Args:
        verbose: if > 0, returns verbose print function otherwise returns no-op function; the value of verbose is the verbose level
        timestamp: if True, includes timestamp in verbose output
        rich: use rich.print instead of click.echo
        highlight: if True, use automatic rich.print highlighting
        theme: optional rich.theme.Theme object to use for formatting
        file: optional file handle to write to instead of stdout
        kwargs: any extra arguments to pass to click.echo or rich.print depending on whether rich==True

    Returns:
        function to print output
    """

    # configure console even if verbose is False so that rich_echo will work correctly
    global _console
    if file:
        _console.console = Console(theme=theme, file=file)
    else:
        _console.console = Console(theme=theme, width=10_000)

    if not verbose:
        return noop

    # closure to capture timestamp
    def verbose_(*args, level: int = 1):
        """print output if verbose flag set"""
        if get_verbose_level() < level:
            return
        styled_args = []
        timestamp_str = f"{str(datetime.now())} -- " if timestamp else ""
        for arg in args:
            if isinstance(arg, str):
                arg = timestamp_str + arg
                if "error" in arg.lower():
                    arg = click.style(arg, fg=CLI_COLOR_ERROR)
                elif "warning" in arg.lower():
                    arg = click.style(arg, fg=CLI_COLOR_WARNING)
            styled_args.append(arg)
        click.echo(*styled_args, **kwargs, file=file or None)

    def rich_verbose_(*args, level: int = 1):
        """rich.print output if verbose flag set"""
        if get_verbose_level() < level:
            return
        global ERROR_EMOJI
        timestamp_str = time_stamp() if timestamp else ""
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                if "error" in arg.lower():
                    arg = f"[error]{arg}"
                    if ERROR_EMOJI:
                        arg = f":cross_mark-emoji:  {arg}"
                elif "warning" in arg.lower():
                    arg = f"[warning]{arg}"
                    if ERROR_EMOJI:
                        arg = f":warning-emoji:  {arg}"
                arg = timestamp_str + arg
            new_args.append(arg)
        _console.console.print(*new_args, highlight=highlight, **kwargs)

    def rich_verbose_testing_(*args, level: int = 1):
        """print output if verbose flag set using rich.print"""
        if get_verbose_level() < level:
            return
        global ERROR_EMOJI
        timestamp_str = time_stamp() if timestamp else ""
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                if "error" in arg.lower():
                    arg = f"[error]{arg}"
                    if ERROR_EMOJI:
                        arg = f":cross_mark-emoji:  {arg}"
                elif "warning" in arg.lower():
                    arg = f"[warning]{arg}"
                    if ERROR_EMOJI:
                        arg = f":warning-emoji:  {arg}"
                arg = timestamp_str + arg
            new_args.append(arg)
        rich_click_echo(*new_args, theme=theme, **kwargs)

    if rich and not OSXPHOTOS_IS_TESTING:
        return rich_verbose_
    elif rich:
        return rich_verbose_testing_
    else:
        return verbose_
