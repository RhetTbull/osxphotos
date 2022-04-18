"""theme command for osxphotos for managing color themes"""

import pathlib

import click
from rich.console import Console
from rich_theme_manager import Theme

from .click_rich_echo import rich_click_echo
from .color_themes import get_default_theme, get_theme, get_theme_dir, get_theme_manager
from .help import get_help_msg


@click.command(name="theme")
@click.pass_obj
@click.pass_context
@click.option("--default", is_flag=True, help="Show default theme.")
@click.option("--list", "list_", is_flag=True, help="List all themes.")
@click.option(
    "--config",
    metavar="[THEME]",
    is_flag=False,
    flag_value="_DEFAULT_",
    default=None,
    help="Print configuration for THEME (or default theme if not specified).",
)
@click.option(
    "--preview",
    metavar="[THEME]",
    is_flag=False,
    flag_value="_DEFAULT_",
    default=None,
    help="Preview THEME (or default theme if not specified).",
)
@click.option(
    "--edit",
    metavar="[THEME]",
    is_flag=False,
    flag_value="_DEFAULT_",
    default=None,
    help="Edit THEME (or default theme if not specified).",
)
@click.option(
    "--clone",
    metavar="THEME NEW_THEME",
    nargs=2,
    type=str,
    help="Clone THEME to NEW_THEME.",
)
@click.option("--delete", metavar="THEME", help="Delete THEME.")
def theme(ctx, cli_obj, default, list_, config, preview, edit, clone, delete):
    """Manage osxphotos color themes."""

    subcommands = [default, list_, config, preview, edit, clone, delete]
    subcommand_names = (
        "--default, --list, --config, --preview, --edit, --clone, --delete"
    )
    if not any(subcommands):
        click.echo(
            f"Must specify exactly one of: {subcommand_names}\n",
            err=True,
        )
        rich_click_echo(get_help_msg(theme), err=True)
        return

    if sum(bool(cmd) for cmd in subcommands) != 1:
        # only a single subcommand may be specified
        raise click.ClickException(f"Must specify exactly one of: {subcommand_names}")

    theme_manager = get_theme_manager()
    console = Console(theme=get_default_theme())

    if default:
        default = get_default_theme()
        theme_manager.list_themes(theme_names=[default.name])
        return

    if list_:
        theme_manager.list_themes()
        return

    if config:
        if config == "_DEFAULT_":
            print(get_default_theme().config)
        else:
            print(get_theme(config).config)
        return

    if preview:
        theme_ = get_default_theme() if preview == "_DEFAULT_" else get_theme(preview)
        theme_manager.preview_theme(theme_)
        return

    if edit:
        theme_ = get_default_theme() if edit == "_DEFAULT_" else get_theme(edit)
        config_file = pathlib.Path(theme_.path)
        console.print(f"Opening [filepath]{config_file}[/] in $EDITOR")
        click.edit(filename=str(config_file))
        return

    if clone:
        src_theme = get_theme(clone[0])
        dest_path = get_theme_dir() / f"{clone[1]}.theme"
        if dest_path.exists():
            raise click.ClickException(
                f"Theme '{clone[1]}' already exists at {dest_path}"
            )
        dest_theme = Theme(
            name=clone[1],
            description=src_theme.description,
            inherit=src_theme.inherit,
            tags=src_theme.tags,
            styles={
                style_name: src_theme.styles[style_name]
                for style_name in src_theme.style_names
            },
        )
        theme_manager = get_theme_manager()
        theme_manager.add(dest_theme)
        theme_ = get_theme(dest_theme.name)
        console.print(
            f"Cloned theme '[filename]{clone[0]}[/]' to '[filename]{clone[1]}[/]' "
            f"at [filepath]{theme_.path}[/]"
        )
        return

    if delete:
        theme_ = get_theme(delete)
        click.confirm(f"Are you sure you want to delete theme {delete}?", abort=True)
        theme_manager.remove(theme_)
        console.print(f"Deleted theme [filepath]{theme_.path}[/]")
        return
