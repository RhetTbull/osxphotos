"""Support for colorized output for osxphotos cli using rich"""

import pathlib
from typing import List, Optional

import click
from rich.style import Style
from rich_theme_manager import Theme, ThemeManager

from .._constants import APP_NAME
from .common import noop
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
    "color",
    "count",
    "error",
    "filename",
    "filepath",
    "highlight",
    "num",
    "time",
    "uuid",
    "warning",
    "bar.back",
    "bar.complete",
    "bar.finished",
    "bar.pulse",
    "progress.elapsed",
    "progress.percentage",
    "progress.remaining",
]

COLOR_THEMES = {
    "dark": Theme(
        name="dark",
        description="Dark mode theme",
        tags=["dark"],
        styles={
            # color pallette from https://github.com/dracula/dracula-theme
            "color": Style(color="rgb(248,248,242)"),
            "count": Style(color="rgb(139,233,253)"),
            "error": Style(color="rgb(255,85,85)", bold=True),
            "filename": Style(color="rgb(189,147,249)", bold=True),
            "filepath": Style(color="rgb(80,250,123)", bold=True),
            "highlight": Style(color="#000000", bgcolor="#d73a49", bold=True),
            "num": Style(color="rgb(139,233,253)", bold=True),
            "time": Style(color="rgb(139,233,253)", bold=True),
            "uuid": Style(color="rgb(255,184,108)"),
            "warning": Style(color="rgb(241,250,140)", bold=True),
            "bar.back": Style(color="rgb(68,71,90)"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(80,250,123)"),
            "bar.pulse": Style(color="rgb(98,114,164)"),
            "progress.elapsed": Style(color="rgb(139,233,253)"),
            "progress.percentage": Style(color="rgb(255,121,198)"),
            "progress.remaining": Style(color="rgb(139,233,253)"),
        },
    ),
    "light": Theme(
        name="light",
        description="Light mode theme",
        styles={
            "color": Style(color="#000000"),
            "count": Style(color="#005cc5", bold=True),
            "error": Style(color="#b31d28", bold=True, underline=True, italic=True),
            "filename": Style(color="#6f42c1", bold=True),
            "filepath": Style(color="#22863a", bold=True),
            "highlight": Style(color="#ffffff", bgcolor="#d73a49", bold=True),
            "num": Style(color="#005cc5", bold=True),
            "time": Style(color="#032f62", bold=True),
            "uuid": Style(color="#d73a49", bold=True),
            "warning": Style(color="#e36209", bold=True, underline=True, italic=True),
            "bar.back": Style(color="grey23"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(114,156,31)"),
            "bar.pulse": Style(color="rgb(249,38,114)"),
            "progress.elapsed": Style(color="#032f62", bold=True),
            "progress.percentage": Style(color="#6f42c1", bold=True),
            "progress.remaining": Style(color="#032f62", bold=True),
        },
    ),
    "mono": Theme(
        name="mono",
        description="Monochromatic theme",
        tags=["mono", "colorblind"],
        styles={
            "count": "bold",
            "error": "reverse italic",
            "filename": "bold",
            "filepath": "bold underline",
            "highlight": "reverse italic",
            "num": "bold",
            "time": "bold",
            "uuid": "bold",
            "warning": "bold italic",
            "bar.back": "",
            "bar.complete": "reverse",
            "bar.finished": "bold",
            "bar.pulse": "bold",
            "progress.elapsed": "",
            "progress.percentage": "bold",
            "progress.remaining": "bold",
        },
    ),
    "plain": Theme(
        name="plain",
        description="Plain theme with no colors",
        tags=["colorblind"],
        styles={
            "color": "",
            "count": "",
            "error": "",
            "filename": "",
            "filepath": "",
            "highlight": "",
            "num": "",
            "time": "",
            "uuid": "",
            "warning": "",
            "bar.back": "",
            "bar.complete": "",
            "bar.finished": "",
            "bar.pulse": "",
            "progress.elapsed": "",
            "progress.percentage": "",
            "progress.remaining": "",
        },
    ),
}


def get_theme_dir() -> str:
    """Return the theme config dir, creating it if necessary"""
    theme_dir = pathlib.Path(click.get_app_dir(APP_NAME, force_posix=True)) / "themes"
    theme_dir.mkdir(parents=True, exist_ok=True)
    return str(theme_dir)


def get_theme_manager() -> ThemeManager:
    """Return theme manager instance"""
    return ThemeManager(theme_dir=get_theme_dir(), themes=COLOR_THEMES.values())


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
