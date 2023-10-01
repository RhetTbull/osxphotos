"""Helper functions to make writing an osxphotos CLI tool easy.

Includes decorator to create an osxphotos query command to be run via `osxphotos run example.py`.

May also be run via `python example.py` if you have pip installed osxphotos
"""

from __future__ import annotations

import logging
import sys
import typing as t  # match style used in Click source code

import click

from osxphotos.photoquery import QueryOptions, query_options_from_kwargs
from osxphotos.photosdb import PhotosDB
from osxphotos.sqlitekvstore import SQLiteKVStore

from .cli_params import (
    _DB_PARAMETER,
    _QUERY_PARAMETERS_DICT,
    DB_OPTION,
    THEME_OPTION,
    TIMESTAMP_OPTION,
    VERBOSE_OPTION,
)
from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import rich_echo_error as echo_error
from .click_rich_echo import set_rich_theme
from .color_themes import get_theme
from .verbose import get_verbose_level, verbose, verbose_print

logger = logging.getLogger("osxphotos")

# ensure echo, echo_error are configured with correct theme
set_rich_theme(get_theme())

__all__ = [
    "abort",
    "echo",
    "echo_error",
    "logger",
    "query_command",
    "selection_command",
    "verbose",
]


def abort(message: str, exit_code: int = 1):
    """Abort with error message and exit code"""
    echo_error(f"[error]{message}[/]")
    sys.exit(exit_code)


def config_verbose_callback(ctx: click.Context, param: click.Parameter, value: t.Any):
    """Callback for --verbose option"""
    # calling verbose_print() will set the verbose level for the verbose() function
    theme = ctx.params.get("theme")
    timestamp = ctx.params.get("timestamp")
    verbose_print(verbose=value, timestamp=timestamp, theme=theme)
    return value


def config_theme_callback(ctx: click.Context, param: click.Parameter, value: t.Any):
    """Callback for --theme option"""
    # calling verbose_print() will set the verbose level for the verbose() function
    # if --verbose is passed after --theme, this callback won't have access it to
    # and verbose_option will be None
    # set to zero and if --verbose is passed, it will be set correctly by the
    # config_verbose_callback (#1186)
    verbose = ctx.params.get("verbose_option") or get_verbose_level()
    timestamp = ctx.params.get("timestamp")
    verbose_print(verbose=verbose, timestamp=timestamp, theme=value)
    return value


def get_photos_for_query(ctx: click.Context):
    """Return list of PhotoInfo objects for the photos matching the query options in ctx.params"""
    options = query_options_from_kwargs(**ctx.params)
    db = ctx.params.get("db")
    photosdb = PhotosDB(dbfile=db, verbose=verbose)
    return photosdb.query(options=options)


def get_selected_photos(ctx: click.Context):
    """Return list of PhotoInfo objects for the photos currently selected in Photos.app"""
    photosdb = PhotosDB(verbose=verbose)
    return photosdb.query(options=QueryOptions(selected=True))


class QueryCommand(click.Command):
    """
    Click command to create an osxphotos query command.

    This class is used by the query_command decorator to create a click command
    that runs an osxphotos query. It will automatically add the query options as
    well as the --verbose, --timestamp, --theme, and --db options.
    """

    standalone_mode = False

    def __init__(
        self,
        name: t.Optional[str],
        context_settings: t.Optional[t.Dict[str, t.Any]] = None,
        callback: t.Optional[t.Callable[..., t.Any]] = None,
        params: t.Optional[t.List[click.Parameter]] = None,
        help: t.Optional[str] = None,
        epilog: t.Optional[str] = None,
        short_help: t.Optional[str] = None,
        options_metavar: t.Optional[str] = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
    ) -> None:
        self.params = params or []
        self.params.append(
            click.Option(
                param_decls=["--verbose", "-V", "verbose_flag"],
                count=True,
                help="Print verbose output; may be specified multiple times for more verbose output.",
                callback=config_verbose_callback,
            )
        )
        self.params.append(
            click.Option(
                param_decls=["--timestamp"],
                is_flag=True,
                help="Add time stamp to verbose output",
            )
        )
        self.params.append(
            click.Option(
                param_decls=["--theme"],
                metavar="THEME",
                type=click.Choice(
                    ["dark", "light", "mono", "plain"], case_sensitive=False
                ),
                callback=config_theme_callback,
                help="Specify the color theme to use for output. "
                "Valid themes are 'dark', 'light', 'mono', and 'plain'. "
                "Defaults to 'dark' or 'light' depending on system dark mode setting.",
            )
        )
        self.params.append(_DB_PARAMETER)
        self.params.extend(_QUERY_PARAMETERS_DICT.values())

        super().__init__(
            name,
            context_settings,
            callback,
            self.params,
            help,
            epilog,
            short_help,
            options_metavar,
            add_help_option,
            no_args_is_help,
            hidden,
            deprecated,
        )

    def make_context(
        self,
        info_name: t.Optional[str],
        args: t.List[str],
        parent: t.Optional[click.Context] = None,
        **extra: t.Any,
    ) -> click.Context:
        ctx = super().make_context(info_name, args, parent, **extra)
        ctx.obj = self
        photos = get_photos_for_query(ctx)
        ctx.params["photos"] = photos

        # remove params handled by this class
        ctx.params.pop("verbose_flag")
        ctx.params.pop("timestamp")
        ctx.params.pop("theme")
        return ctx


