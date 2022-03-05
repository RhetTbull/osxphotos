"""click.echo replacement that supports rich text formatting"""

import inspect
import typing as t
from io import StringIO

import click
from rich.console import Console
from rich.markdown import Markdown


def rich_echo(
    message: t.Optional[t.Any] = None,
    markdown=False,
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

    if width := kwargs.pop("width", None) is None:
        width = Console().width
    output = StringIO()
    console = Console(force_terminal=True, file=output, width=width)
    if markdown:
        message = Markdown(message)
        # Markdown always adds a new line so disable unless explicitly specified
        echo_args["nl"] = echo_args.get("nl") is True
    console.print(message, end=end, **kwargs)
    click.echo(output.getvalue(), **echo_args)


def rich_echo_via_pager(
    text_or_generator: t.Union[t.Iterable[str], t.Callable[[], t.Iterable[str]], str],
    markdown: bool = False,
    **kwargs,
) -> None:
    """This function takes a text and shows it via an environment specific
    pager on stdout.

    Args:
        text_or_generator: the text to page, or alternatively, a generator emitting the text to page.
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

    console = Console()

    color = kwargs.pop("color", None)
    if color is None:
        color = bool(console.color_system)

    with console.pager(styles=color):
        for x in text_or_generator:
            if isinstance(x, str) and markdown:
                x = Markdown(x)
            console.print(x, **kwargs)
