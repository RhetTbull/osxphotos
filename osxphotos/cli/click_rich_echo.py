"""click.echo replacement that supports rich text formatting"""

import inspect
import os
import typing as t

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

from .common import time_stamp

__all__ = [
    "get_rich_console",
    "get_rich_theme",
    "rich_click_echo",
    "rich_echo",
    "rich_echo_error",
    "rich_echo_via_pager",
    "set_rich_console",
    "set_rich_theme",
    "set_rich_timestamp",
]

# TODO: this should really be a class instead of a module with a bunch of globals

# include emoji's in rich_echo_error output
ERROR_EMOJI = True


class _Console:
    """Store console object for rich output"""

    def __init__(self):
        self._console: t.Optional[Console] = None

    @property
    def console(self):
        return self._console

    @console.setter
    def console(self, console: Console):
        self._console = console


_console = _Console()

_theme = None

_timestamp = False

# set to 1 if running tests
OSXPHOTOS_IS_TESTING = bool(os.getenv("OSXPHOTOS_IS_TESTING", default=False))


def set_rich_console(console: Console) -> None:
    """Set the console object to use for rich_echo and rich_echo_via_pager"""
    global _console
    _console.console = console


def get_rich_console() -> Console:
    """Get console object

    Returns:
        Console object
    """
    global _console
    return _console.console


def set_rich_theme(theme: Theme) -> None:
    """Set the theme to use for rich_click_echo"""
    global _theme
    _theme = theme


def get_rich_theme() -> t.Optional[Theme]:
    """Get the theme to use for rich_click_echo"""
    global _theme
    return _theme


def set_rich_timestamp(timestamp: bool) -> None:
    """Set whether to print timestamp with rich_echo, rich_echo_error, and rich_click_error"""
    global _timestamp
    _timestamp = timestamp


def rich_echo(
    message: t.Optional[t.Any] = None,
    theme=None,
    markdown=False,
    highlight=False,
    **kwargs: t.Any,
) -> None:
    """Echo text to the console with rich formatting.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        theme: optional rich.theme.Theme object to use for formatting
        markdown: if True, interpret message as Markdown
        highlight: if True, use automatic rich.print highlighting
        kwargs: any extra arguments are passed to rich.console.Console.print() and click.echo
            if kwargs contains 'file', 'nl', 'err', 'color', these are passed to click.echo,
            all other values passed to rich.console.Console.print()
    """

    # args for click.echo that may have been passed in kwargs
    echo_args = {}
    for arg in ("file", "nl", "err", "color"):
        val = kwargs.pop(arg, None)
        if val is not None:
            echo_args[arg] = val

    width = kwargs.pop("width", None)
    if width is None and OSXPHOTOS_IS_TESTING:
        # if not outputting to terminal, use a huge width to avoid wrapping
        # otherwise tests fail
        width = 10_000
    console = get_rich_console() or Console(
        theme=theme or get_rich_theme(), width=width
    )
    if markdown:
        message = Markdown(message)
        # Markdown always adds a new line so disable unless explicitly specified
    global _timestamp
    if _timestamp:
        message = time_stamp() + message
    console.print(message, highlight=highlight, **kwargs)


def rich_echo_error(
    message: t.Optional[t.Any] = None,
    theme=None,
    markdown=False,
    highlight=False,
    **kwargs: t.Any,
) -> None:
    """Echo text to the console with rich formatting and if stdout is redirected, echo to stderr

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        theme: optional rich.theme.Theme object to use for formatting
        markdown: if True, interpret message as Markdown
        highlight: if True, use automatic rich.print highlighting
        kwargs: any extra arguments are passed to rich.console.Console.print() and click.echo
            if kwargs contains 'file', 'nl', 'err', 'color', these are passed to click.echo,
            all other values passed to rich.console.Console.print()
    """

    global ERROR_EMOJI
    if ERROR_EMOJI:
        if "[error]" in message:
            message = f":cross_mark-emoji:  {message}"
        elif "[warning]" in message:
            message = f":warning-emoji:  {message}"

    console = get_rich_console() or Console(theme=theme or get_rich_theme())
    if not console.is_terminal:
        # if stdout is redirected, echo to stderr
        rich_click_echo(
            message,
            theme=theme or get_rich_theme(),
            markdown=markdown,
            highlight=highlight,
            **kwargs,
            err=True,
        )
    else:
        rich_echo(
            message,
            theme=theme or get_rich_theme(),
            markdown=markdown,
            highlight=highlight,
            **kwargs,
        )


def rich_click_echo(
    message: t.Optional[t.Any] = None,
    theme=None,
    markdown=False,
    highlight=False,
    **kwargs: t.Any,
) -> None:
    """Echo text to the console with rich formatting using click.echo

    This is a wrapper around click.echo that supports rich text formatting.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        theme: optional rich.theme.Theme object to use for formatting
        markdown: if True, interpret message as Markdown
        highlight: if True, use automatic rich.print highlighting
        kwargs: any extra arguments are passed to rich.console.Console.print() and click.echo
            if kwargs contains 'file', 'nl', 'err', 'color', these are passed to click.echo,
            all other values passed to rich.console.Console.print()
    """

    # args for click.echo that may have been passed in kwargs
    echo_args = {}
    for arg in ("file", "nl", "err", "color"):
        val = kwargs.pop(arg, None)
        if val is not None:
            echo_args[arg] = val

    # click.echo will include "\n" so don't add it here unless specified
    end = kwargs.pop("end", "")

    if width := kwargs.pop("width", None) is None:
        # if not outputting to terminal, use a huge width to avoid wrapping
        # otherwise tests fail
        temp_console = Console()
        width = temp_console.width if temp_console.is_terminal else 10_000
    console = Console(
        force_terminal=True,
        theme=theme or get_rich_theme(),
        width=width,
    )
    if markdown:
        message = Markdown(message)
        # Markdown always adds a new line so disable unless explicitly specified
        echo_args["nl"] = echo_args.get("nl") is True
    global _timestamp
    if _timestamp:
        message = time_stamp() + message
    with console.capture() as capture:
        console.print(message, end=end, highlight=highlight, **kwargs)
    click.echo(capture.get(), **echo_args)


def rich_echo_via_pager(
    text_or_generator: t.Union[t.Iterable[str], t.Callable[[], t.Iterable[str]], str],
    theme: t.Optional[Theme] = None,
    highlight=False,
    markdown: bool = False,
    **kwargs,
) -> None:
    """This function takes a text and shows it via an environment specific
    pager on stdout.

    Args:
        text_or_generator: the text to page, or alternatively, a generator emitting the text to page.
        theme: optional rich.theme.Theme object to use for formatting
        markdown: if True, interpret message as Markdown
        highlight: if True, use automatic rich.print highlighting
        **kwargs: if "color" in kwargs, works the same as click.echo_via_pager(color=color)
        otherwise any kwargs are passed to rich.Console.print()
    """
    if inspect.isgeneratorfunction(text_or_generator):
        text_or_generator = t.cast(t.Callable[[], t.Iterable[str]], text_or_generator)()
    elif isinstance(text_or_generator, str):
        text_or_generator = [text_or_generator]
    else:
        try:
            text_or_generator = iter(text_or_generator)
        except TypeError:
            text_or_generator = [text_or_generator]

    console = _console.console or Console(theme=theme)

    color = kwargs.pop("color", True)

    with console.pager(styles=color):
        for x in text_or_generator:
            if isinstance(x, str) and markdown:
                x = Markdown(x)
            console.print(x, highlight=highlight, **kwargs)
