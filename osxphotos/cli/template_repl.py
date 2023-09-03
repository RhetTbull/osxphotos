"""Render template for currently selected photo"""

from __future__ import annotations

import contextlib
import re
import readline
import sys
from textwrap import dedent
from typing import Literal

import click
from rich.columns import Columns
from rich.console import Console

import osxphotos
from osxphotos.phototemplate import (
    FIELD_NAMES,
    FILTER_VALUES,
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
    TEMPLATE_SUBSTITUTIONS_PATHLIB,
    get_template_field_table,
    get_template_help,
)
from osxphotos.platform import is_macos

from .cli_params import DB_OPTION
from .click_rich_echo import rich_echo_via_pager
from .common import get_data_dir

if is_macos:
    import photoscript

HISTORY_PATH = get_data_dir() / ".template_history"


# these two functions need to be defined here as they are used to declare constants below
def get_field_names() -> list[str]:
    """Return list of valid field names for template"""
    field_names = FIELD_NAMES.copy()
    for p in dir(osxphotos.PhotoInfo):
        if not p.startswith("_") and isinstance(
            getattr(osxphotos.PhotoInfo, p), property
        ):
            field_names.append(f"photo.{p}")
    return sorted(field_names)


def get_filter_fields() -> list[str]:
    """Return list of filter fields"""
    filter_fields = list(FILTER_VALUES.keys())
    filter_fields = [k.split("(")[0] for k in filter_fields]
    return sorted(filter_fields)


# valid commands for REPL
COMMANDS = [":help", ":vi", ":emacs", ":q", ":quit", ":exit", ":fields", ":filters"]

# Various constants used in REPL to lookup help, etc.
TEMPLATE_FIELDS = get_field_names()
ALL_FIELDS = TEMPLATE_FIELDS + get_filter_fields() + COMMANDS
ALL_TEMPLATE_SUBSTITUTIONS = (
    TEMPLATE_SUBSTITUTIONS
    | TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
    | TEMPLATE_SUBSTITUTIONS_PATHLIB
)
TEMPLATE_LOOKUP = {
    k.lower().replace("{", "").replace("}", ""): v.lower()
    for k, v in ALL_TEMPLATE_SUBSTITUTIONS.items()
}
HELP_DICT = (
    TEMPLATE_SUBSTITUTIONS
    | TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
    | TEMPLATE_SUBSTITUTIONS_PATHLIB
    | FILTER_VALUES
)


@click.command(name="template")
@click.option(
    "--template",
    "-T",
    metavar="TEMPLATE",
    multiple=True,
    help="Template string to render for selected photo. "
    "If --template/-T is used, the template will be rendered and printed "
    "and the REPL will not be started. "
    "Multiple templates may be specified by repeating --template/-T.",
)
@click.option(
    "--uuid",
    metavar="UUID",
    default=None,
    help="Use photo with uuid UUID to render template inplace of selected photo.",
)
@DB_OPTION
@click.option("--vi", "mode", flag_value="vi", help="Use vi keybindings.")
@click.option("--emacs", "mode", flag_value="emacs", help="Use emacs keybindings.")
def template_repl(
    mode: str | None, template: tuple[str, ...], uuid: str | None, db: str | None
):
    """Interactively render templates for selected photo.

    Launches a REPL (Read-Eval-Print-Loop) to interactively render a template for the selected photo.

    Select a photo in Photos then run `osxphotos template` to start the REPL.
    """
    configure_readline(mode)
    if not template:
        print("Loading Photos library...")
    photosdb = osxphotos.PhotosDB(dbfile=db)
    if template:
        sys.exit(render_and_print_template(photosdb, template, uuid))
    else:
        run_repl_loop(photosdb, uuid)


def configure_readline(mode: str | None):
    """Configure readline and load history"""
    readline.set_auto_history(True)
    with contextlib.suppress(FileNotFoundError):
        readline.read_history_file(HISTORY_PATH)
    readline.set_completer(mtl_completion)
    set_editor_mode(mode=mode)


def run_repl_loop(photosdb: osxphotos.PhotosDB, uuid: str | None):
    """Run REPL loop to evaluate template

    Args:
        photosdb: osxphotos.PhotosDB instance
        uuid: UUID of photo to use in place of selected photo or None to use selected photo
    """
    try:
        # Set up the prompt
        prompt = ">>> "
        print_intro()
        while True:
            try:
                line = input(prompt)
            except (KeyboardInterrupt, EOFError):
                print()  # New line after Ctrl+C or Ctrl+D
                break

            line = line.strip()

            # handle commands before templates
            if line.startswith(":") and handle_command(line):
                continue

            photo = get_photo(photosdb, uuid)
            if not photo:
                continue
            try:
                rendered, unmatched = photo.render_template(line)
            except Exception as e:
                print(e)
                continue
            if unmatched:
                handle_unmatched(unmatched)
            print("\n".join(rendered))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print()
        cleanup_and_exit()


def handle_command(command: str) -> bool:
    """Handle possible commands. Return True if command handled, otherwise False"""
    # strip leading ":" and convert to lowercase
    command = command.lower()[1:]
    if command.startswith("help"):
        print_help(command)
        return True

    if command == "fields":
        # print all fields
        print_fields()
        return True

    if command == "filters":
        # print all filters
        print_filters()
        return True

    if command in {"emacs", "vi"}:
        # set editor mode
        set_editor_mode(command)
        print(f"{command.title()} mode enabled")
        return True

    if command in {"q", "quit", "exit"}:
        print()
        return cleanup_and_exit()

    print(f"Unknown command :{command}")
    return False


