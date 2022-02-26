"""Help text helper class for osxphotos CLI """

import io
import re

import click
import osxmetadata
from rich.console import Console
from rich.markdown import Markdown

from osxphotos._constants import (
    EXTENDED_ATTRIBUTE_NAMES,
    EXTENDED_ATTRIBUTE_NAMES_QUOTED,
    OSXPHOTOS_EXPORT_DB,
    POST_COMMAND_CATEGORIES,
)
from osxphotos.phototemplate import (
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
    TEMPLATE_SUBSTITUTIONS_PATHLIB,
    get_template_help,
)

__all__ = [
    "ExportCommand",
    "template_help",
    "rich_text",
    "strip_md_header_and_links",
    "strip_md_links",
    "strip_html_comments",
    "help",
    "get_help_msg",
]


def get_help_msg(command):
    """get help message for a Click command"""
    with click.Context(command) as ctx:
        return command.get_help(ctx)


@click.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx, topic, **kw):
    """Print help; for help on commands: help <command>."""
    if topic is None:
        click.echo(ctx.parent.get_help())
        return
    elif topic in ctx.obj.group.commands:
        ctx.info_name = topic
        click.echo_via_pager(ctx.obj.group.commands[topic].get_help(ctx))
    else:
        click.echo(f"Invalid command: {topic}", err=True)
        click.echo(ctx.parent.get_help())


