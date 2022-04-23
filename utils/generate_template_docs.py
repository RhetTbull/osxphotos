""" Automatically generate template system docs
"""

from click.testing import CliRunner

from osxphotos.cli import cli_main
from osxphotos.cli.help import strip_html_comments
from osxphotos.phototemplate import (
    FILTER_VALUES,
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
)

TEMPLATE_HELP = "osxphotos/phototemplate.md"
TUTORIAL_HELP = "osxphotos/tutorial.md"
TEMPLATE_HELP_DOC = "docsrc/source/template_help.md"

TEMPLATE_TABLE_START = (
    "<!-- OSXPHOTOS-TEMPLATE-TABLE:START - Do not remove or modify this section -->"
)
TEMPLATE_TABLE_STOP = "<!-- OSXPHOTOS-TEMPLATE-TABLE:END -->"

TEMPLATE_HELP_START = (
    "<!-- OSXPHOTOS-TEMPLATE-HELP:START - Do not remove or modify this section -->"
)
TEMPLATE_HELP_STOP = "<!-- OSXPHOTOS-TEMPLATE-HELP:END -->"

TEMPLATE_FILTER_TABLE_START = (
    "!-- OSXPHOTOS-FILTER-TABLE:START - Do not remove or modify this section -->"
)
TEMPLATE_FILTER_TABLE_STOP = "<!-- OSXPHOTOS-FILTER-TABLE:END -->"


def generate_template_table():
    """generate template substitution table for README.md"""

    template_table = "| Substitution | Description |"
    template_table += "\n|--------------|-------------|"
    for subst, descr in [
        *TEMPLATE_SUBSTITUTIONS.items(),
        *TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items(),
    ]:
        # replace '|' with '\|' to avoid markdown parsing issues (e.g. in {pipe} description)
        descr = descr.replace("'|'", "'\|'")
        template_table += f"\n|{subst}|{descr}|"
    return template_table


def replace_text(text, start_tag, stop_tag, replacement_text, prefix="", postfix=""):
    """replace text between start/stop tags with new text

    Args:
        text: str, original text
        start_tag: str, tag to find at beginning of replacement
        stop_tag: str, tag to find at end of replacement
        prefix: optional prefix that will go between start_tag and replacement_text
        postfix: optional postfix that will go between replacement_text and stop_tag
        replacement_text: str, new text to place between start_tag, stop_tag

    Returns:
        str
    """

    # sanity check to ensure tags are present
    if start_tag not in text:
        raise ValueError(f"start_tag {start_tag} not in text")
    if stop_tag not in text:
        raise ValueError(f"stop_tag {stop_tag} not in text")

    begin = end = ""
    try:
        begin = text.split(start_tag)[0]
        end = text.split(stop_tag)[1]
    except IndexError as e:
        # didn't find one of the delimiters
        raise ValueError(f"Unable to parse input: {e}") from e

    return begin + start_tag + prefix + replacement_text + postfix + stop_tag + end


def main():
    """generate docsrc/source/template_help.md"""

    # update phototemplate.md with info on filters
    filter_help = "\n".join(f"- `{f}`: {descr}" for f, descr in FILTER_VALUES.items())
    with open(TEMPLATE_HELP) as file:
        template_help = file.read()

    template_help = replace_text(
        template_help,
        TEMPLATE_FILTER_TABLE_START,
        TEMPLATE_FILTER_TABLE_STOP,
        filter_help,
        prefix="\n",
        postfix="\n",
    )

    # Add header
    template_help = "# osxphotos Template System\n\n" + template_help

    # Add the template substitution table
    print("Adding template substitution table")
    template_help += "\n\n## Template Substitutions\n\n"
    template_table = generate_template_table()
    template_help += template_table

    template_help = strip_html_comments(template_help)

    print(f"Writing new {TEMPLATE_HELP_DOC}")
    with open(TEMPLATE_HELP_DOC, "w") as file:
        file.write(template_help)


if __name__ == "__main__":
    main()
