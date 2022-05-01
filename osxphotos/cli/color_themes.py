"""Support for colorized output for osxphotos cli using rich"""

import pathlib
from typing import List, Optional

import click
from rich.style import Style
from rich_theme_manager import Theme, ThemeManager

from .common import get_config_dir, noop
from .darkmode import is_dark_mode

DEFAULT_THEME_NAME = "default"

__all__ = [
    "get_default_theme",
    "get_theme",
    "get_theme_dir",
    "get_theme_manager",
    DEFAULT_THEME_NAME,
]


THEME_STYLES = [
    "bar.back",
    "bar.complete",
    "bar.finished",
    "bar.pulse",
    "change",
    "color",
    "count",
    "error",
    "filename",
    "filepath",
    "highlight",
    "no_change",
    "num",
    "progress.elapsed",
    "progress.percentage",
    "progress.remaining",
    "time",
    "tz",
    "uuid",
    "warning",
]

COLOR_THEMES = {
    "dark": Theme(
        name="dark",
        description="Dark mode theme",
        tags=["dark"],
        styles={
            # color pallette from https://github.com/dracula/dracula-theme
            "bar.back": Style(color="rgb(68,71,90)"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(80,250,123)"),
            "bar.pulse": Style(color="rgb(98,114,164)"),
            "change": Style(color="bright_red", bold=True),
            "color": Style(color="rgb(248,248,242)"),
            "count": Style(color="rgb(139,233,253)"),
            "error": Style(color="rgb(255,85,85)", bold=True),
            "filename": Style(color="rgb(189,147,249)", bold=True),
            "filepath": Style(color="rgb(80,250,123)", bold=True),
            "highlight": Style(color="#000000", bgcolor="#d73a49", bold=True),
            "no_change": Style(color="bright_green", bold=True),
            "num": Style(color="rgb(139,233,253)", bold=True),
            "progress.elapsed": Style(color="rgb(139,233,253)"),
            "progress.percentage": Style(color="rgb(255,121,198)"),
            "progress.remaining": Style(color="rgb(139,233,253)"),
            "time": Style(color="rgb(139,233,253)", bold=True),
            "tz": Style(color="bright_cyan", bold=True),
            "uuid": Style(color="rgb(255,184,108)"),
            "warning": Style(color="rgb(241,250,140)", bold=True),
            # "headers": Style(color="rgb(165,194,97)"),
            # "options": Style(color="rgb(255,198,109)"),
            # "metavar": Style(color="rgb(12,125,157)"),
        },
    ),
    "light": Theme(
        name="light",
        description="Light mode theme",
        styles={
            "bar.back": Style(color="grey23"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(114,156,31)"),
            "bar.pulse": Style(color="rgb(249,38,114)"),
            "change": "bold dark_red",
            "color": Style(color="#000000"),
            "count": Style(color="#005cc5", bold=True),
            "error": Style(color="#b31d28", bold=True, underline=True, italic=True),
            "filename": Style(color="#6f42c1", bold=True),
            "filepath": Style(color="#22863a", bold=True),
            "highlight": Style(color="#ffffff", bgcolor="#d73a49", bold=True),
            "no_change": "bold dark_green",
            "num": Style(color="#005cc5", bold=True),
            "progress.elapsed": Style(color="#032f62", bold=True),
            "progress.percentage": Style(color="#6f42c1", bold=True),
            "progress.remaining": Style(color="#032f62", bold=True),
            "time": Style(color="#032f62", bold=True),
            "tz": "bold cyan",
            "uuid": Style(color="#d73a49", bold=True),
            "warning": Style(color="#e36209", bold=True, underline=True, italic=True),
            # "headers": Style(color="rgb(254,212,66)"),
            # "options": Style(color="rgb(227,98,9)"),
            # "metavar": Style(color="rgb(111,66,193)"),
        },
    ),
    "mono": Theme(
        name="mono",
        description="Monochromatic theme",
        tags=["mono", "colorblind"],
        styles={
            "bar.back": "",
            "bar.complete": "reverse",
            "bar.finished": "bold",
            "bar.pulse": "bold",
            "change": "reverse",
            "count": "bold",
            "error": "reverse italic",
            "filename": "bold",
            "filepath": "bold underline",
            "highlight": "reverse italic",
            "no_change": "",
            "num": "bold",
            "progress.elapsed": "",
            "progress.percentage": "bold",
            "progress.remaining": "bold",
            "time": "bold",
            "tz": "",
            "uuid": "bold",
            "warning": "bold italic",
            # "headers": "bold",
            # "options": "bold",
            # "metavar": "bold",
        },
    ),
    "plain": Theme(
        name="plain",
        description="Plain theme with no colors",
        tags=["colorblind"],
        styles={
            "bar.back": "",
            "bar.complete": "",
            "bar.finished": "",
            "bar.pulse": "",
            "change": "",
            "color": "",
            "count": "",
            "error": "",
            "filename": "",
            "filepath": "",
            "highlight": "",
            "no_change": "",
            "num": "",
            "progress.elapsed": "",
            "progress.percentage": "",
            "progress.remaining": "",
            "time": "",
            "tz": "",
            "uuid": "",
            "warning": "",
            # "headers": "",
            # "options": "",
            # "metavar": "",
        },
    ),
}


def get_theme_dir() -> pathlib.Path:
    """Return the theme config dir, creating it if necessary"""
    theme_dir = get_config_dir() / "themes"
    if not theme_dir.exists():
        theme_dir.mkdir()
    return theme_dir


def get_theme_manager() -> ThemeManager:
    """Return theme manager instance"""
    return ThemeManager(
        theme_dir=str(get_theme_dir()), themes=COLOR_THEMES.values(), update=True
    )


def get_theme(
    theme_name: Optional[str] = None,
):
    """Get theme by name, or default theme if no name is provided"""

    if theme_name is None:
        return get_default_theme()

    theme_manager = get_theme_manager()
    try:
        return theme_manager.get(theme_name)
    except ValueError as e:
        raise click.ClickException(
            f"Theme '{theme_name}' not found. "
            f"Available themes: {', '.join(t.name for t in theme_manager.themes)}"
        ) from e


def get_default_theme():
    """Get the default color theme"""
    theme_manager = get_theme_manager()
    try:
        return theme_manager.get(DEFAULT_THEME_NAME)
    except ValueError:
        return (
            theme_manager.get("dark") if is_dark_mode() else theme_manager.get("light")
        )