# TODO: The following help text could probably be done as mako template
class ExportCommand(click.Command):
    """Custom click.Command that overrides get_help() to show additional help info for export"""

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = click.HelpFormatter()
        # passed to click.HelpFormatter.write_dl for formatting

        formatter.write("\n\n")
        formatter.write(rich_text("[bold]** Export **[/bold]", width=formatter.width))
        formatter.write("\n")
        formatter.write_text(
            "When exporting photos, osxphotos creates a database in the top-level "
            + f"export folder called '{OSXPHOTOS_EXPORT_DB}'.  This database preserves state information "
            + "used for determining which files need to be updated when run with --update.  It is recommended "
            + "that if you later move the export folder tree you also move the database file."
        )
        formatter.write("\n")
        formatter.write_text(
            "The --update option will only copy new or updated files from the library "
            + "to the export folder.  If a file is changed in the export folder (for example, you edited the "
            + "exported image), osxphotos will detect this as a difference and re-export the original image "
            + "from the library thus overwriting the changes.  If using --update, the exported library "
            + "should be treated as a backup, not a working copy where you intend to make changes. "
            + "If you do edit or process the exported files and do not want them to be overwritten with"
            + "subsequent --update, use --ignore-signature which will match filename but not file signature when "
            + "exporting."
        )
        formatter.write("\n")
        formatter.write_text(
            "Note: The number of files reported for export and the number actually exported "
            + "may differ due to live photos, associated raw images, and edited photos which are reported "
            + "in the total photos exported."
        )
        formatter.write("\n")
        formatter.write_text(
            "Implementation note: To determine which files need to be updated, "
            + f"osxphotos stores file signature information in the '{OSXPHOTOS_EXPORT_DB}' database. "
            + "The signature includes size, modification time, and filename.  In order to minimize "
            + "run time, --update does not do a full comparison (diff) of the files nor does it compare "
            + "hashes of the files.  In normal usage, this is sufficient for updating the library. "
            + "You can always run export without the --update option to re-export the entire library thus "
            + f"rebuilding the '{OSXPHOTOS_EXPORT_DB}' database."
        )
        formatter.write("\n\n")
        formatter.write(
            rich_text("[bold]** Extended Attributes **[/bold]", width=formatter.width)
        )
        formatter.write("\n")
        formatter.write_text(
            """
Some options (currently '--finder-tag-template', '--finder-tag-keywords', '-xattr-template') write
additional metadata to extended attributes in the file. These options will only work
if the destination filesystem supports extended attributes (most do).
For example, --finder-tag-keyword writes all keywords (including any specified by '--keyword-template'
or other options) to Finder tags that are searchable in Spotlight using the syntax: 'tag:tagname'.
For example, if you have images with keyword "Travel" then using '--finder-tag-keywords' you could quickly
find those images in the Finder by typing 'tag:Travel' in the Spotlight search bar.
Finder tags are written to the 'com.apple.metadata:_kMDItemUserTags' extended attribute.
Unlike EXIF metadata, extended attributes do not modify the actual file. Most cloud storage services
do not synch extended attributes. Dropbox does sync them and any changes to a file's extended attributes
will cause Dropbox to re-sync the files.

The following attributes may be used with '--xattr-template':

            """
        )
        formatter.write_dl(
            [
                (
                    attr,
                    f"{osxmetadata.ATTRIBUTES[attr].help} ({osxmetadata.ATTRIBUTES[attr].constant})",
                )
                for attr in EXTENDED_ATTRIBUTE_NAMES
            ]
        )
        formatter.write("\n")
        formatter.write_text(
            "For additional information on extended attributes see: https://developer.apple.com/documentation/coreservices/file_metadata/mditem/common_metadata_attribute_keys"
        )
        formatter.write("\n\n")
        formatter.write(
            rich_text("[bold]** Templating System **[/bold]", width=formatter.width)
        )
        formatter.write("\n")
        formatter.write(template_help(width=formatter.width))
        formatter.write("\n")
        formatter.write_text(
            "With the --directory and --filename options you may specify a template for the "
            + "export directory or filename, respectively. "
            + "The directory will be appended to the export path specified "
            + "in the export DEST argument to export.  For example, if template is "
            + "'{created.year}/{created.month}', and export destination DEST is "
            + "'/Users/maria/Pictures/export', "
            + "the actual export directory for a photo would be '/Users/maria/Pictures/export/2020/March' "
            + "if the photo was created in March 2020. "
        )
        formatter.write("\n")
        formatter.write_text(
            "The templating system may also be used with the --keyword-template option "
            + "to set keywords on export (with --exiftool or --sidecar), "
            + "for example, to set a new keyword in format 'folder/subfolder/album' to "
            + 'preserve the folder/album structure, you can use --keyword-template "{folder_album}" '
            + "or in the 'folder>subfolder>album' format used in Lightroom Classic, --keyword-template \"{folder_album(>)}\"."
        )
        formatter.write("\n")
        formatter.write_text(
            "In the template, valid template substitutions will be replaced by "
            + "the corresponding value from the table below.  Invalid substitutions will result in a "
            + "an error and the script will abort."
        )
        formatter.write("\n")
        formatter.write(
            rich_text(
                "[bold]** Template Substitutions **[/bold]", width=formatter.width
            )
        )
        formatter.write("\n")
        templ_tuples = [("Substitution", "Description")]
        templ_tuples.extend((k, v) for k, v in TEMPLATE_SUBSTITUTIONS.items())
        formatter.write_dl(templ_tuples)

        formatter.write("\n")
        formatter.write_text(
            "The following substitutions may result in multiple values. Thus "
            + "if specified for --directory these could result in multiple copies of a photo being "
            + "being exported, one to each directory.  For example: "
            + "--directory '{created.year}/{album}' could result in the same photo being exported "
            + "to each of the following directories if the photos were created in 2019 "
            + "and were in albums 'Vacation' and 'Family': "
            + "2019/Vacation, 2019/Family"
        )
        formatter.write("\n")
        templ_tuples = [("Substitution", "Description")]
        templ_tuples.extend(
            (k, v) for k, v in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items()
        )

        formatter.write_dl(templ_tuples)

        formatter.write("\n")
        formatter.write_text(
            "The following substitutions are file or directory paths. "
            + "You can access various parts of the path using the following modifiers:"
        )
        formatter.write("\n")
        formatter.write("{path.parent}: the parent directory\n")
        formatter.write("{path.name}: the name of the file or final sub-directory\n")
        formatter.write("{path.stem}: the name of the file without the extension\n")
        formatter.write(
            "{path.suffix}: the suffix of the file including the leading '.'\n"
        )
        formatter.write("\n")
        formatter.write(
            "For example, if the field {export_dir} is '/Shared/Backup/Photos':\n"
        )
        formatter.write("{export_dir.parent} is '/Shared/Backup'\n")
        formatter.write("\n")
        formatter.write(
            "If the field {filepath} is '/Shared/Backup/Photos/IMG_1234.JPG':\n"
        )
        formatter.write("{filepath.parent} is '/Shared/Backup/Photos'\n")
        formatter.write("{filepath.name} is 'IMG_1234.JPG'\n")
        formatter.write("{filepath.stem} is 'IMG_1234'\n")
        formatter.write("{filepath.suffix} is '.JPG'\n")
        formatter.write("\n")
        templ_tuples = [("Substitution", "Description")]
        templ_tuples.extend((k, v) for k, v in TEMPLATE_SUBSTITUTIONS_PATHLIB.items())

        formatter.write_dl(templ_tuples)

        formatter.write("\n\n")
        formatter.write(
            rich_text("[bold]** Post Command **[/bold]", width=formatter.width)
        )
        formatter.write_text(
            "You can run commands on the exported photos for post-processing "
            + "using the '--post-command' option. '--post-command' is passed a CATEGORY and a COMMAND. "
            + "COMMAND is an osxphotos template string which will be rendered and passed to the shell "
            + "for execution. CATEGORY is the category of file to pass to COMMAND. "
            + "The following categories are available: "
        )
        formatter.write("\n")
        templ_tuples = [("Category", "Description")]
        templ_tuples.extend((k, v) for k, v in POST_COMMAND_CATEGORIES.items())
        formatter.write_dl(templ_tuples)
        formatter.write("\n")
        formatter.write_text(
            "In addition to all normal template fields, the template fields "
            + "'{filepath}' and '{export_dir}' will be available to your command template. "
            + "Both of these are path-type templates which means their various parts can be accessed using "
            + "the available properties, e.g. '{filepath.name}' provides just the file name without path "
            + "and '{filepath.suffix}' is the file extension (suffix) of the file. "
            + "When using paths in your command template, it is important to properly quote the paths "
            + "as they will be passed to the shell and path names may contain spaces. "
            + "Both the '{shell_quote}' template and the '|shell_quote' template filter are available for "
            + "this purpose.  For example, the following command outputs the full path of newly exported files to file 'new.txt': "
        )
        formatter.write("\n")
        formatter.write(
            '--post-command new "echo {filepath|shell_quote} >> {shell_quote,{export_dir}/exported.txt}"'
        )
        formatter.write("\n\n")
        formatter.write_text(
            "In the above command, the 'shell_quote' filter is used to ensure '{filepath}' is properly quoted "
            + "and the '{shell_quote}' template ensures the constructed path of '{exported_dir}/exported.txt' is properly quoted. "
            "If '{filepath}' is 'IMG 1234.jpeg' and '{export_dir}' is '/Volumes/Photo Export', the command "
            "thus renders to: "
        )
        formatter.write("\n")
        formatter.write("echo 'IMG 1234.jpeg' >> '/Volumes/Photo Export/exported.txt'")
        formatter.write("\n\n")
        formatter.write_text(
            "It is highly recommended that you run osxphotos with '--dry-run --verbose' "
            + "first to ensure your commands are as expected. This will not actually run the commands but will "
            + "print out the exact command string which would be executed."
        )
        formatter.write("\n\n")
        formatter.write(
            rich_text("[bold]** Post Function **[/bold]", width=formatter.width)
        )
        formatter.write_text(
            "You can run your own python functions on the exported photos for post-processing "
            + "using the '--post-function' option. '--post-function' is passed the name a python file "
            + "and the name of the function in the file to call using format 'filename.py::function_name'. "
            + "See the example function at https://github.com/RhetTbull/osxphotos/blob/master/examples/post_function.py "
            + "You may specify multiple functions to run by repeating the --post-function option. "
            + "All post functions will be called immediately after export of each photo and immediately before any --post-command commands. "
            + "Post functions will not be called if the --dry-run flag is set."
        )
        formatter.write("\n")

        help_text += formatter.getvalue()
        return help_text


