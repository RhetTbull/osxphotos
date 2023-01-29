"""Sample query command for osxphotos

This shows how simple it is to create a command line tool using osxphotos to process your photos.

Using the @query_command decorator turns your function to a full-fledged command line app that
can be run via `osxphotos run example.py` or `python example.py` if you have pip installed osxphotos.

Using this decorator makes it very easy to create a quick command line tool that can operate on
a subset of your photos. Additionally, writing a command in this way makes it easy to later
incorporate the command into osxphotos as a full-fledged command.

The decorator will add all the query options available in `osxphotos query` as command line options
as well as the following options:
--verbose
--timestamp
--theme
--db
--debug (hidden, won't show in help)

The decorated function will perform the query and pass the list of filtered PhotoInfo objects
to your function.  You can then do whatever you want with the photos.

For example, to run the command on only selected photos:

    osxphotos run example.py --selected

To run the command on all photos with the keyword "foo":

    osxphotos run example.py --keyword foo

The following helper functions may be useful and can be imported from osxphotos.cli:

    abort(message: str, exit_code: int = 1)
        Abort with error message and exit code
    echo(message: str)
        Print message to stdout using rich formatting
    echo_error(message: str)
        Print message to stderr using rich formatting
    logger: logging.Logger
        Python logger for osxphotos; for example, logger.debug("debug message")
    verbose(*args, level: int = 1)
        Print args to stdout if --verbose option is set
    query_command: decorator to create an osxphotos query command

The verbose, echo, and echo_error functions use rich formatting to print messages to stdout and stderr.
See https://github.com/Textualize/rich for more information on rich formatting.

In addition to standard rich formatting styles, the following styles will be defined
(and can be changed using --theme):

    [change]: something change
    [no_change]: indicate no change
    [count]: a count
    [error]: an error
    [filename]: a filename
    [filepath]: a filepath
    [num]: a number
    [time]: a time or date
    [tz]: a timezone
    [warning]: a warning
    [uuid]: a uuid
"""

from __future__ import annotations

import osxphotos
from osxphotos.cli import abort, echo, echo_error, logger, query_command, verbose


@query_command
def example(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Sample query command for osxphotos. Prints out the filename and date of each photo.

    Whatever text you put in the function's docstring here, will be used as the command's
    help text when run via `osxphotos run example.py --help` or `python example.py --help`
    """

    # abort will print the message to stderr and exit with the given exit code
    if not photos:
        abort("Nothing to do!", 1)

    # verbose() will print to stdout if --verbose option is set
    # you can optionally provide a level (default is 1) to print only if --verbose is set to that level
    # for example: -VV or --verbose --verbose == level 2
    verbose(f"Found [count]{len(photos)}[/] photos")
    verbose("This message will only be printed if verbose level 2 is set", level=2)

    # the logger is a python logging.Logger object
    # debug messages will only be printed if --debug option is set
    logger.debug(f"{kwargs=}")

    # do something with photos here
    for photo in photos:
        # photos is a list of PhotoInfo objects
        # see: https://rhettbull.github.io/osxphotos/reference.html#osxphotos.PhotoInfo
        echo(f"[filename]{photo.original_filename}[/] [time]{photo.date}[/]")

    # echo_error will print to stderr
    # if you add [warning] or [error], it will be formatted accordingly
    # and include an emoji to make the message stand out
    echo_error("[warning]This is a warning message!")
    echo_error("[error]This is an error message!")


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    example()
