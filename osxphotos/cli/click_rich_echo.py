"""click.echo replacement that supports rich text formatting"""

import typing as t
from io import StringIO

import click
from rich.console import Console


def rich_echo(
    message: t.Optional[t.Any] = None,
    **kwargs: t.Any,
) -> None:
    """
    Echo text to the console with rich formatting.

    This is a wrapper around click.echo that supports rich text formatting.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
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

    # rich.console.Console defaults to 80 chars if it can't auto-detect, which in this case it won't
    # so we need to set the width manually to a ridiculously large number
    width = kwargs.pop("width", 10000)
    output = StringIO()
    console = Console(force_terminal=True, file=output, width=width)
    console.print(message, end=end, **kwargs)
    click.echo(output.getvalue(), **echo_args)
