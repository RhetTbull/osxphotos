"""Help text helper class for osxphotos CLI """

import click
import osxmetadata

from ._constants import (
    EXTENDED_ATTRIBUTE_NAMES,
    EXTENDED_ATTRIBUTE_NAMES_QUOTED,
    OSXPHOTOS_EXPORT_DB,
)
from .phototemplate import get_template_help, TEMPLATE_SUBSTITUTIONS, TEMPLATE_SUBSTITUTIONS_MULTI_VALUED


class ExportCommand(click.Command):
    """ Custom click.Command that overrides get_help() to show additional help info for export """

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = click.HelpFormatter()

        # passed to click.HelpFormatter.write_dl for formatting

        formatter.write("\n\n")
        formatter.write_text("** Export **")
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
        formatter.write_text("** Extended Attributes **")
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
        formatter.write_text("** Templating System **")
        formatter.write_text(get_template_help())
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
            + 'preserve the folder/album structure, you can use --keyword-template "{folder_album}"'
        )
        formatter.write("\n")
        formatter.write_text(
            "In the template, valid template substitutions will be replaced by "
            + "the corresponding value from the table below.  Invalid substitutions will result in a "
            + "an error and the script will abort."
        )
        formatter.write("\n")
        formatter.write_text(
            "If you want the actual text of the template substition to appear "
            + "in the rendered name, use double braces, e.g. '{{' or '}}', thus "
            + "using '{created.year}/{{name}}' for --directory "
            + "would result in output of 2020/{name}/photoname.jpg"
        )
        formatter.write("\n")
        formatter.write_text(
            "You may specify an optional default value to use if the substitution does not contain a value "
            + "(e.g. the value is null) "
            + "by specifying the default value after a ',' in the template string: "
            + "for example, if template is '{created.year}/{place.address,NO_ADDRESS}' "
            + "but there was no address associated with the photo, the resulting output would be: "
            + "'2020/NO_ADDRESS/photoname.jpg'. "
            + "If specified, the default value may not contain a brace symbol ('{' or '}')."
        )
        formatter.write("\n")
        formatter.write_text(
            "If you do not specify a default value and the template substitution "
            + "has no value, '_' (underscore) will be used as the default value. For example, in the "
            + "above example, this would result in '2020/_/photoname.jpg' if address was null."
        )
        formatter.write("\n")
        formatter.write_text(
            'You may specify a null default (e.g. "" or empty string) by omitting the value after '
            + 'the comma, e.g. {title,} which would render to "" if title had no value.'
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
        help_text += formatter.getvalue()
        return help_text
