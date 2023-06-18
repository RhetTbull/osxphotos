"""Sample query command for osxphotos

This shows how simple it is to create a command line tool using osxphotos to process your photos.

Using the @selection_command decorator turns your function to a full-fledged command line app that
can be run via `osxphotos run cli_example_1.py` or `python cli_example_1.py` if you have pip installed osxphotos.

Using this decorator makes it very easy to create a quick command line tool that can operate on
a subset of your photos. Additionally, writing a command in this way makes it easy to later
incorporate the command into osxphotos as a full-fledged command.

The decorator will add the following options to your command:
--verbose
--timestamp
--theme
--db
--debug (hidden, won't show in help)

The decorated function will get the selected photos and pass the list of PhotoInfo objects
to your function.  You can then do whatever you want with the photos.
"""

from __future__ import annotations

import osxphotos
from osxphotos.cli import selection_command, verbose


@selection_command
def example(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Sample command for osxphotos. Prints out the filename and date of each photo
    currently selected in Photos.app.

    Whatever text you put in the function's docstring here, will be used as the command's
    help text when run via `osxphotos run cli_example_1.py --help` or `python cli_example_1.py --help`
    """

    # verbose() will print to stdout if --verbose option is set
    # you can optionally provide a level (default is 1) to print only if --verbose is set to that level
    # for example: -VV or --verbose --verbose == level 2
    verbose(f"Found {len(photos)} photo(s)")
    verbose("This message will only be printed if verbose level 2 is set", level=2)

    # do something with photos here
    for photo in photos:
        # photos is a list of PhotoInfo objects
        # see: https://rhettbull.github.io/osxphotos/reference.html#osxphotos.PhotoInfo
        verbose(f"Processing {photo.original_filename}")
        print(f"{photo.original_filename} {photo.date}")
        ...


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    example()