class SelectionCommand(click.Command):
    """
    Click command to create an osxphotos selection command that runs on selected photos.

    This class is used by the query_command decorator to create a click command
    that runs on currently selected photos.

    The --verbose, --timestamp, --theme, and --db options will also be added to the command.
    """

    standalone_mode = False

    def __init__(
        self,
        name: t.Optional[str],
        context_settings: t.Optional[t.Dict[str, t.Any]] = None,
        callback: t.Optional[t.Callable[..., t.Any]] = None,
        params: t.Optional[t.List[click.Parameter]] = None,
        help: t.Optional[str] = None,
        epilog: t.Optional[str] = None,
        short_help: t.Optional[str] = None,
        options_metavar: t.Optional[str] = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
    ) -> None:
        self.params = params or []
        self.params.append(
            click.Option(
                param_decls=["--verbose", "-V", "verbose_flag"],
                count=True,
                help="Print verbose output; may be specified multiple times for more verbose output.",
                callback=config_verbose_callback,
            )
        )
        self.params.append(
            click.Option(
                param_decls=["--timestamp"],
                is_flag=True,
                help="Add time stamp to verbose output",
            )
        )
        self.params.append(
            click.Option(
                param_decls=["--theme"],
                metavar="THEME",
                type=click.Choice(
                    ["dark", "light", "mono", "plain"], case_sensitive=False
                ),
                callback=config_theme_callback,
                help="Specify the color theme to use for output. "
                "Valid themes are 'dark', 'light', 'mono', and 'plain'. "
                "Defaults to 'dark' or 'light' depending on system dark mode setting.",
            )
        )
        self.params.append(
            click.Option(
                param_decls=["--library", "--db"],
                required=False,
                metavar="PHOTOS_LIBRARY_PATH",
                default=None,
                help=(
                    "Specify Photos database path. "
                    "Path to Photos library/database can be specified using either --db "
                    "or directly as PHOTOS_LIBRARY positional argument. "
                    "If neither --db or PHOTOS_LIBRARY provided, will attempt to find the library "
                    "to use in the following order: 1. last opened library, 2. system library, 3. ~/Pictures/Photos Library.photoslibrary"
                ),
                type=click.Path(exists=True),
            )
        )
        super().__init__(
            name,
            context_settings,
            callback,
            self.params,
            help,
            epilog,
            short_help,
            options_metavar,
            add_help_option,
            no_args_is_help,
            hidden,
            deprecated,
        )

    def make_context(
        self,
        info_name: t.Optional[str],
        args: t.List[str],
        parent: t.Optional[click.Context] = None,
        **extra: t.Any,
    ) -> click.Context:
        ctx = super().make_context(info_name, args, parent, **extra)
        ctx.obj = self
        photos = get_selected_photos(ctx)
        ctx.params["photos"] = photos

        # remove params handled by this class
        ctx.params.pop("verbose_flag")
        ctx.params.pop("timestamp")
        ctx.params.pop("theme")
        return ctx


def query_command(name=None, cls=QueryCommand, **attrs):
    """Decorator to create an osxphotos command to be run via `osxphotos run example.py`

    The command will be passed a list of PhotoInfo objects for all photos in Photos
    matching the query options or all photos if no query options are specified.

    The standard osxphotos query options will be added to the command.

    The CLI will also be passed the following options:

    --verbose
    --timestamp
    --theme
    --db
    """
    if callable(name) and cls:
        return click.command(cls=cls, **attrs)(name)

    return click.command(name, cls=cls, **attrs)


def selection_command(name=None, cls=SelectionCommand, **attrs):
    """Decorator to create an osxphotos command to be run via `osxphotos run example.py`

    The command will be passed a list of PhotoInfo objects for all photos selected in Photos.
    The CLI will also be passed the following options:

    --verbose
    --timestamp
    --theme
    --db
    """
    if callable(name) and cls:
        return click.command(cls=cls, **attrs)(name)

    return click.command(name, cls=cls, **attrs)
