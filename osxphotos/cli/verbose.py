"""helper functions for printing verbose output"""

from __future__ import annotations

import os
import typing as t
from datetime import datetime

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

__all__ = [
    "get_verbose_console",
    "get_verbose_level",
    "set_verbose_level",
    "verbose_print",
]


def set_verbose_level(level: int):
    """Set verbose level"""
    global __verbose_level
    __verbose_level = level


def get_verbose_level() -> int:
    """Get verbose level"""
    global __verbose_level
    return __verbose_level


class _Console:
    """Store console object for verbose output"""

    def __init__(self):
        self._console: t.Optional[Console] = None

    @property
    def console(self):
        return self._console

    @console.setter
    def console(self, console: Console):
        self._console = console


_console = _Console()


def noop(*args, **kwargs):
    """no-op function"""
    pass


def get_verbose_console(theme: t.Optional[Theme] = None) -> Console:
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
    verbose: bool = True,
    timestamp: bool = False,
    rich: bool = True,
    theme: str | None = None,
    highlight: bool = False,
    file: t.Optional[t.IO] = None,
    level: int = 1,
    **kwargs: t.Any,
) -> t.Callable[..., None]:
    """Configure verbose printing and create verbose function to print output

    Args:
        verbose: if True, returns verbose print function otherwise returns no-op function
        timestamp: if True, includes timestamp in verbose output
        rich: use rich.print instead of click.echo
        highlight: if True, use automatic rich.print highlighting
        theme: optional name of theme to use for formatting (will be loaded by get_theme())
        file: optional file handle to write to instead of stdout
        level: verbose level to print output
        kwargs: any extra arguments to pass to click.echo or rich.print depending on whether rich==True

    Returns:
        function to print output

    Note: sets the console for rich_echo to be the same as the console used for verbose output
    """

    color_theme = get_theme(theme)
    verbose_function = _verbose_print_function(
        verbose=verbose,
        timestamp=timestamp,
        rich=rich,
        theme=color_theme,
        highlight=highlight,
        file=file,
        level=level,
        **kwargs,
    )

    # set console for rich_echo to be same as for verbose
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

    return verbose_function


def _verbose_print_function(
    verbose: bool = True,
    timestamp: bool = False,
    rich: bool = False,
    highlight: bool = False,
    theme: t.Optional[Theme] = None,
    file: t.Optional[t.IO] = None,
    level: int = 1,
    **kwargs: t.Any,
) -> t.Callable[..., None]:
    """Create verbose function to print output

    Args:
        verbose: if True, returns verbose print function otherwise returns no-op function
        timestamp: if True, includes timestamp in verbose output
        rich: use rich.print instead of click.echo
        highlight: if True, use automatic rich.print highlighting
        theme: optional rich.theme.Theme object to use for formatting
        file: optional file handle to write to instead of stdout
        level: verbose level to print output
        kwargs: any extra arguments to pass to click.echo or rich.print depending on whether rich==True

    Returns:
        function to print output
    """
    if not verbose:
        return noop

    set_verbose_level(level)

    global _console
    if file:
        _console.console = Console(theme=theme, file=file)
    else:
        _console.console = Console(theme=theme, width=10_000)

    # closure to capture timestamp
    def verbose_(*args, level: int = 1):
        """print output if verbose flag set"""
        if get_verbose_level() < level:
            return
        styled_args = []
        timestamp_str = f"{str(datetime.now())} -- " if timestamp else ""
        for arg in args:
            if type(arg) == str:
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
            if type(arg) == str:
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
            if type(arg) == str:
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