def template_help(width=78):
    """Return formatted string for template system"""
    sio = io.StringIO()
    console = Console(file=sio, force_terminal=True, width=width)
    template_help_md = strip_md_header_and_links(get_template_help())
    console.print(Markdown(template_help_md))
    help_str = sio.getvalue()
    sio.close()
    return help_str


def rich_text(text, width=78):
    """Return rich formatted text"""
    sio = io.StringIO()
    console = Console(file=sio, force_terminal=True, width=width)
    console.print(text)
    rich_text = sio.getvalue()
    sio.close()
    return rich_text


def strip_md_header_and_links(md):
    """strip markdown headers and links from markdown text md

    Args:
        md: str, markdown text

    Returns:
        str with markdown headers and links removed

    Note: This uses a very basic regex that likely fails on all sorts of edge cases
    but works for the links in the osxphotos docs
    """
    links = r"(?:[*#])|\[(.*?)\]\(.+?\)"

    def subfn(match):
        return match.group(1)

    return re.sub(links, subfn, md)


def strip_md_links(md):
    """strip markdown links from markdown text md

    Args:
        md: str, markdown text

    Returns:
        str with markdown links removed

    Note: This uses a very basic regex that likely fails on all sorts of edge cases
    but works for the links in the osxphotos docs
    """
    links = r"\[(.*?)\]\(.+?\)"

    def subfn(match):
        return match.group(1)

    return re.sub(links, subfn, md)


def strip_html_comments(text):
    """Strip html comments from text (which doesn't need to be valid HTML)"""
    return re.sub(r"<!--(.|\s|\n)*?-->", "", text)
