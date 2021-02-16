""" Automatically update certain sections of README.md for osxphotos 
    Also updates osxphotos/phototemplate.md 
"""

# This is a pretty "dumb" script that searches the README.md for
# certain tags, expressed as HTML comments, and replaces text between
# those tags.  The following replacements are made:
# 1. the output of "osxphotos help export"
# 2. the template substitution table
# Running this script ensures the above sections of the README.md contain
# the most current information, updated directly from the code.

from click.testing import CliRunner

from osxphotos.cli import help
from osxphotos.phototemplate import (
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
    FILTER_VALUES,
)

TEMPLATE_HELP = "osxphotos/phototemplate.md"

USAGE_START = (
    "<!-- OSXPHOTOS-EXPORT-USAGE:START - Do not remove or modify this section -->"
)
USAGE_STOP = "<!-- OSXPHOTOS-EXPORT-USAGE:END -->"

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
    """ generate template substitution table for README.md """

    template_table = "| Substitution | Description |"
    template_table += "\n|--------------|-------------|"
    for subst, descr in [
        *TEMPLATE_SUBSTITUTIONS.items(),
        *TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items(),
    ]:
        template_table += f"\n|{subst}|{descr}|"
    return template_table


def generate_help_text(command):
    """ generate output of `osxphotos help command` """
    runner = CliRunner()

    # get current help text
    with runner.isolated_filesystem():
        result = runner.invoke(help, [command])
        help_txt = result.output

    # running the help command above doesn't output the full "Usage" line
    help_txt = help_txt.replace(f"Usage: {command}", f"Usage: osxphotos {command}")
    return help_txt


def replace_text(text, start_tag, stop_tag, replacement_text, prefix="", postfix=""):
    """ replace text between start/stop tags with new text

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
        raise ValueError(f"Unable to parse input: {e}")

    return begin + start_tag + prefix + replacement_text + postfix + stop_tag + end


def main():
    """ update README.md """
    # update phototemplate.md with info on filters
    print(f"Updating {TEMPLATE_HELP}")
    filter_help = "\n".join(f"- {f}: {descr}" for f, descr in FILTER_VALUES.items())
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

    with open(TEMPLATE_HELP, "w") as file:
        file.write(template_help)

    # update the help text for `osxphotos help export`
    print("Updating help for `osxphotos help export`")
    with open("README.md", "r") as file:
        readme = file.read()
    help_txt = generate_help_text("export")
    new_readme = replace_text(
        readme, USAGE_START, USAGE_STOP, help_txt, prefix="\n```\n", postfix="\n```\n"
    )

    # update the template substitution table
    print("Updating template substitution table")
    template_table = generate_template_table()
    new_readme = replace_text(
        new_readme,
        TEMPLATE_TABLE_START,
        TEMPLATE_TABLE_STOP,
        template_table,
        prefix="\n",
        postfix="\n",
    )

    # update the template system docs
    print("Updating template system help")
    with open(TEMPLATE_HELP) as fd:
        template_help = fd.read()

    new_readme = replace_text(
        new_readme,
        TEMPLATE_HELP_START,
        TEMPLATE_HELP_STOP,
        template_help,
        prefix="\n",
        postfix="\n",
    )

    print("Writing new README.md")
    with open("README.md", "w") as file:
        file.write(new_readme)


if __name__ == "__main__":
    main()
