"""Helper functions to make writing an osxphotos CLI tool easy.

Includes decorator to create an osxphotos query command to be run via `osxphotos run example.py`.

May also be run via `python example.py` if you have pip installed osxphotos
"""
import logging
import sys

import click
import wrapt

from osxphotos.photosdb import PhotosDB
from osxphotos.queryoptions import query_options_from_kwargs

from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import rich_echo_error as echo_error
from .common import (
    DB_OPTION,
    QUERY_OPTIONS,
    THEME_OPTION,
    TIMESTAMP_OPTION,
    VERBOSE_OPTION,
)
from .verbose import verbose, verbose_print

logger = logging.getLogger("osxphotos")

__all__ = ["abort", "echo", "echo_error", "logger", "query_command", "verbose"]


def abort(message: str, exit_code: int = 1):
    """Abort with error message and exit code"""
    echo_error(f"[error]{message}[/]")
    sys.exit(exit_code)


@wrapt.decorator
def query_command(wrapped, instance, args, kwargs):
    """Decorator to create an osxphotos query command to be run via `osxphotos run example.py`

    The query command will be passed a list of PhotoInfo objects for the photos matching the query.
    All query options available in `osxphotos query` are available as command line options.
    The CLI will also be passed the following options:

    --verbose
    --timestamp
    --theme
    --db
    """

    @click.command()
    @QUERY_OPTIONS
    @VERBOSE_OPTION
    @TIMESTAMP_OPTION
    @THEME_OPTION
    @DB_OPTION
    @click.option("--debug", is_flag=True, help="Enable debug logging", hidden=True)
    def cli_wrapper(**kwargs):
        """Run function with query options"""
        verbose = verbose_print(
            verbose=kwargs.get("verbose_flag", 0),
            timestamp=kwargs.get("timestamp"),
            theme=kwargs.get("theme"),
        )
        query_options = query_options_from_kwargs(**kwargs)
        photosdb = PhotosDB(dbfile=kwargs.get("dbfile"), verbose=verbose)
        photos = photosdb.query(options=query_options)
        wrapped(photos=photos, **kwargs)

    return cli_wrapper(*args, **kwargs)
