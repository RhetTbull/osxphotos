"""utilities for working with rich markup"""

from typing import Callable


def add_rich_markup_tag(tag: str, rich=True) -> Callable:
    """Returns function that rich markup tags to string"""

    if not rich:
        return no_markup

    def add_tag(msg: str) -> str:
        """Add tag to string"""
        return f"[{tag}]{msg}[/{tag}]"

    return add_tag


def no_markup(msg: str) -> str:
    """Return msg without markup"""
    return msg


__all__ = ["add_rich_markup_tag", "no_markup"]
