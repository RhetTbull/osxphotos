"""theme command for osxphotos for managing color themes"""

import pathlib
from typing import List, Optional

import click
from rich import print as rprint
from rich_theme_manager import Theme, ThemeManager

from .._constants import APP_NAME
from .color_themes import (
    COLOR_THEMES,
    THEME_STYLES,
    get_default_theme,
    get_default_theme_name,
    get_theme,
)
from .common import THEME_OPTION

SAMPLE_TEXT = "The quick brown fox..."


def get_theme_dir() -> str:
    """Return the theme config dir, creating it if necessary"""
    theme_dir = pathlib.Path(click.get_app_dir(APP_NAME, force_posix=True)) / "themes"
    theme_dir.mkdir(parents=True, exist_ok=True)
    return str(theme_dir)


THEME_DIR = get_theme_dir()
DEFAULT_THEME = "default"


@click.command(name="theme")
@click.pass_obj
@click.pass_context
@THEME_OPTION
@click.argument(
    "subcommand",
    required=False,
    type=click.Choice(["list", "edit", "config", "preview", "delete", "default"]),
)
def theme(ctx, cli_obj, theme, subcommand):
    """Manage osxphotos color themes.

    One of the following subcommands must be specified:

    list: list available themes

    config: print config file for theme to stdout

    preview: preview theme

    delete: delete theme

    default: set default theme
    """

    theme_manager = ThemeManager(theme_dir=THEME_DIR, themes=COLOR_THEMES.values())

    if subcommand == "default":
        default = get_default_theme(theme_manager)
        theme_manager.list_themes(theme_names=[default.name])
        return

    if subcommand == "list":
        theme_manager.list_themes()
        return

    if subcommand == "config":
        if theme:
            print(theme_manager.get(theme).config)
        else:
            print(get_default_theme(theme_manager).config)
        return

    if subcommand == "preview":
        theme_ = get_theme(theme)
        theme_manager.preview_theme(theme_, sample_text=SAMPLE_TEXT)
        return

    if subcommand == "edit":
        if not config_file.exists():
            rprint(f"No config file found for theme {theme}, creating '{config_file}'.")
            config_file.write_text(get_theme(theme).config, THEME_STYLES)
        rprint(f"Opening {config_file} in $EDITOR")
        click.edit(filename=str(config_file))

    if subcommand == "delete":
        raise NotImplementedError("delete")


def get_default_theme(theme_manager: ThemeManager) -> Theme:
    """Return the default theme"""
    try:
        return theme_manager.get("default")
    except ValueError:
        theme_name = get_default_theme_name()
        return theme_manager.get(theme_name)
