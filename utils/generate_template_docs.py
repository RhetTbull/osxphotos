""" Automatically generate template system docs
"""

from click.testing import CliRunner

from osxphotos.cli import cli_main
from osxphotos.cli.help import strip_html_comments
from osxphotos.phototemplate import get_template_field_table, get_template_help

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

    template_help = get_template_help()
    # Add header
    template_help = "# OSXPhotos Template System\n\n" + template_help

    # Add the template substitution table
    print("Adding template substitution table")
    template_help += "\n\n## Template Substitutions\n\n"
    template_table = get_template_field_table()
    template_help += template_table

    template_help = strip_html_comments(template_help)

    print(f"Writing new {TEMPLATE_HELP_DOC}")
    with open(TEMPLATE_HELP_DOC, "w") as file:
        file.write(template_help)


if __name__ == "__main__":
    main()