def print_help(help_command: str):
    """Print help"""
    try:
        search_text = help_command.split(" ")[1]
    except IndexError:
        search_text = None

    if not search_text:
        print_intro()
        return

    search_text = search_text.lower().strip()

    if search_text == "template":
        print_template_help()
        return

    if help_text := [
        f"{k}: {v}"
        for k, v in HELP_DICT.items()
        if re.search(search_text, k, re.IGNORECASE)
        or re.search(search_text, v, re.IGNORECASE)
    ]:
        print("\n".join(help_text))
    else:
        print(f"No help found for {search_text}")


def print_template_help():
    """ "Print help for template system"""
    help_text = get_template_help()
    help_text = (
        "# Template System Help\n\n"
        + "**Press Space to page, arrow keys to scroll, or q to exit help.**\n\n"
        + help_text
    )
    help_text += (
        "\n\n" + "## Template Substitutions\n\n" + get_template_field_table() + "\n"
    )
    rich_echo_via_pager(help_text, markdown=True)


def get_photo(
    photosdb: osxphotos.PhotosDB, uuid: str | None
) -> osxphotos.PhotoInfo | None:
    """Return selected photo or None

    Args:
        photosdb: osxphotos.PhotosDB instance
        uuid: UUID of photo to use in place of selected photo or None to use selected photo
    """
    if not uuid:
        # no uuid, get uuid of selected photo
        if not is_macos:
            print("Set photo uuid with --uuid option")
            return None
        try:
            selected = photoscript.PhotosLibrary().selection
            if not selected:
                print("No photo selected")
                return None
        except Exception as e:
            print(f"Error getting photo: {e}")
            return None
        uuid = selected[0].uuid
    photo = photosdb.get_photo(uuid)
    if not photo:
        print(f"No photo found with UUID {uuid}")
        return None
    return photo


def set_editor_mode(mode: Literal["emacs", "vi", None]):
    """Config editor mode and tab completion for readline"""

    if "libedit" in readline.__doc__:
        # macOS readline uses libedit
        if mode == "vi":
            readline.parse_and_bind("bind -v")
        else:
            readline.parse_and_bind("bind -e")

        # configure tab completion
        readline.parse_and_bind("bind '\t' rl_complete")
        return

    if mode:
        readline.parse_and_bind(f"set editing-mode {mode}")
    else:
        readline.parse_and_bind("set editing-mode emacs")

    # configure tab completion
    readline.parse_and_bind("tab: complete")


def mtl_completion(text: str, state: int) -> str | None:
    """Completion function for readline"""
    options = [field for field in ALL_FIELDS if field.startswith(text)]
    return options[state] if state < len(options) else None


def suggest_template_fields(unmatched: list[str]) -> list[str]:
    """For fields that are not matched, suggest possible fields"""
    # this is a very simple suggestion algorithm that just looks for
    # fields that start with the unmatched text or contain the unmatched text
    suggestions = []
    for un in unmatched:
        un = un.lower()
        for field, description in TEMPLATE_LOOKUP.items():
            if field.startswith(un):
                suggestions.append(field)
            elif un in field or un in description:
                suggestions.append(field)
            elif field.startswith(un[0]):
                # if first letter matches, suggest
                suggestions.append(field)
    return suggestions


def render_and_print_template(
    photosdb: osxphotos.PhotosDB, template: tuple[str, ...], uuid: str | None
) -> int:
    """Render and print template(s)

    Args:
        photosdb: osxphotos.PhotosDB instance
        template: tuple of template strings to render
        uuid: UUID of photo to use in place of selected photo or None to use selected photo

    Returns:
        0 if no errors, 1 if errors
    """
    photo = get_photo(photosdb, uuid)
    error = False
    if not photo:
        sys.exit(1)
    for t in template:
        try:
            rendered, unmatched = photo.render_template(t)
        except Exception as e:
            print(e)
            error = True
            continue
        print("\n".join(rendered))
        if unmatched:
            error = True
            handle_unmatched(unmatched)
    return 1 if error else 0


def handle_unmatched(unmatched: list[str]):
    """Print unmatched template fields and suggest possible matches (prints to stderr)"""
    print(
        ("Unknown template field: " + ", ".join([f"'{field}'" for field in unmatched])),
        file=sys.stderr,
    )
    if suggestions := suggest_template_fields(unmatched):
        print("Did you mean one of these?", file=sys.stderr)
        print(" ".join(suggestions), file=sys.stderr)


def print_intro():
    """Print introductory text for REPL"""

    print(
        dedent(
            """
        Enter a template to render then press Return.
        Press Tab to autocomplete.  Press Tab twice to see list of available fields and filters.

        The following commands are available. All commands start with a colon (:).

        :help <KEYWORD>     Print help for <KEYWORD> (e.g. :help description to get help on {descr} template field)
        :help template      Print help for template system
        :fields             Print list of all template fields
        :filters            Print list of all template filters
        :emacs              Set Emacs keybindings
        :vi                 Set Vi keybindings
        :quit, :q, :exit    Exit the REPL (Ctrl+C or Ctrl+D will also exit)
        """
        )
    )


def print_fields():
    """Print all field names"""
    print_columns(TEMPLATE_FIELDS)


def print_filters():
    """Print all filter names"""
    print_columns(FILTER_VALUES.keys())


def cleanup_and_exit():
    """Perform any needed cleanup and exit"""
    readline.write_history_file(HISTORY_PATH)
    sys.exit(0)


def print_columns(strings: list[str]):
    """Print a list of strings in columns"""
    columns = Columns(strings, equal=True, expand=True)
    Console(highlight=False).print(columns)


if __name__ == "__main__":
    template_repl()
