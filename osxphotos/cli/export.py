"""export command for osxphotos CLI"""

from __future__ import annotations

import atexit
import inspect
import os
import pathlib
import platform
import subprocess
import sys
import time
from typing import Any, Callable, Iterable, List, Literal, Optional, Tuple

import click

import osxphotos
import osxphotos.gitignorefile
from osxphotos._constants import (
    _EXIF_TOOL_URL,
    _OSXPHOTOS_NONE_SENTINEL,
    DEFAULT_EDITED_SUFFIX,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_ORIGINAL_SUFFIX,
    DEFAULT_PREVIEW_SUFFIX,
    EXTENDED_ATTRIBUTE_NAMES,
    EXTENDED_ATTRIBUTE_NAMES_QUOTED,
    OSXPHOTOS_EXPORT_DB,
    POST_COMMAND_CATEGORIES,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
)
from osxphotos._version import __version__
from osxphotos.configoptions import (
    ConfigOptions,
    ConfigOptionsInvalidError,
    ConfigOptionsLoadError,
)
from osxphotos.crash_reporter import crash_reporter, set_crash_data
from osxphotos.datetime_formatter import DateTimeFormatter
from osxphotos.debug import is_debug
from osxphotos.exiftool import get_exiftool_path
from osxphotos.exifwriter import ExifWriter, exif_options_from_options
from osxphotos.export_db import ExportDB, ExportDBInMemory
from osxphotos.exportoptions import ExportOptions, ExportResults
from osxphotos.fileutil import FileUtilMacOS, FileUtilNoOp, FileUtilShUtil
from osxphotos.path_utils import is_valid_filepath, sanitize_filename, sanitize_filepath
from osxphotos.photoexporter import PhotoExporter
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.photoquery import load_uuid_from_file, query_options_from_kwargs
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.platform import get_macos_version, is_macos
from osxphotos.unicode import normalize_fs_path
from osxphotos.uti import get_preferred_uti_extension
from osxphotos.utils import (
    format_sec_to_hhmmss,
    is_mounted_volume,
    pluralize,
    under_test,
)

if is_macos:
    from osxmetadata import (
        MDITEM_ATTRIBUTE_DATA,
        MDITEM_ATTRIBUTE_SHORT_NAMES,
        OSXMetaData,
        Tag,
    )
    from osxmetadata.constants import _TAGS_NAMES

    from osxphotos.photokit import (
        check_photokit_authorization,
        request_photokit_authorization,
    )
    from osxphotos.photosalbum import PhotosAlbum

from osxphotos.iphoto import is_iphoto_library

from .cli_commands import logger
from .cli_params import (
    DB_ARGUMENT,
    DB_OPTION,
    DELETED_OPTIONS,
    JSON_OPTION,
    QUERY_OPTIONS,
    THEME_OPTION,
    TIMESTAMP_OPTION,
    VERBOSE_OPTION,
)
from .click_rich_echo import rich_click_echo, rich_echo, rich_echo_error
from .common import (
    CLI_COLOR_ERROR,
    CLI_COLOR_WARNING,
    OSXPHOTOS_CRASH_LOG,
    OSXPHOTOS_HIDDEN,
    get_photos_db,
    noop,
)
from .help import ExportCommand, get_help_msg
from .list import _list_libraries
from .param_types import CSVOptions, ExportDBType, FunctionCall, TemplateString
from .report_writer import ReportWriterNoOp, export_report_writer_factory
from .rich_progress import rich_progress
from .sidecar import generate_user_sidecar
from .verbose import get_verbose_console, verbose_print


@click.command(cls=ExportCommand)
@DB_OPTION
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@click.option(
    "--no-progress", is_flag=True, help="Do not display progress bar during export."
)
@QUERY_OPTIONS
@DELETED_OPTIONS
@click.option(
    "--update",
    is_flag=True,
    help="Only export new or updated files. "
    "See also --force-update and notes below on export and --update.",
)
@click.option(
    "--force-update",
    is_flag=True,
    help="Only export new or updated files. Unlike --update, --force-update will re-export photos "
    "if their metadata has changed even if this would not otherwise trigger an export. "
    "See also --update and notes below on export and --update.",
)
@click.option(
    "--update-errors",
    is_flag=True,
    help="Update files that were previously exported but produced errors during export. "
    "For example, if a file produced an error with --exiftool due to bad metadata, "
    "this option will re-export the file and attempt to write the metadata again "
    "when used with --exiftool and --update. "
    "Without --update-errors, photos that were successfully exported but generated "
    "an error or warning during export will not be re-attempted if metadata has not changed. "
    "Must be used with --update.",
)
@click.option(
    "--ignore-signature",
    is_flag=True,
    help="When used with '--update', ignores file signature when updating files. "
    "This is useful if you have processed or edited exported photos changing the "
    "file signature (size & modification date). In this case, '--update' would normally "
    "re-export the processed files but with '--ignore-signature', files which exist "
    "in the export directory will not be re-exported. "
    "If used with '--sidecar', '--ignore-signature' has the following behavior: "
    "1) if the metadata (in Photos) that went into the sidecar did not change, "
    "the sidecar will not be updated; "
    "2) if the metadata (in Photos) that went into the sidecar did change, "
    "a new sidecar is written but a new image file is not; "
    "3) if a sidecar does not exist for the photo, a sidecar will be written "
    "whether or not the photo file was written or updated.",
)
@click.option(
    "--only-new",
    is_flag=True,
    help="If used with --update, ignores any previously exported files, even if missing from "
    "the export folder and only exports new files that haven't previously been exported.",
)
@click.option(
    "--limit",
    metavar="LIMIT",
    help="Export at most LIMIT photos. "
    "Useful for testing. May be used with --update to export incrementally.",
    type=int,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run (test) the export but don't actually export any files; most useful with --verbose.",
)
@click.option(
    "--export-as-hardlink",
    is_flag=True,
    help="Hardlink files instead of copying them. "
    "Cannot be used with --exiftool which creates copies of the files with embedded EXIF data. "
    "Note: on APFS volumes, files are cloned when exporting giving many of the same "
    "advantages as hardlinks without having to use --export-as-hardlink.",
)
@click.option(
    "--touch-file",
    is_flag=True,
    help="Sets the file's modification time to match photo date.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing files. "
    "Default behavior is to add (1), (2), etc to filename if file already exists. "
    "Use this with caution as it may create name collisions on export. "
    "(e.g. if two files happen to have the same name)",
)
@click.option(
    "--retry",
    metavar="RETRY",
    type=click.INT,
    help="Automatically retry export up to RETRY times if an error occurs during export.  "
    "This may be useful with network drives that experience intermittent errors.",
)
@click.option(
    "--export-by-date",
    is_flag=True,
    help="Automatically create output folders to organize photos by date created "
    "(e.g. DEST/2019/12/20/photoname.jpg).",
)
@click.option(
    "--skip-edited",
    is_flag=True,
    help="Do not export edited version of photo if an edited version exists.",
)
@click.option(
    "--skip-original-if-edited",
    is_flag=True,
    help="Do not export original if there is an edited version (exports only the edited version).",
)
@click.option(
    "--skip-bursts",
    is_flag=True,
    help="Do not export all associated burst images in the library if a photo is a burst photo.  ",
)
@click.option(
    "--skip-live",
    is_flag=True,
    help="Do not export the associated live video component of a live photo.",
)
@click.option(
    "--skip-raw",
    is_flag=True,
    help="Do not export associated RAW image of a RAW+JPEG pair.  "
    "Note: this does not skip RAW photos if the RAW photo does not have an associated JPEG image "
    "(e.g. the RAW file was imported to Photos without a JPEG preview).",
)
@click.option(
    "--skip-uuid",
    metavar="UUID",
    default=None,
    multiple=True,
    help="Skip photos with UUID(s) during export. "
    "May be repeated to include multiple UUIDs.",
)
@click.option(
    "--skip-uuid-from-file",
    metavar="FILE",
    default=None,
    multiple=False,
    help="Skip photos with UUID(s) loaded from FILE. "
    "Format is a single UUID per line.  Lines preceded with # are ignored.",
    type=click.Path(exists=True),
)
@click.option(
    "--current-name",
    is_flag=True,
    help="Use photo's current filename instead of original filename for export.  "
    "Note: Starting with Photos 5, all photos are renamed upon import.  By default, "
    "photos are exported with the the original name they had before import.",
)
@click.option(
    "--convert-to-jpeg",
    is_flag=True,
    help="Convert all non-JPEG images (e.g. RAW, HEIC, PNG, etc) to JPEG upon export. "
    "Note: does not convert the RAW component of a RAW+JPEG pair as the associated JPEG image "
    "will be exported. You can use --skip-raw to skip exporting the associated RAW image of "
    "a RAW+JPEG pair. See also --jpeg-quality and --jpeg-ext. "
    "Only works if your Mac has a GPU (thus may not work on virtual machines).",
)
@click.option(
    "--jpeg-quality",
    type=click.FloatRange(0.0, 1.0),
    help="Value in range 0.0 to 1.0 to use with --convert-to-jpeg. "
    "A value of 1.0 specifies best quality, "
    "a value of 0.0 specifies maximum compression. "
    f"Defaults to {DEFAULT_JPEG_QUALITY}",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Export preview image generated by Photos. "
    "This is a lower-resolution image used by Photos to quickly preview the image. "
    "See also --preview-suffix and --preview-if-missing.",
)
@click.option(
    "--preview-if-missing",
    is_flag=True,
    help="Export preview image generated by Photos if the actual photo file is missing from the library. "
    "This may be helpful if photos were not copied to the Photos library and the original photo is missing. "
    "See also --preview-suffix and --preview.",
)
@click.option(
    "--preview-suffix",
    metavar="SUFFIX",
    help="Optional suffix template for naming preview photos.  Default name for preview photos is in form "
    f"'photoname{DEFAULT_PREVIEW_SUFFIX}.ext'. For example, with '--preview-suffix _low_res', the preview photo "
    f"would be named 'photoname_low_res.ext'.  The default suffix is '{DEFAULT_PREVIEW_SUFFIX}'. "
    "Multi-value templates (see Templating System) are not permitted with --preview-suffix. "
    "See also --preview and --preview-if-missing.",
    type=TemplateString(),
)
@click.option(
    "--download-missing",
    is_flag=True,
    help="Attempt to download missing photos from iCloud. The current implementation uses Applescript "
    "to interact with Photos to export the photo which will force Photos to download from iCloud if "
    "the photo does not exist on disk.  This will be slow and will require internet connection. "
    "This obviously only works if the Photos library is synched to iCloud.  "
    "Note: --download-missing does not currently export all burst images; "
    "only the primary photo will be exported--associated burst images will be skipped.",
)
@click.option(
    "--export-aae",
    is_flag=True,
    help="Also export an adjustments file detailing edits made to the original. "
    "The resulting file is named photoname.AAE. "
    "Note that to import these files back to Photos succesfully, you also need to "
    "export the edited photo and match the filename format Photos.app expects: "
    "--filename 'IMG_{edited_version?E,}{id:04d}' --edited-suffix ''",
)
@click.option(
    "--sidecar",
    default=None,
    multiple=True,
    metavar="FORMAT",
    type=click.Choice(["xmp", "json", "exiftool"], case_sensitive=False),
    help="Create sidecar for each photo exported; valid FORMAT values: xmp, json, exiftool; "
    "--sidecar xmp: create XMP sidecar used by Digikam, Adobe Lightroom, etc. "
    "The sidecar file is named in format photoname.ext.xmp "
    "The XMP sidecar exports the following tags: Description, Title, Keywords/Tags, "
    "Subject (set to Keywords + PersonInImage), PersonInImage, CreateDate, ModifyDate, "
    "GPSLongitude, Face Regions (Metadata Working Group and Microsoft Photo)."
    f"\n--sidecar json: create JSON sidecar useable by exiftool ({_EXIF_TOOL_URL}) "
    "The sidecar file can be used to apply metadata to the file with exiftool, for example: "
    '"exiftool -j=photoname.jpg.json photoname.jpg" '
    "The sidecar file is named in format photoname.ext.json; "
    "format includes tag groups (equivalent to running 'exiftool -G -j'). "
    "\n--sidecar exiftool: create JSON sidecar compatible with output of 'exiftool -j'. "
    "Unlike '--sidecar json', '--sidecar exiftool' does not export tag groups. "
    "Sidecar filename is in format photoname.ext.json; "
    "For a list of tags exported in the JSON and exiftool sidecar, see '--exiftool'. "
    "See also '--ignore-signature'.",
)
@click.option(
    "--sidecar-drop-ext",
    is_flag=True,
    help="Drop the photo's extension when naming sidecar files. "
    "By default, sidecar files are named in format 'photo_filename.photo_ext.sidecar_ext', "
    "e.g. 'IMG_1234.JPG.xmp'. Use '--sidecar-drop-ext' to ignore the photo extension. "
    "Resulting sidecar files will have name in format 'IMG_1234.xmp'. "
    "Warning: this may result in sidecar filename collisions if there are files of different "
    "types but the same name in the output directory, e.g. 'IMG_1234.JPG' and 'IMG_1234.MOV'.",
)
@click.option(
    "--sidecar-template",
    metavar="MAKO_TEMPLATE_FILE SIDECAR_FILENAME_TEMPLATE OPTIONS",
    multiple=True,
    type=click.Tuple(
        [
            click.Path(dir_okay=False, file_okay=True, exists=True),
            TemplateString(),
            CSVOptions(
                [
                    "write_skipped",
                    "strip_whitespace",
                    "strip_lines",
                    "skip_zero",
                    "catch_errors",
                    "none",
                ]
            ),
        ]
    ),
    help="Create a custom sidecar file for each photo exported with user provided Mako template (MAKO_TEMPLATE_FILE). "
    "MAKO_TEMPLATE_FILE must be a valid Mako template (see https://www.makotemplates.org/). "
    "The template will passed the following variables: photo (PhotoInfo object for the photo being exported), "
    "sidecar_path (pathlib.Path object for the path to the sidecar being written), and "
    "photo_path (pathlib.Path object for the path to the exported photo. "
    "SIDECAR_FILENAME_TEMPLATE must be a valid template string (see Templating System in help) "
    "which will be rendered to generate the filename of the sidecar file. "
    "The `{filepath}` template variable may be used in the SIDECAR_FILENAME_TEMPLATE to refer to the filename of the "
    "photo being exported. "
    "OPTIONS is a comma-separated list of strings providing additional options to the template. "
    "Valid options are: write_skipped, strip_whitespace, strip_lines, skip_zero, catch_errors, none. "
    "write_skipped will cause the sidecar file to be written even if the photo is skipped during export. "
    "If write_skipped is not passed as an option, the sidecar file will not be written if the photo is skipped during export. "
    "strip_whitespace and strip_lines indicate whether or not to strip whitespace and blank lines, respectively, "
    "from the resulting sidecar file. "
    "skip_zero causes the sidecar file to be skipped if the rendered template is zero-length. "
    "catch_errors causes errors in the template to be caught and logged but not raised. "
    "Without catch_errors, osxphotos will abort the export if an error occurs in the template. "
    "For example, to create a sidecar file with extension .xmp using a template file named 'sidecar.mako' "
    "and write a sidecar for skipped photos and strip blank lines but not whitespace: "
    "`--sidecar-template sidecar.mako '{filepath}.xmp' write_skipped,strip_lines`. "
    "To do the same but to drop the photo extension from the sidecar filename: "
    "`--sidecar-template sidecar.mako '{filepath.parent}/{filepath.stem}.xmp' write_skipped,strip_lines`. "
    "If you are not passing any options, you must pass 'none' as the last argument to --sidecar-template: "
    "`--sidecar-template sidecar.mako '{filepath}.xmp' none`. "
    "For an example Mako file see https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/custom_sidecar.mako",
)
@click.option(
    "--exiftool",
    is_flag=True,
    help="Use exiftool to write metadata directly to exported photos. "
    "To use this option, exiftool must be installed and in the path.  "
    "exiftool may be installed from https://exiftool.org/.  "
    "Cannot be used with --export-as-hardlink.  Writes the following metadata: "
    "EXIF:ImageDescription, XMP:Description (see also --description-template); "
    "XMP:Title; XMP:TagsList, IPTC:Keywords, XMP:Subject "
    "(see also --keyword-template, --person-keyword, --album-keyword); "
    "XMP:PersonInImage; EXIF:GPSLatitudeRef; EXIF:GPSLongitudeRef; EXIF:GPSLatitude; EXIF:GPSLongitude; "
    "EXIF:GPSPosition; EXIF:DateTimeOriginal; EXIF:OffsetTimeOriginal; "
    "EXIF:ModifyDate (see --ignore-date-modified); IPTC:DateCreated; IPTC:TimeCreated; "
    "(video files only): QuickTime:CreationDate; QuickTime:CreateDate; QuickTime:ModifyDate (see also --ignore-date-modified); "
    "QuickTime:GPSCoordinates; UserData:GPSCoordinates.",
)
@click.option(
    "--exiftool-path",
    metavar="EXIFTOOL_PATH",
    type=click.Path(exists=True),
    help="Optionally specify path to exiftool; if not provided, will look for exiftool in $PATH.",
)
@click.option(
    "--exiftool-option",
    multiple=True,
    metavar="OPTION",
    help="Optional flag/option to pass to exiftool when using --exiftool. "
    "For example, --exiftool-option '-m' to ignore minor warnings. "
    "Specify these as you would on the exiftool command line. "
    "See exiftool docs at https://exiftool.org/exiftool_pod.html for full list of options. "
    "More than one option may be specified by repeating the option, e.g. "
    "--exiftool-option '-m' --exiftool-option '-F'. ",
)
@click.option(
    "--exiftool-merge-keywords",
    is_flag=True,
    help="Merge any keywords found in the original file with keywords used for '--exiftool' and '--sidecar'.",
)
@click.option(
    "--exiftool-merge-persons",
    is_flag=True,
    help="Merge any persons found in the original file with persons used for '--exiftool' and '--sidecar'.",
)
@click.option(
    "--favorite-rating",
    is_flag=True,
    help="When used with --exiftool or --sidecar, "
    "set XMP:Rating=5 for photos marked as Favorite and XMP:Rating=0 for non-Favorites. "
    "If not specified, XMP:Rating is not set.",
)
@click.option(
    "--ignore-date-modified",
    is_flag=True,
    help="If used with --exiftool or --sidecar, will ignore the photo "
    "modification date and set EXIF:ModifyDate to EXIF:DateTimeOriginal; "
    "this is consistent with how Photos handles the EXIF:ModifyDate tag.",
)
@click.option(
    "--person-keyword",
    is_flag=True,
    help="Use person in image as keyword/tag when exporting metadata.",
)
@click.option(
    "--album-keyword",
    is_flag=True,
    help="Use album name as keyword/tag when exporting metadata.",
)
@click.option(
    "--keyword-template",
    metavar="TEMPLATE",
    multiple=True,
    default=None,
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "keyword in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to add "
    "the full path to the folder and album photo is contained in as a keyword when exporting "
    'you could specify --keyword-template "{folder_album}" '
    'You may specify more than one template, for example --keyword-template "{folder_album}" '
    '--keyword-template "{created.year}". '
    "See '--replace-keywords' and Templating System below.",
    type=TemplateString(),
)
@click.option(
    "--replace-keywords",
    is_flag=True,
    help="Replace keywords with any values specified with --keyword-template. "
    "By default, --keyword-template will add keywords to any keywords already associated "
    "with the photo.  If --replace-keywords is specified, values from --keyword-template "
    "will replace any existing keywords instead of adding additional keywords.",
)
@click.option(
    "--description-template",
    metavar="TEMPLATE",
    multiple=False,
    default=None,
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "description in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to append "
    "'exported with osxphotos on [today's date]' to the description, you could specify "
    '--description-template "{descr} exported with osxphotos on {today.date}" '
    "See Templating System below.",
    type=TemplateString(),
)
@click.option(
    "--finder-tag-template",
    metavar="TEMPLATE",
    multiple=True,
    default=None,
    help="Set MacOS Finder tags to TEMPLATE. These tags can be searched in the Finder or Spotlight with "
    "'tag:tagname' format. For example, '--finder-tag-template \"{label}\"' to set Finder tags to photo labels. "
    "You may specify multiple TEMPLATE values by using '--finder-tag-template' multiple times. "
    "See also '--finder-tag-keywords and Extended Attributes below.'.",
    type=TemplateString(),
)
@click.option(
    "--finder-tag-keywords",
    is_flag=True,
    help="Set MacOS Finder tags to keywords; any keywords specified via '--keyword-template', '--person-keyword', etc. "
    "will also be used as Finder tags. See also '--finder-tag-template and Extended Attributes below.'.",
)
@click.option(
    "--xattr-template",
    nargs=2,
    metavar="ATTRIBUTE TEMPLATE",
    multiple=True,
    help="Set extended attribute ATTRIBUTE to TEMPLATE value. Valid attributes are: "
    f"{', '.join(EXTENDED_ATTRIBUTE_NAMES_QUOTED)}. "
    "For example, to set Finder comment to the photo's title and description: "
    '\'--xattr-template findercomment "{title}; {descr}" '
    "See Extended Attributes below for additional details on this option.",
    type=TemplateString(),
)
@click.option(
    "--directory",
    metavar="DIRECTORY",
    default=None,
    help="Optional template for specifying name of output directory in the form '{name,DEFAULT}'. "
    "See below for additional details on templating system.",
    type=TemplateString(),
)
@click.option(
    "--filename",
    "filename_template",
    metavar="FILENAME",
    default=None,
    help="Optional template for specifying name of output file in the form '{name,DEFAULT}'. "
    "File extension will be added automatically--do not include an extension in the FILENAME template. "
    "See below for additional details on templating system.",
    type=TemplateString(),
)
@click.option(
    "--jpeg-ext",
    multiple=False,
    metavar="EXTENSION",
    type=click.Choice(["jpeg", "jpg", "JPEG", "JPG"], case_sensitive=True),
    help="Specify file extension for JPEG files. Photos uses .jpeg for edited images but many images "
    "are imported with .jpg or .JPG which can result in multiple different extensions used for JPEG files "
    "upon export.  Use --jpeg-ext to specify a single extension to use for all exported JPEG images. "
    "Valid values are jpeg, jpg, JPEG, JPG; e.g. '--jpeg-ext jpg' to use '.jpg' for all JPEGs.",
)
@click.option(
    "--strip",
    is_flag=True,
    help="Optionally strip leading and trailing whitespace from any rendered templates. "
    'For example, if --filename template is "{title,} {original_name}" and image has no '
    "title, resulting file would have a leading space but if used with --strip, this will "
    "be removed.",
)
@click.option(
    "--edited-suffix",
    metavar="SUFFIX",
    help="Optional suffix template for naming edited photos.  Default name for edited photos is in form "
    "'photoname_edited.ext'. For example, with '--edited-suffix _bearbeiten', the edited photo "
    f"would be named 'photoname_bearbeiten.ext'.  The default suffix is '{DEFAULT_EDITED_SUFFIX}'. "
    "Multi-value templates (see Templating System) are not permitted with --edited-suffix.",
    type=TemplateString(),
)
@click.option(
    "--original-suffix",
    metavar="SUFFIX",
    help="Optional suffix template for naming original photos.  Default name for original photos is in form "
    "'filename.ext'. For example, with '--original-suffix _original', the original photo "
    "would be named 'filename_original.ext'.  The default suffix is '' (no suffix). "
    "Multi-value templates (see Templating System) are not permitted with --original-suffix.",
    type=TemplateString(),
)
@click.option(
    "--use-photos-export",
    is_flag=True,
    help="Force the use of AppleScript or PhotoKit to export even if not missing (see also '--download-missing' and '--use-photokit').",
)
@click.option(
    "--use-photokit",
    is_flag=True,
    help="Use with '--download-missing' or '--use-photos-export' to use direct Photos interface instead of AppleScript to export. "
    "Highly experimental alpha feature; does not work with iTerm2 (use with Terminal.app). "
    "This is faster and more reliable than the default AppleScript interface.",
)
@click.option(
    "--report",
    metavar="REPORT_FILE",
    help="Write a report of all files that were exported. "
    "The extension of the report filename will be used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    "REPORT_FILE may be a template string (see Templating System), for example, "
    "--report 'export_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=TemplateString(),
)
@click.option(
    "--append",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@click.option(
    "--cleanup",
    is_flag=True,
    help="Cleanup export directory by deleting any files which were not included in this export set. "
    "For example, photos which had previously been exported and were subsequently deleted in Photos. "
    "WARNING: --cleanup will delete *any* files in the export directory that were not exported by osxphotos, "
    "for example, your own scripts or other files.  Be sure this is what you intend before using "
    "--cleanup.  Use --dry-run with --cleanup first if you're not certain. "
    "To prevent files not generated by osxphotos from being deleted, you may specify one or more rules"
    "in a file named `.osxphotos_keep` in the export directory. "
    "This file uses the same format as a .gitignore file and should contain one rule per line; "
    "lines starting with a `#` will be ignored. "
    "Reference https://git-scm.com/docs/gitignore#_pattern_format for details. "
    "In addition to the standard .gitignore rules, the rules may also be the absolute path to a file or directory. "
    "For example if export destination is `/Volumes/Photos` and you want to keep all `.txt` files, "
    'in the top level of the export directory, you can specify `/*.txt"` in the .osxphotos_keep file. '
    "If you want to keep all `.txt` files in the export directory and all subdirectories, "
    "you can specify `**/*.txt`. "
    "If present, the .osxphotos_keep file will be read after the export is completed and any rules found in the file "
    "will be added to the list of rules to keep. "
    "See also --keep.",
)
@click.option(
    "--keep",
    metavar="KEEP_RULE",
    nargs=1,
    multiple=True,
    help="When used with --cleanup, prevents file or directory matching KEEP_RULE from being deleted "
    "when cleanup is run. Use this if there are files in the export directory that you don't "
    "want to be deleted when --cleanup is run. "
    "KEEP_RULE follows the same format rules a .gitignore file. "
    "Reference https://git-scm.com/docs/gitignore#_pattern_format for details. "
    "In addition to the standard .gitignore rules, KEEP_RULE may also be the absolute path to a file or directory. "
    "For example if export destination is `/Volumes/Photos` and you want to keep all `.txt` files, "
    'in the top level of the export directory, you can specify `--keep "/*.txt"`. '
    "If you want to keep all `.txt` files in the export directory and all subdirectories, "
    'you can specify `--keep "**/*.txt"`. '
    "If wild card is used, KEEP_RULE must be enclosed in quotes to prevent the shell from expanding the wildcard. "
    "--keep may be repeated to keep additional files/directories. "
    "Rules may also be included in a file named `.osxphotos_keep` in the export directory. "
    "If present, this file will be read after the export is completed and any rules found in the file "
    "will be added to the list of rules to keep. "
    "This file uses the same format as a .gitignore file and should contain one rule per line; "
    "lines starting with a `#` will be ignored. ",
)
@click.option(
    "--add-exported-to-album",
    metavar="ALBUM",
    help="Add all exported photos to album ALBUM in Photos. Album ALBUM will be created "
    "if it doesn't exist.  All exported photos will be added to this album. "
    "This only works if the Photos library being exported is the last-opened (default) library in Photos. "
    "This feature is currently experimental.  I don't know how well it will work on large export sets.",
)
@click.option(
    "--add-skipped-to-album",
    metavar="ALBUM",
    help="Add all skipped photos to album ALBUM in Photos. Album ALBUM will be created "
    "if it doesn't exist.  All skipped photos will be added to this album. "
    "This only works if the Photos library being exported is the last-opened (default) library in Photos. "
    "This feature is currently experimental.  I don't know how well it will work on large export sets.",
)
@click.option(
    "--add-missing-to-album",
    metavar="ALBUM",
    help="Add all missing photos to album ALBUM in Photos. Album ALBUM will be created "
    "if it doesn't exist.  All missing photos will be added to this album. "
    "This only works if the Photos library being exported is the last-opened (default) library in Photos. "
    "This feature is currently experimental.  I don't know how well it will work on large export sets.",
)
@click.option(
    "--post-command",
    metavar="CATEGORY COMMAND",
    nargs=2,
    multiple=True,
    help="Run COMMAND on exported files of category CATEGORY.  CATEGORY can be one of: "
    f"{', '.join(list(POST_COMMAND_CATEGORIES.keys()))}. "
    "COMMAND is an osxphotos template string, for example: '--post-command exported \"echo {filepath|shell_quote} >> {export_dir}/exported.txt\"', "
    "which appends the full path of all exported files to the file 'exported.txt'. "
    "You can run more than one command by repeating the '--post-command' option with different arguments. "
    "See also --post-command-error and --post-function."
    "See Post Command below.",
    type=click.Tuple(
        [click.Choice(POST_COMMAND_CATEGORIES, case_sensitive=False), TemplateString()]
    ),
)
@click.option(
    "--post-command-error",
    metavar="ACTION",
    help="Specify either `continue` or `break` for ACTION to control behavior when a post-command fails. "
    "If `continue`, osxphotos will log the error and continue processing. "
    "If `break`, osxphotos will stop processing any additional --post-command commands for the current photo "
    "but will continue with the export. "
    "Without --post-command-error, osxphotos will abort the export if a post-command encounters an error. ",
    type=click.Choice(["continue", "break"], case_sensitive=False),
)
@click.option(
    "--post-function",
    metavar="filename.py::function",
    nargs=1,
    type=FunctionCall(),
    multiple=True,
    help="Run function on exported files. Use this in format: --post-function filename.py::function where filename.py is a python "
    "file you've created and function is the name of the function in the python file you want to call.  The function will be "
    "passed information about the photo that's been exported and a list of all exported files associated with the photo. "
    "You can run more than one function by repeating the '--post-function' option with different arguments. "
    "See Post Function below.",
)
@click.option(
    "--exportdb",
    metavar="EXPORTDB_FILE",
    default=None,
    help=(
        "Specify alternate path for database file which stores state information for export and --update. "
        f"If --exportdb is not specified, export database will be saved to '{OSXPHOTOS_EXPORT_DB}' "
        "in the export directory.  If --exportdb is specified, it will be saved to the specified file. "
    ),
    type=ExportDBType(),
)
@click.option(
    "--ramdb",
    is_flag=True,
    help="Copy export database to memory during export; "
    "may improve performance when exporting over a network or slow disk but could result in "
    "losing update state information if the program is interrupted or crashes.",
)
@click.option(
    "--tmpdir",
    metavar="DIR",
    help="Specify alternate temporary directory. Default is system temporary directory. "
    "osxphotos needs to create a number of temporary files during export. In some cases, "
    "particularly if the Photos library is on an APFS volume that is not the system volume, "
    "osxphotos may run faster if you specify a temporary directory on the same volume as "
    "the Photos library.",
    type=click.Path(dir_okay=True, file_okay=False, exists=True),
)
@click.option(
    "--alt-copy",
    is_flag=True,
    help="Use alternate copy method that may be more reliable for some "
    "network attached storage (NAS) devices. Use --alt-copy if you experience "
    "problems exporting to a NAS device or SMB volume. "
    "Unlike the default copy method, --alt-copy does not support "
    "copy-on-write on APFS volumes nor does it preserve filesystem metadata.",
)
@click.option(
    "--load-config",
    required=False,
    metavar="CONFIG_FILE",
    default=None,
    help=(
        "Load options from file as written with --save-config. "
        "This allows you to save a complex export command to file for later reuse. "
        "For example: 'osxphotos export <lots of options here> --save-config osxphotos.toml' then "
        " 'osxphotos export /path/to/export --load-config osxphotos.toml'. "
        "If any other command line options are used in conjunction with --load-config, "
        "they will override the corresponding values in the config file."
    ),
    type=click.Path(exists=True),
)
@click.option(
    "--save-config",
    required=False,
    metavar="CONFIG_FILE",
    default=None,
    help="Save options to file for use with --load-config. File format is TOML. "
    "See also --config-only.",
    type=click.Path(),
)
@click.option(
    "--config-only",
    is_flag=True,
    help="If specified, saves the config file but does not export any files; must be used with --save-config.",
)
@click.option(
    "--print",
    "print_template",
    metavar="TEMPLATE",
    multiple=True,
    help="Render TEMPLATE string for each photo being exported and print to stdout. "
    "TEMPLATE is an osxphotos template string. "
    "This may be useful for creating custom reports, etc. "
    "TEMPLATE will be printed after the photo is exported or skipped. "
    "May be repeated to print multiple template strings. ",
)
@click.option(
    "--beta",
    is_flag=True,
    default=False,
    hidden=OSXPHOTOS_HIDDEN,
    help="Enable beta options.",
)
@THEME_OPTION
@DB_ARGUMENT
@click.argument("dest", nargs=1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
@crash_reporter(
    OSXPHOTOS_CRASH_LOG,
    "[red]Something went wrong and osxphotos encountered an error:[/red]",
    "osxphotos crash log",
    "Please file a bug report at https://github.com/RhetTbull/osxphotos/issues with the crash log attached.",
    f"osxphotos version: {__version__}",
)
def export(
    ctx,
    cli_obj,
    db,
    photos_library,
    add_exported_to_album,
    add_missing_to_album,
    add_skipped_to_album,
    added_after,
    added_before,
    added_in_last,
    album,
    album_keyword,
    alt_copy,
    append,
    beta,
    burst,
    cleanup,
    cloudasset,
    config_only,
    convert_to_jpeg,
    current_name,
    deleted,
    deleted_only,
    description,
    description_template,
    dest,
    directory,
    download_missing,
    dry_run,
    duplicate,
    edited,
    edited_suffix,
    exif,
    exiftool,
    exiftool_merge_keywords,
    exiftool_merge_persons,
    exiftool_option,
    exiftool_path,
    export_as_hardlink,
    export_by_date,
    exportdb,
    external_edit,
    favorite,
    favorite_rating,
    filename_template,
    finder_tag_keywords,
    finder_tag_template,
    folder,
    force_update,
    from_date,
    from_time,
    has_comment,
    has_likes,
    has_raw,
    hdr,
    hidden,
    ignore_case,
    ignore_date_modified,
    ignore_signature,
    in_album,
    incloud,
    is_reference,
    jpeg_ext,
    jpeg_quality,
    keep,
    keyword,
    keyword_template,
    label,
    limit,
    live,
    load_config,
    location,
    max_size,
    min_size,
    missing,
    name,
    no_comment,
    no_description,
    no_keyword,
    no_likes,
    no_location,
    no_place,
    no_progress,
    no_title,
    not_burst,
    not_cloudasset,
    not_edited,
    not_favorite,
    not_hdr,
    not_hidden,
    not_in_album,
    not_incloud,
    not_live,
    not_missing,
    not_panorama,
    not_portrait,
    not_reference,
    not_screenshot,
    not_selfie,
    not_shared,
    not_slow_mo,
    not_time_lapse,
    only_movies,
    only_new,
    only_photos,
    original_suffix,
    overwrite,
    panorama,
    person,
    person_keyword,
    place,
    portrait,
    post_command,
    post_command_error,
    post_function,
    preview,
    preview_if_missing,
    preview_suffix,
    print_template,
    query_eval,
    query_function,
    ramdb,
    regex,
    replace_keywords,
    report,
    retry,
    save_config,
    screenshot,
    selfie,
    shared,
    export_aae,
    sidecar,
    sidecar_drop_ext,
    sidecar_template,
    skip_bursts,
    skip_edited,
    skip_live,
    skip_original_if_edited,
    skip_raw,
    skip_uuid,
    skip_uuid_from_file,
    slow_mo,
    strip,
    theme,
    time_lapse,
    timestamp,
    title,
    tmpdir,
    to_date,
    to_time,
    touch_file,
    update,
    update_errors,
    use_photokit,
    use_photos_export,
    uti,
    uuid,
    uuid_from_file,
    verbose_flag,
    xattr_template,
    year,
    syndicated,
    not_syndicated,
    saved_to_library,
    not_saved_to_library,
    shared_moment,
    not_shared_moment,
    shared_library,
    not_shared_library,
    selected=False,  # Isn't provided on unsupported platforms
    # debug,  # debug, watch, breakpoint handled in cli/__init__.py
    # watch,
    # breakpoint,
):
    """Export photos from the Photos database.
    Export path DEST is required.

    Optionally, query the Photos database using 1 or more search options;
    if more than one different option is provided, they are treated as "AND"
    (e.g. search for photos matching all options).
    If the same query option is provided multiple times, they are treated as
    "OR" (e.g. search for photos matching any of the options).
    If no query options are provided, all photos will be exported.

    For example, adding the query options:

    --person "John Doe" --person "Jane Doe" --keyword "vacation"

    will export all photos with either person of ("John Doe" OR "Jane Doe") AND keyword of "vacation"

    By default, all versions of all photos will be exported including edited
    versions, live photo movies, burst photos, and associated raw images.
    See --skip-edited, --skip-live, --skip-bursts, and --skip-raw options
    to modify this behavior.
    """

    # capture locals for use with ConfigOptions before changing any of them
    locals_ = locals()
    crash_data = locals_.copy()
    set_crash_data("locals", crash_data)

    # config expects --verbose to be named "verbose" not "verbose_flag"
    locals_["verbose"] = verbose_flag
    del locals_["verbose_flag"]

    # NOTE: because of the way ConfigOptions works, Click options must not
    # set defaults which are not None or False. If defaults need to be set
    # do so below after load_config and save_config are handled.
    cfg = ConfigOptions(
        "export",
        locals_,
        ignore=["ctx", "cli_obj", "dest", "load_config", "save_config", "config_only"],
    )

    verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)

    if load_config:
        try:
            cfg.load_from_file(load_config)
        except ConfigOptionsLoadError as e:
            # click.echo(
            #     click.style(
            #         f"Error parsing {load_config} config file: {e.message}",
            #         fg=CLI_COLOR_ERROR,
            #     ),
            #     err=True,
            # )
            rich_click_echo(
                f"[error]Error parsing {load_config} config file: {e.message}", err=True
            )
            sys.exit(1)

        # re-set the local vars to the corresponding config value
        # this isn't elegant but avoids having to rewrite this function to use cfg.varname for every parameter
        # the query options appear to be unaccessed but they are used below by query_options_from_kwargs
        # which accesses them via locals() to avoid a long list of parameters
        add_exported_to_album = cfg.add_exported_to_album
        add_missing_to_album = cfg.add_missing_to_album
        add_skipped_to_album = cfg.add_skipped_to_album
        added_after = cfg.added_after
        added_before = cfg.added_before
        added_in_last = cfg.added_in_last
        album = cfg.album
        album_keyword = cfg.album_keyword
        alt_copy = cfg.alt_copy
        append = cfg.append
        beta = cfg.beta
        burst = cfg.burst
        cleanup = cfg.cleanup
        cloudasset = cfg.cloudasset
        convert_to_jpeg = cfg.convert_to_jpeg
        current_name = cfg.current_name
        db = cfg.db
        deleted = cfg.deleted
        deleted_only = cfg.deleted_only
        description = cfg.description
        description_template = cfg.description_template
        directory = cfg.directory
        download_missing = cfg.download_missing
        dry_run = cfg.dry_run
        duplicate = cfg.duplicate
        edited = cfg.edited
        edited_suffix = cfg.edited_suffix
        exif = cfg.exif
        exiftool = cfg.exiftool
        exiftool_merge_keywords = cfg.exiftool_merge_keywords
        exiftool_merge_persons = cfg.exiftool_merge_persons
        exiftool_option = cfg.exiftool_option
        exiftool_path = cfg.exiftool_path
        export_aae = cfg.export_aae
        export_as_hardlink = cfg.export_as_hardlink
        export_by_date = cfg.export_by_date
        exportdb = cfg.exportdb
        external_edit = cfg.external_edit
        favorite = cfg.favorite
        favorite_rating = cfg.favorite_rating
        filename_template = cfg.filename_template
        finder_tag_keywords = cfg.finder_tag_keywords
        finder_tag_template = cfg.finder_tag_template
        folder = cfg.folder
        force_update = cfg.force_update
        from_date = cfg.from_date
        from_time = cfg.from_time
        has_comment = cfg.has_comment
        has_likes = cfg.has_likes
        has_raw = cfg.has_raw
        hdr = cfg.hdr
        hidden = cfg.hidden
        ignore_case = cfg.ignore_case
        ignore_date_modified = cfg.ignore_date_modified
        ignore_signature = cfg.ignore_signature
        in_album = cfg.in_album
        incloud = cfg.incloud
        is_reference = cfg.is_reference
        jpeg_ext = cfg.jpeg_ext
        jpeg_quality = cfg.jpeg_quality
        keep = cfg.keep
        keyword = cfg.keyword
        keyword_template = cfg.keyword_template
        label = cfg.label
        limit = cfg.limit
        live = cfg.live
        location = cfg.location
        max_size = cfg.max_size
        min_size = cfg.min_size
        missing = cfg.missing
        name = cfg.name
        no_comment = cfg.no_comment
        no_description = cfg.no_description
        no_keyword = cfg.no_keyword
        no_likes = cfg.no_likes
        no_location = cfg.no_location
        no_place = cfg.no_place
        no_progress = cfg.no_progress
        no_title = cfg.no_title
        not_burst = cfg.not_burst
        not_cloudasset = cfg.not_cloudasset
        not_edited = cfg.not_edited
        not_favorite = cfg.not_favorite
        not_hdr = cfg.not_hdr
        not_hidden = cfg.not_hidden
        not_in_album = cfg.not_in_album
        not_incloud = cfg.not_incloud
        not_live = cfg.not_live
        not_missing = cfg.not_missing
        not_panorama = cfg.not_panorama
        not_portrait = cfg.not_portrait
        not_reference = cfg.not_reference
        not_saved_to_library = cfg.not_saved_to_library
        not_screenshot = cfg.not_screenshot
        not_selfie = cfg.not_selfie
        not_shared = cfg.not_shared
        not_shared_library = cfg.not_shared_library
        not_shared_moment = cfg.not_shared_moment
        not_slow_mo = cfg.not_slow_mo
        not_syndicated = cfg.not_syndicated
        not_time_lapse = cfg.not_time_lapse
        only_movies = cfg.only_movies
        only_new = cfg.only_new
        only_photos = cfg.only_photos
        original_suffix = cfg.original_suffix
        overwrite = cfg.overwrite
        panorama = cfg.panorama
        person = cfg.person
        person_keyword = cfg.person_keyword
        photos_library = cfg.photos_library
        place = cfg.place
        portrait = cfg.portrait
        post_command = cfg.post_command
        post_command_error = cfg.post_command_error
        post_function = cfg.post_function
        preview = cfg.preview
        preview_if_missing = cfg.preview_if_missing
        preview_suffix = cfg.preview_suffix
        print_template = cfg.print_template
        query_eval = cfg.query_eval
        query_function = cfg.query_function
        ramdb = cfg.ramdb
        regex = cfg.regex
        replace_keywords = cfg.replace_keywords
        report = cfg.report
        retry = cfg.retry
        saved_to_library = cfg.saved_to_library
        screenshot = cfg.screenshot
        selected = cfg.selected
        selfie = cfg.selfie
        shared = cfg.shared
        shared_library = cfg.shared_library
        shared_moment = cfg.shared_moment
        sidecar = cfg.sidecar
        sidecar_drop_ext = cfg.sidecar_drop_ext
        sidecar_template = cfg.sidecar_template
        skip_bursts = cfg.skip_bursts
        skip_edited = cfg.skip_edited
        skip_live = cfg.skip_live
        skip_original_if_edited = cfg.skip_original_if_edited
        skip_raw = cfg.skip_raw
        skip_uuid = cfg.skip_uuid
        skip_uuid_from_file = cfg.skip_uuid_from_file
        slow_mo = cfg.slow_mo
        strip = cfg.strip
        syndicated = cfg.syndicated
        theme = cfg.theme
        time_lapse = cfg.time_lapse
        timestamp = cfg.timestamp
        title = cfg.title
        tmpdir = cfg.tmpdir
        to_date = cfg.to_date
        to_time = cfg.to_time
        touch_file = cfg.touch_file
        update = cfg.update
        update_errors = cfg.update_errors
        use_photokit = cfg.use_photokit
        use_photos_export = cfg.use_photos_export
        uti = cfg.uti
        uuid = cfg.uuid
        uuid_from_file = cfg.uuid_from_file
        verbose_flag = (
            cfg.verbose
        )  # this is named differently in the config file than the variable passed by --verbose (verbose_flag)
        xattr_template = cfg.xattr_template
        year = cfg.year

        # config file might have changed verbose
        verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)
        verbose(f"Loaded options from file [filepath]{load_config}")

        set_crash_data("cfg", cfg.asdict())

    verbose(f"osxphotos version: {__version__}")
    verbose(f"Python version: {sys.version}")
    if is_macos:
        verbose(f"Platform: {platform.platform()}, {'.'.join(get_macos_version())}")
    else:
        verbose(f"Platform: {platform.platform()}")
    verbose(f"Verbose level: {verbose_flag}")

    # validate options
    exclusive_options = [
        ("burst", "not_burst"),
        ("cloudasset", "not_cloudasset"),
        ("deleted", "deleted_only"),
        ("description", "no_description"),
        ("edited", "not_edited"),
        ("export_as_hardlink", "convert_to_jpeg"),
        ("export_as_hardlink", "download_missing"),
        ("export_as_hardlink", "exiftool"),
        ("export_by_date", "directory"),
        ("favorite", "not_favorite"),
        ("has_comment", "no_comment"),
        ("has_likes", "no_likes"),
        ("hdr", "not_hdr"),
        ("hidden", "not_hidden"),
        ("in_album", "not_in_album"),
        ("incloud", "not_incloud"),
        ("is_reference", "not_reference"),
        ("keyword", "no_keyword"),
        ("live", "not_live"),
        ("location", "no_location"),
        ("missing", "not_missing"),
        ("only_photos", "only_movies"),
        ("panorama", "not_panorama"),
        ("place", "no_place"),
        ("portrait", "not_portrait"),
        ("screenshot", "not_screenshot"),
        ("selfie", "not_selfie"),
        ("shared", "not_shared"),
        ("skip_edited", "skip_original_if_edited"),
        ("slow_mo", "not_slow_mo"),
        ("time_lapse", "not_time_lapse"),
        ("title", "no_title"),
        ("syndicated", "not_syndicated"),
        ("saved_to_library", "not_saved_to_library"),
        ("shared_moment", "not_shared_moment"),
    ]
    dependent_options = [
        ("append", ("report")),
        ("exiftool_merge_keywords", ("exiftool", "sidecar")),
        ("exiftool_merge_persons", ("exiftool", "sidecar")),
        ("exiftool_option", ("exiftool")),
        ("favorite_rating", ("exiftool", "sidecar")),
        ("ignore_signature", ("update", "force_update")),
        ("jpeg_quality", ("convert_to_jpeg")),
        ("keep", ("cleanup")),
        ("missing", ("download_missing", "use_photos_export")),
        ("only_new", ("update", "force_update")),
        ("update_errors", ("update")),
    ]
    try:
        cfg.validate(exclusive=exclusive_options, dependent=dependent_options, cli=True)
    except ConfigOptionsInvalidError as e:
        rich_click_echo(
            f"[error]Incompatible export options: {e.message}",
            err=True,
        )
        sys.exit(1)

    if config_only and not save_config:
        rich_click_echo(
            "[error]Incompatible export options: --config-only must be used with --save-config",
            err=True,
        )
        sys.exit(1)

    if all(x in [s.lower() for s in sidecar] for x in ["json", "exiftool"]):
        rich_click_echo(
            "[error]Incompatible export options:: cannot use --sidecar json with --sidecar exiftool due to name collisions",
            err=True,
        )
        sys.exit(1)

    if xattr_template:
        for attr, _ in xattr_template:
            if attr not in EXTENDED_ATTRIBUTE_NAMES:
                rich_click_echo(
                    f"[error]Invalid attribute '{attr}' for --xattr-template; "
                    f"valid values are {', '.join(EXTENDED_ATTRIBUTE_NAMES_QUOTED)}",
                    err=True,
                )
                sys.exit(1)

    if save_config:
        verbose(f"Saving options to config file '[filepath]{save_config}'")
        cfg.write_to_file(save_config)
        if config_only:
            rich_echo(f"Saved config file to '[filepath]{save_config}'")
            sys.exit(0)

    # set defaults for options that need them
    jpeg_quality = DEFAULT_JPEG_QUALITY if jpeg_quality is None else jpeg_quality
    edited_suffix = DEFAULT_EDITED_SUFFIX if edited_suffix is None else edited_suffix
    original_suffix = (
        DEFAULT_ORIGINAL_SUFFIX if original_suffix is None else original_suffix
    )
    preview_suffix = (
        DEFAULT_PREVIEW_SUFFIX if preview_suffix is None else preview_suffix
    )
    retry = retry or 0

    if not os.path.isdir(dest):
        rich_click_echo(f"[error]DEST {dest} must be valid path", err=True)
        sys.exit(1)

    dest = str(pathlib.Path(dest).resolve())

    if report:
        report = render_and_validate_report(report, exiftool_path, dest)
        report_writer = export_report_writer_factory(report, append)
    else:
        report_writer = ReportWriterNoOp()

    # if use_photokit and not check_photokit_authorization():
    #     click.echo(
    #         "Requesting access to use your Photos library. Click 'OK' on the dialog box to grant access."
    #     )
    #     request_photokit_authorization()
    #     click.confirm("Have you granted access?")
    #     if not check_photokit_authorization():
    #         click.echo(
    #             "Failed to get access to the Photos library which is needed with `--use-photokit`."
    #         )
    #         return

    # initialize export flags
    # by default, will export all versions of photos unless skip flag is set
    (export_edited, export_bursts, export_live, export_raw) = [
        not x for x in [skip_edited, skip_bursts, skip_live, skip_raw]
    ]

    # verify exiftool installed and in path if path not provided and exiftool will be used
    # NOTE: this won't catch use of {exiftool:} in a template
    # but those will raise error during template eval if exiftool path not set
    if (
        any([exiftool, exiftool_merge_keywords, exiftool_merge_persons])
        and not exiftool_path
    ):
        try:
            exiftool_path = get_exiftool_path()
        except FileNotFoundError:
            rich_click_echo(
                "[error]Could not find exiftool. Please download and install"
                " from https://exiftool.org/",
                err=True,
            )
            ctx.exit(1)

    if any([exiftool, exiftool_merge_keywords, exiftool_merge_persons]):
        verbose(f"exiftool path: [filepath]{exiftool_path}")

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(*photos_library, db, cli_db)
    if not db:
        rich_click_echo(get_help_msg(export), err=True)
        rich_click_echo(
            "\n\nLocated the following Photos library databases: ", err=True
        )
        _list_libraries()
        return

    # sanity check exportdb
    if exportdb and exportdb != OSXPHOTOS_EXPORT_DB:
        if pathlib.Path(pathlib.Path(dest) / OSXPHOTOS_EXPORT_DB).exists():
            rich_click_echo(
                f"[warning]Warning: export database is '{exportdb}' but found '{OSXPHOTOS_EXPORT_DB}' in {dest}; using '{exportdb}'",
                err=True,
            )
        if pathlib.Path(exportdb).resolve().parent != pathlib.Path(dest):
            rich_click_echo(
                f"[warning]Warning: export database '{pathlib.Path(exportdb).resolve()}' is in a different directory than export destination '{dest}'",
                err=True,
            )

    # open export database
    export_db_path = exportdb or os.path.join(dest, OSXPHOTOS_EXPORT_DB)

    # check that export isn't in the parent or child of a previously exported library
    other_db_files = find_files_in_branch(dest, OSXPHOTOS_EXPORT_DB)
    if other_db_files:
        rich_click_echo(
            "[warning]WARNING: found other export database files in this destination directory branch.  "
            + "This likely means you are attempting to export files into a directory "
            + "that is either the parent or a child directory of a previous export. "
            + "Proceeding may cause your exported files to be overwritten.",
            err=True,
        )
        rich_click_echo(
            f"You are exporting to {dest}, found {OSXPHOTOS_EXPORT_DB} files in:"
        )
        for other_db in other_db_files:
            rich_click_echo(f"{other_db}")
        if not click.confirm("Do you want to continue?"):
            sys.exit(1)

    if dry_run:
        export_db = ExportDBInMemory(dbfile=export_db_path, export_dir=dest)
        fileutil = FileUtilNoOp
    else:
        export_db = (
            ExportDBInMemory(dbfile=export_db_path, export_dir=dest)
            if ramdb
            else ExportDB(dbfile=export_db_path, export_dir=dest)
        )
        if alt_copy or not is_macos or (exiftool and is_mounted_volume(dest)):
            # if alt_copy or not on macOS, use shutil for copying files
            # also, if destination appears to be on a mounted volume and using exiftool, use shutil
            # as the copy used in FileUtilMacOS may cause exiftool to fail if permissions are wrong
            # this shouldn't impact performance as exiftool removes the benefit of copy-on-write
            fileutil = FileUtilShUtil
        else:
            # on macOS, FileUtilMacOS will take advantage of copy-on-write for APFS volumes
            fileutil = FileUtilMacOS

    if verbose:
        if export_db.was_created:
            verbose(f"Created export database [filepath]{export_db_path}")
        else:
            verbose(f"Using export database [filepath]{export_db_path}")
        upgraded = export_db.was_upgraded
        if upgraded:
            verbose(
                f"Upgraded export database [filepath]{export_db_path}[/] from version [num]{upgraded[0]}[/] to [num]{upgraded[1]}[/]"
            )

    # save config to export_db
    export_db.set_config(cfg.write_to_str())

    query_kwargs = locals()
    # skip missing bursts if using --download-missing by itself as AppleScript otherwise causes errors
    query_kwargs["missing_bursts"] = (
        (download_missing and use_photokit) or not download_missing,
    )
    query_kwargs["burst_photos"] = export_bursts
    query_options = query_options_from_kwargs(**query_kwargs)

    if is_iphoto_library(db):
        photosdb = osxphotos.iPhotoDB(
            dbfile=db, verbose=verbose, exiftool=exiftool_path, rich=False
        )
    else:
        photosdb = osxphotos.PhotosDB(
            dbfile=db, verbose=verbose, exiftool=exiftool_path, rich=True
        )

    # enable beta features if requested
    photosdb._beta = beta

    try:
        photos = photosdb.query(query_options)
    except ValueError as e:
        if "Invalid query_eval CRITERIA:" in str(e):
            msg = str(e).split(":")[1]
            raise click.BadOptionUsage(
                "query_eval", f"Invalid query-eval CRITERIA: {msg}"
            )
        else:
            raise ValueError(e)

    if skip_uuid:
        photos = [p for p in photos if p.uuid not in skip_uuid]

    if skip_uuid_from_file:
        skip_uuid_list = load_uuid_from_file(skip_uuid_from_file)
        photos = [p for p in photos if p.uuid not in skip_uuid_list]

    if photos and only_new:
        # ignore previously exported files
        previous_uuids = {uuid: 1 for uuid in export_db.get_previous_uuids()}
        photos = [p for p in photos if p.uuid not in previous_uuids]

    # store results of export
    results = ExportResults()

    if photos:
        num_photos = len(photos)
        photo_str = pluralize(num_photos, "photo", "photos")
        rich_echo(
            f"Exporting [num]{num_photos}[/num] {photo_str} to [filepath]{dest}[/]..."
        )
        start_time = time.perf_counter()
        # though the command line option is current_name, internally all processing
        # logic uses original_name which is the boolean inverse of current_name
        # because the original code used --original-name as an option
        # appears to be unused but is used in export_photo and passed via kwargs
        original_name = not current_name

        # set up for --add-export-to-album if needed
        album_export = (
            PhotosAlbum(add_exported_to_album, verbose=verbose)
            if add_exported_to_album
            else None
        )
        album_skipped = (
            PhotosAlbum(add_skipped_to_album, verbose=verbose)
            if add_skipped_to_album
            else None
        )
        album_missing = (
            PhotosAlbum(add_missing_to_album, verbose=verbose)
            if add_missing_to_album
            else None
        )

        def cleanup_lock_files():
            """Cleanup lock files"""
            if not under_test():
                verbose("Cleaning up lock files")
            if dry_run:
                return
            for lock_file in pathlib.Path(dest).rglob("*.osxphotos.lock"):
                try:
                    lock_file.unlink()
                except Exception as e:
                    logger.debug(f"Error removing lock file {lock_file}: {e}")

        atexit.register(cleanup_lock_files)

        photo_num = 0
        num_exported = 0
        limit_str = f" (limit = [num]{limit}[/num])" if limit else ""
        # hack to avoid passing all the options to export_photo
        kwargs = {
            k: v
            for k, v in locals().items()
            if k in inspect.getfullargspec(export_photo).args
        }
        kwargs["export_dir"] = dest
        kwargs["export_preview"] = preview
        with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
            task = progress.add_task(
                f"Exporting [num]{num_photos}[/] photos{limit_str}", total=num_photos
            )
            for p in photos:
                photo_num += 1
                kwargs["photo"] = p
                kwargs["photo_num"] = photo_num
                export_results = export_photo(**kwargs)

                # generate custom sidecars if needed
                if sidecar_template:
                    export_results += generate_user_sidecar(
                        photo=p,
                        export_results=export_results,
                        sidecar_template=sidecar_template,
                        exiftool_path=exiftool_path,
                        export_dir=dest,
                        dry_run=dry_run,
                        verbose=verbose,
                    )

                # run post functions
                if run_results := run_post_function(
                    photo=p,
                    post_function=post_function,
                    export_results=export_results,
                    verbose=verbose,
                    dry_run=dry_run,
                ):
                    export_results += run_results

                # run post command
                run_post_command(
                    photo=p,
                    post_command=post_command,
                    export_results=export_results,
                    export_dir=dest,
                    dry_run=dry_run,
                    exiftool_path=exiftool_path,
                    on_error=post_command_error,
                    verbose=verbose,
                )

                if album_export and export_results.exported:
                    try:
                        album_export.add(p)
                        export_results.exported_album = [
                            (filename, album_export.name)
                            for filename in export_results.exported
                        ]
                    except Exception as e:
                        click.secho(
                            f"Error adding photo {p.original_filename} ({p.uuid}) to album {album_export.name}: {e}",
                            fg=CLI_COLOR_ERROR,
                            err=True,
                        )

                if album_skipped and export_results.skipped:
                    try:
                        album_skipped.add(p)
                        export_results.skipped_album = [
                            (filename, album_skipped.name)
                            for filename in export_results.skipped
                        ]
                    except Exception as e:
                        click.secho(
                            f"Error adding photo {p.original_filename} ({p.uuid}) to album {album_skipped.name}: {e}",
                            fg=CLI_COLOR_ERROR,
                            err=True,
                        )

                if album_missing and export_results.missing:
                    try:
                        album_missing.add(p)
                        export_results.missing_album = [
                            (filename, album_missing.name)
                            for filename in export_results.missing
                        ]
                    except Exception as e:
                        click.secho(
                            f"Error adding photo {p.original_filename} ({p.uuid}) to album {album_missing.name}: {e}",
                            fg=CLI_COLOR_ERROR,
                            err=True,
                        )

                results += export_results

                # all photo files (not including sidecars) that are part of this export set
                # used below for applying Finder tags, etc.
                photo_files = set(
                    export_results.exported
                    + export_results.new
                    + export_results.updated
                    + export_results.exif_updated
                    + export_results.converted_to_jpeg
                    + export_results.skipped
                )

                if finder_tag_keywords or finder_tag_template:
                    if dry_run:
                        for filepath in photo_files:
                            verbose(f"Writing Finder tags to [filepath]{filepath}[/]")
                    else:
                        tags_written, tags_skipped = write_finder_tags(
                            p,
                            photo_files,
                            keywords=finder_tag_keywords,
                            keyword_template=keyword_template,
                            album_keyword=album_keyword,
                            person_keyword=person_keyword,
                            exiftool_merge_keywords=exiftool_merge_keywords,
                            finder_tag_template=finder_tag_template,
                            strip=strip,
                            export_dir=dest,
                            verbose=verbose,
                        )
                        export_results.xattr_written.extend(tags_written)
                        export_results.xattr_skipped.extend(tags_skipped)
                        results.xattr_written.extend(tags_written)
                        results.xattr_skipped.extend(tags_skipped)

                if xattr_template:
                    if dry_run:
                        for filepath in photo_files:
                            verbose(
                                f"Writing extended attributes to [filepath]{filepath}[/]"
                            )
                    else:
                        xattr_written, xattr_skipped = write_extended_attributes(
                            p,
                            photo_files,
                            xattr_template,
                            strip=strip,
                            export_dir=dest,
                            verbose=verbose,
                        )
                        export_results.xattr_written.extend(xattr_written)
                        export_results.xattr_skipped.extend(xattr_skipped)
                        results.xattr_written.extend(xattr_written)
                        results.xattr_skipped.extend(xattr_skipped)

                report_writer.write(export_results)

                if print_template:
                    options = RenderOptions(export_dir=dest)
                    for template in print_template:
                        rendered_templates, unmatched = p.render_template(
                            template,
                            options,
                        )
                        if unmatched:
                            rich_click_echo(
                                f"[warning]Unmatched template field: {unmatched}[/]"
                            )
                        for rendered_template in rendered_templates:
                            if not rendered_template:
                                continue
                            rich_click_echo(rendered_template)

                progress.advance(task)

                # handle limit
                if export_results.exported:
                    # if any photos were exported, increment num_exported used by limit
                    # limit considers each PhotoInfo object as a single photo even if multiple files are exported
                    num_exported += 1
                if limit and num_exported >= limit:
                    # advance progress to end
                    progress.advance(task, num_photos - photo_num)
                    break

        photo_str_total = pluralize(len(photos), "photo", "photos")
        if update or force_update:
            summary = (
                f"Processed: [num]{len(photos)}[/] {photo_str_total}, "
                f"exported: [num]{len(results.new)}[/], "
                f"updated: [num]{len(results.updated)}[/], "
                f"skipped: [num]{len(results.skipped)}[/], "
                f"updated EXIF data: [num]{len(results.exif_updated)}[/], "
            )
        else:
            summary = (
                f"Processed: [num]{len(photos)}[/] {photo_str_total}, "
                f"exported: [num]{len(results.exported)}[/], "
            )
        summary += f"missing: [num]{len(results.missing)}[/], "
        summary += f"error: [num]{len(results.error)}[/]"
        if touch_file:
            summary += f", touched date: [num]{len(results.touched)}[/]"
        if limit:
            summary += f", limit: [num]{num_exported}[/]/[num]{limit}[/] exported"
        rich_echo(summary)
        stop_time = time.perf_counter()
        rich_echo(f"Elapsed time: [time]{format_sec_to_hhmmss(stop_time-start_time)}")
    else:
        rich_echo("Did not find any photos to export")

    # cleanup files and do report if needed
    if cleanup:
        db_file = str(pathlib.Path(export_db_path).resolve())
        db_files = [db_file, db_file + "-wal", db_file + "-shm"]
        keep_file = str(pathlib.Path(dest) / ".osxphotos_keep")
        all_files = (
            results.exported
            + results.skipped
            + results.exif_updated
            + results.touched
            + results.converted_to_jpeg
            + results.aae_written
            + results.sidecar_json_written
            + results.sidecar_json_skipped
            + results.sidecar_exiftool_written
            + results.sidecar_exiftool_skipped
            + results.sidecar_xmp_written
            + results.sidecar_xmp_skipped
            + results.sidecar_user_written
            + results.sidecar_user_skipped
            + results.user_written
            + results.user_skipped
            # include missing so a file that was already in export directory
            # but was missing on --update doesn't get deleted
            # (better to have old version than none)
            + results.missing
            # include files that have error in case they exist from previous export
            + [r[0] for r in results.error]
            # don't delete export database files
            + db_files
            # include the .osxphotos_keep file
            + [keep_file]
        )

        # if --report, add report file to keep list to prevent it from being deleted
        if report:
            all_files.append(report)

        # gather any files that should be kept from both .osxphotos_keep and --keep
        dirs_to_keep = []
        files_to_keep, dirs_to_keep = collect_files_to_keep(keep, dest)
        all_files += files_to_keep

        rich_echo(f"Cleaning up [filepath]{dest}")
        cleaned_files, cleaned_dirs = cleanup_files(
            dest, all_files, dirs_to_keep, fileutil, verbose=verbose
        )
        file_str = "files" if len(cleaned_files) != 1 else "file"
        dir_str = "directories" if len(cleaned_dirs) != 1 else "directory"

        rich_echo(
            f"Deleted: [num]{len(cleaned_files)}[/num] {file_str}, [num]{len(cleaned_dirs)}[/num] {dir_str}"
        )

        report_writer.write(
            ExportResults(deleted_files=cleaned_files, deleted_directories=cleaned_dirs)
        )

        results.deleted_files = cleaned_files
        results.deleted_directories = cleaned_dirs

    # store results so they can be used by `osxphotos exportdb --report`
    export_db.set_export_results(results)

    if report:
        verbose(f"Wrote export report to [filepath]{report}")
        report_writer.close()

    # close export_db and write changes if needed
    if ramdb and not dry_run:
        verbose(f"Writing export database changes back to [filepath]{export_db.path}")
        export_db.write_to_disk()
    export_db.close()


def export_photo(
    photo=None,
    dest=None,
    verbose=None,
    export_by_date=None,
    export_aae=None,
    sidecar=None,
    sidecar_drop_ext=False,
    update=None,
    force_update=None,
    ignore_signature=None,
    export_as_hardlink=None,
    overwrite=None,
    export_edited=None,
    skip_original_if_edited=None,
    original_name=None,
    export_live=None,
    download_missing=None,
    exiftool=None,
    exiftool_merge_keywords=False,
    exiftool_merge_persons=False,
    directory=None,
    favorite_rating=False,
    filename_template=None,
    export_raw=None,
    album_keyword=None,
    person_keyword=None,
    keyword_template=None,
    description_template=None,
    export_db=None,
    fileutil=FileUtilShUtil,
    dry_run=None,
    touch_file=None,
    edited_suffix="_edited",
    original_suffix="",
    use_photos_export=False,
    convert_to_jpeg=False,
    jpeg_quality=1.0,
    ignore_date_modified=False,
    use_photokit=False,
    exiftool_option=None,
    strip=False,
    jpeg_ext=None,
    replace_keywords=False,
    retry=0,
    export_dir=None,
    export_preview=False,
    preview_suffix=None,
    preview_if_missing=False,
    photo_num=1,
    num_photos=1,
    tmpdir=None,
    update_errors=False,
) -> ExportResults:
    """Helper function for export that does the actual export

    Args:
        photo: PhotoInfo object
        dest: destination path as string
        album_keyword: bool; if True, exports album names as keywords in metadata
        convert_to_jpeg: bool; if True, converts non-jpeg images to jpeg
        description_template: str; optional template string that will be rendered for use as photo description
        directory: template used to determine output directory
        download_missing: attempt download of missing iCloud photos
        dry_run: bool; if True, doesn't actually export or update any files
        exiftool_merge_keywords: bool; if True, merged keywords found in file's exif data (requires exiftool)
        exiftool_merge_persons: bool; if True, merged persons found in file's exif data (requires exiftool)
        exiftool_option: optional list flags (e.g. ["-m", "-F"]) to pass to exiftool
        exiftool: bool; use exiftool to write EXIF metadata directly to exported photo
        export_as_hardlink: bool; hardlink files instead of copying them
        export_by_date: bool; create export folder in form dest/YYYY/MM/DD
        export_db: export database instance compatible with ExportDB_ABC
        export_dir: top-level export directory for {export_dir} template
        export_edited: bool; if True exports edited version of photo if there is one
        export_live: bool; also export live video component if photo is a live photo; live video will have same name as photo but with .mov extension
        export_preview: export the preview image generated by Photos
        export_raw: bool; if True exports raw image associate with the photo
        favorite_rating: bool; if True, set XMP:Rating=5 for favorite images and XMP:Rating=0 for non-favorites
        filename_template: template use to determine output file
        fileutil: file util class compatible with FileUtilABC
        force_update: bool, only export updated photos but trigger export even if only metadata has changed
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
        jpeg_ext: if not None, specify the extension to use for all JPEG images on export
        jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
        keyword_template: list of strings; if provided use rendered template strings as keywords
        num_photos: int, total number of photos that will be exported
        original_name: bool; use original filename instead of current filename
        overwrite: bool; overwrite dest file if it already exists
        person_keyword: bool; if True, exports person names as keywords in metadata
        photo_num: int, which number photo in total of num_photos is being exported
        preview_if_missing: bool, export preview if original is missing
        preview_suffix: str, template to use as suffix for preview images
        replace_keywords: if True, --keyword-template replaces keywords instead of adding keywords
        retry: retry up to retry # of times if there's an error
        export_aae: bool; if True, will also save adjustments
        sidecar_drop_ext: bool; if True, drops photo extension from sidecar name
        sidecar: list zero, 1 or 2 of ["json","xmp"] of sidecar variety to export
        skip_original_if_edited: bool; if True does not export original if photo has been edited
        touch_file: bool; sets file's modification time to match photo date
        update: bool, only export updated photos
        update_errors: bool, attempt to re-export photos that previously produced errors even if they otherwise would not be exported
        use_photos_export: bool; if True forces the use of AppleScript to export even if photo not missing
        verbose: callable for verbose output
        tmpdir: optional str; temporary directory to use for export

    Returns:
        list of path(s) of exported photo or None if photo was missing

    Raises:
        ValueError on invalid filename_template
    """
    export_original = not (skip_original_if_edited and photo.hasadjustments)

    # can't export edited if photo doesn't have edited versions
    export_edited = export_edited if photo.hasadjustments else False

    # slow_mo photos will always have hasadjustments=True even if not edited
    if photo.hasadjustments and photo.path_edited is None:
        if photo.slow_mo:
            export_original = True
            export_edited = False
        elif not download_missing:
            # requested edited version but it's missing, download original
            export_original = True
            export_edited = False
            verbose(
                f"Edited file for [filename]{photo.original_filename}[/] is missing, exporting original"
            )

    # check for missing photos before downloading
    missing_original = False
    missing_edited = False
    if download_missing:
        if (
            (photo.ismissing or photo.path is None)
            and not photo.iscloudasset
            and not photo.incloud
        ):
            missing_original = True
        if (
            photo.hasadjustments
            and photo.path_edited is None
            and not photo.iscloudasset
            and not photo.incloud
        ):
            missing_edited = True
    else:
        if photo.ismissing or photo.path is None:
            missing_original = True
        if photo.hasadjustments and photo.path_edited is None:
            missing_edited = True

    sidecar = [s.lower() for s in sidecar]
    sidecar_flags = 0
    if "json" in sidecar:
        sidecar_flags |= SIDECAR_JSON
    if "xmp" in sidecar:
        sidecar_flags |= SIDECAR_XMP
    if "exiftool" in sidecar:
        sidecar_flags |= SIDECAR_EXIFTOOL

    rendered_suffix = _render_suffix_template(
        original_suffix,
        "original_suffix",
        "--original-suffix",
        strip,
        dest,
        photo,
        export_db,
    )
    rendered_preview_suffix = _render_suffix_template(
        preview_suffix,
        "preview_suffix",
        "--preview-suffix",
        strip,
        dest,
        photo,
        export_db,
    )

    results = ExportResults()
    dest_paths = get_dirnames_from_template(
        photo,
        directory,
        export_by_date,
        dest,
        dry_run,
        strip=strip,
        edited=False,
        export_db=export_db,
    )
    for dest_path in dest_paths:
        filenames = get_filenames_from_template(
            photo,
            filename_template,
            dest,
            dest_path,
            original_name,
            strip=strip,
            export_db=export_db,
        )

        for filename in filenames:
            original_filename = pathlib.Path(filename)
            file_ext = original_filename.suffix
            if photo.isphoto and (jpeg_ext or convert_to_jpeg):
                # change the file extension to correct jpeg extension if needed
                file_ext = (
                    "." + jpeg_ext
                    if jpeg_ext
                    and (photo.uti_original == "public.jpeg" or convert_to_jpeg)
                    else ".jpeg"
                    if convert_to_jpeg and photo.uti_original != "public.jpeg"
                    else original_filename.suffix
                )
            original_filename = (
                original_filename.parent
                / f"{original_filename.stem}{rendered_suffix}{file_ext}"
            )
            original_filename = str(original_filename)

            verbose(
                f"Exporting [filename]{photo.original_filename}[/] ([filename]{photo.filename}[/]) ([count]{photo_num}/{num_photos}[/])"
            )

            results += export_photo_to_directory(
                album_keyword=album_keyword,
                convert_to_jpeg=convert_to_jpeg,
                description_template=description_template,
                dest_path=dest_path,
                dest=dest,
                download_missing=download_missing,
                dry_run=dry_run,
                edited=False,
                exiftool_merge_keywords=exiftool_merge_keywords,
                exiftool_merge_persons=exiftool_merge_persons,
                exiftool_option=exiftool_option,
                exiftool=exiftool,
                export_as_hardlink=export_as_hardlink,
                export_db=export_db,
                export_dir=export_dir,
                export_live=export_live,
                export_original=export_original,
                export_preview=export_preview,
                export_raw=export_raw,
                favorite_rating=favorite_rating,
                filename=original_filename,
                fileutil=fileutil,
                force_update=force_update,
                ignore_date_modified=ignore_date_modified,
                ignore_signature=ignore_signature,
                jpeg_ext=jpeg_ext,
                jpeg_quality=jpeg_quality,
                keyword_template=keyword_template,
                missing=missing_original,
                overwrite=overwrite,
                person_keyword=person_keyword,
                photo=photo,
                preview_if_missing=preview_if_missing,
                preview_suffix=rendered_preview_suffix,
                replace_keywords=replace_keywords,
                retry=retry,
                export_aae=export_aae,
                sidecar_drop_ext=sidecar_drop_ext,
                sidecar_flags=sidecar_flags,
                touch_file=touch_file,
                update=update,
                update_errors=update_errors,
                use_photos_export=use_photos_export,
                use_photokit=use_photokit,
                verbose=verbose,
                tmpdir=tmpdir,
            )

    if export_edited and photo.hasadjustments:
        dest_paths = get_dirnames_from_template(
            photo,
            directory,
            export_by_date,
            dest,
            dry_run,
            strip=strip,
            edited=True,
            export_db=export_db,
        )
        for dest_path in dest_paths:
            # if export-edited, also export the edited version
            edited_filenames = get_filenames_from_template(
                photo,
                filename_template,
                dest,
                dest_path,
                original_name,
                strip=strip,
                edited=True,
                export_db=export_db,
            )
            for edited_filename in edited_filenames:
                edited_filename = pathlib.Path(edited_filename)
                # verify the photo has adjustments and valid path to avoid raising an exception
                edited_ext = (
                    # rare cases on Photos <= 4 that uti_edited is None
                    "." + get_preferred_uti_extension(photo.uti_edited)
                    if photo.uti_edited
                    else pathlib.Path(photo.path_edited).suffix
                    if photo.path_edited
                    else pathlib.Path(photo.filename).suffix
                )

                if (
                    photo.isphoto
                    and jpeg_ext
                    and edited_ext.lower() in [".jpg", ".jpeg"]
                ):
                    edited_ext = "." + jpeg_ext

                # Big Sur uses .heic for some edited photos so need to check
                # if extension isn't jpeg/jpg and using --convert-to-jpeg
                if (
                    photo.isphoto
                    and convert_to_jpeg
                    and edited_ext.lower() not in [".jpg", ".jpeg"]
                ):
                    edited_ext = "." + jpeg_ext if jpeg_ext else ".jpeg"

                rendered_edited_suffix = _render_suffix_template(
                    edited_suffix,
                    "edited_suffix",
                    "--edited-suffix",
                    strip,
                    dest,
                    photo,
                    export_db,
                )
                edited_filename = (
                    f"{edited_filename.stem}{rendered_edited_suffix}{edited_ext}"
                )

                verbose(
                    f"Exporting edited version of [filename]{photo.original_filename}[/filename] ([filename]{photo.filename}[/filename])"
                )

                results += export_photo_to_directory(
                    album_keyword=album_keyword,
                    convert_to_jpeg=convert_to_jpeg,
                    description_template=description_template,
                    dest_path=dest_path,
                    dest=dest,
                    download_missing=download_missing,
                    dry_run=dry_run,
                    edited=True,
                    exiftool_merge_keywords=exiftool_merge_keywords,
                    exiftool_merge_persons=exiftool_merge_persons,
                    exiftool_option=exiftool_option,
                    exiftool=exiftool,
                    export_as_hardlink=export_as_hardlink,
                    export_db=export_db,
                    export_dir=export_dir,
                    export_live=export_live,
                    export_original=False,
                    export_preview=not export_original and export_preview,
                    export_raw=not export_original and export_raw,
                    favorite_rating=favorite_rating,
                    filename=edited_filename,
                    fileutil=fileutil,
                    force_update=force_update,
                    ignore_date_modified=ignore_date_modified,
                    ignore_signature=ignore_signature,
                    jpeg_ext=jpeg_ext,
                    jpeg_quality=jpeg_quality,
                    keyword_template=keyword_template,
                    missing=missing_edited,
                    overwrite=overwrite,
                    person_keyword=person_keyword,
                    photo=photo,
                    preview_if_missing=preview_if_missing,
                    preview_suffix=rendered_preview_suffix,
                    replace_keywords=replace_keywords,
                    retry=retry,
                    export_aae=export_aae,
                    sidecar_drop_ext=sidecar_drop_ext,
                    sidecar_flags=sidecar_flags if not export_original else 0,
                    touch_file=touch_file,
                    update=update,
                    update_errors=update_errors,
                    use_photos_export=use_photos_export,
                    use_photokit=use_photokit,
                    verbose=verbose,
                    tmpdir=tmpdir,
                )

    return results


def _render_suffix_template(
    suffix_template, var_name, option_name, strip, dest, photo, export_db
):
    """render suffix template

    Returns:
        rendered template
    """
    if not suffix_template:
        return ""

    try:
        options = RenderOptions(filename=True, export_dir=dest)
        rendered_suffix, unmatched = photo.render_template(suffix_template, options)
    except ValueError as e:
        raise click.BadOptionUsage(
            var_name,
            f"Invalid template for {option_name} '{suffix_template}': {e}",
        )
    if not rendered_suffix or unmatched:
        raise click.BadOptionUsage(
            var_name,
            f"Invalid template for {option_name} '{suffix_template}': results={rendered_suffix} unknown field={unmatched}",
        )
    if len(rendered_suffix) > 1:
        raise click.BadOptionUsage(
            var_name,
            f"Invalid template for {option_name}: may not use multi-valued templates: '{suffix_template}': results={rendered_suffix}",
        )

    if strip:
        rendered_suffix[0] = rendered_suffix[0].strip()

    return rendered_suffix[0]


def export_photo_to_directory(
    album_keyword,
    convert_to_jpeg,
    description_template,
    dest_path,
    dest,
    download_missing,
    dry_run,
    edited,
    exiftool_merge_keywords,
    exiftool_merge_persons,
    exiftool_option,
    exiftool,
    export_as_hardlink,
    export_db,
    export_dir,
    export_live,
    export_original,
    export_preview,
    export_raw,
    favorite_rating,
    filename,
    fileutil,
    force_update,
    ignore_date_modified,
    ignore_signature,
    jpeg_ext,
    jpeg_quality,
    keyword_template,
    missing,
    overwrite,
    person_keyword,
    photo,
    preview_if_missing,
    preview_suffix,
    replace_keywords,
    retry,
    export_aae,
    sidecar_drop_ext,
    sidecar_flags,
    touch_file,
    update,
    update_errors,
    use_photos_export,
    use_photokit,
    verbose,
    tmpdir,
) -> ExportResults:
    """Export photo to directory dest_path"""

    results = ExportResults()

    # don't try to export photos in the trash if they're missing
    photo_path = photo.path if export_original else photo.path_edited
    if photo.intrash and not photo_path and not preview_if_missing:
        # skip deleted files if they're missing
        # as AppleScript/PhotoKit cannot export deleted photos
        verbose(
            f"Skipping missing deleted photo {photo.original_filename} ({photo.uuid})"
        )
        results.missing.append(str(pathlib.Path(dest_path) / filename))
        return results

    render_options = RenderOptions(export_dir=export_dir, dest_path=dest_path)

    if not export_original and not edited:
        verbose(f"Skipping original version of [filename]{photo.original_filename}")
        return results

    tries = 0
    while tries <= retry:
        tries += 1
        error = 0
        try:
            export_options = ExportOptions(
                convert_to_jpeg=convert_to_jpeg,
                description_template=description_template,
                download_missing=download_missing,
                dry_run=dry_run,
                edited=edited,
                exiftool=exiftool,
                exiftool_flags=exiftool_option,
                export_as_hardlink=export_as_hardlink,
                export_db=export_db,
                favorite_rating=favorite_rating,
                fileutil=fileutil,
                force_update=force_update,
                ignore_date_modified=ignore_date_modified,
                ignore_signature=ignore_signature,
                jpeg_ext=jpeg_ext,
                jpeg_quality=jpeg_quality,
                keyword_template=keyword_template,
                live_photo=export_live,
                merge_exif_keywords=exiftool_merge_keywords,
                merge_exif_persons=exiftool_merge_persons,
                overwrite=overwrite,
                preview=export_preview or (missing and preview_if_missing),
                preview_suffix=preview_suffix,
                raw_photo=export_raw,
                render_options=render_options,
                replace_keywords=replace_keywords,
                rich=True,
                export_aae=export_aae,
                sidecar=sidecar_flags,
                sidecar_drop_ext=sidecar_drop_ext,
                tmpdir=tmpdir,
                touch_file=touch_file,
                update=update,
                update_errors=update_errors,
                use_albums_as_keywords=album_keyword,
                use_persons_as_keywords=person_keyword,
                use_photokit=use_photokit,
                use_photos_export=use_photos_export,
                verbose=verbose,
            )
            exporter = PhotoExporter(photo)
            export_results = exporter.export(
                dest=dest_path, filename=filename, options=export_options
            )
            for warning_ in export_results.exiftool_warning:
                verbose(
                    f"[warning]exiftool warning for file {warning_[0]}: {warning_[1]}"
                )
            for error_ in export_results.exiftool_error:
                rich_echo_error(
                    f"[error]exiftool error for file {error_[0]}: {error_[1]}"
                )
            for error_ in export_results.error:
                rich_echo_error(
                    f"[error]Error exporting photo ({photo.uuid}: {photo.original_filename}) as {error_[0]}: {error_[1]}"
                )
                error += 1
            if not error or tries > retry:
                results += export_results
                break
            else:
                rich_echo(
                    f"Retrying export for photo ([uuid]{photo.uuid}[/uuid]: [filename]{photo.original_filename}[/filename])"
                )
        except Exception as e:
            if is_debug():
                # if debug mode, don't swallow the exceptions
                raise e
            rich_echo(
                f"[error]Error exporting photo ([uuid]{photo.uuid}[/uuid]: [filename]{photo.original_filename}[/filename]) as [filepath]{filename}[/filepath]: {e}",
                err=True,
            )
            if tries > retry:
                results.error.append((str(pathlib.Path(dest) / filename), str(e)))
                break
            else:
                rich_echo(
                    f"Retrying export for photo ([uuid]{photo.uuid}[/uuid]: [filename]{photo.original_filename}[/filename])"
                )

    if verbose:
        if update or force_update:
            for new in results.new:
                verbose(f"Exported new file [filepath]{new}")
            for updated in results.updated:
                verbose(f"Exported updated file [filepath]{updated}")
            for skipped in results.skipped:
                verbose(f"Skipped up to date file [filepath]{skipped}")
        else:
            for exported in results.exported:
                verbose(f"Exported [filepath]{exported}")
        for touched in results.touched:
            verbose(f"Touched date on file [filepath]{touched}")

    return results


def get_filenames_from_template(
    photo,
    filename_template,
    export_dir,
    dest_path,
    original_name,
    strip=False,
    edited=False,
    export_db=None,
):
    """get list of export filenames for a photo

    Args:
        photo: a PhotoInfo instance
        filename_template: a PhotoTemplate template string, may be None
        original_name: bool; if True, use photo's original filename instead of current filename
        dest_path: the path the photo will be exported to
        strip: if True, strips leading/trailing white space from resulting template
        edited: if True, sets {edited_version} field to True, otherwise it gets set to False; set if you want template evaluated for edited version

    Returns:
        list of filenames

    Raises:
        click.BadOptionUsage if template is invalid
    """
    if filename_template:
        photo_ext = pathlib.Path(photo.original_filename).suffix
        try:
            options = RenderOptions(
                path_sep="_",
                filename=True,
                edited_version=edited,
                export_dir=export_dir,
                dest_path=dest_path,
            )
            filenames, unmatched = photo.render_template(filename_template, options)
        except ValueError as e:
            raise click.BadOptionUsage(
                "filename_template", f"Invalid template '{filename_template}': {e}"
            )
        if not filenames or unmatched:
            raise click.BadOptionUsage(
                "filename_template",
                f"Invalid template '{filename_template}': unknown field={unmatched}",
            )
        filenames = [f"{file_}{photo_ext}" for file_ in filenames]
    else:
        filenames = (
            [photo.original_filename]
            if (original_name and (photo.original_filename is not None))
            else [photo.filename]
        )

    if strip:
        filenames = [filename.strip() for filename in filenames]
    filenames = [sanitize_filename(filename) for filename in filenames]

    return filenames


def get_dirnames_from_template(
    photo,
    directory,
    export_by_date,
    dest,
    dry_run,
    strip=False,
    edited=False,
    export_db=None,
):
    """get list of directories to export a photo into, creates directories if they don't exist

    Args:
        photo: a PhotoInstance object
        directory: a PhotoTemplate template string, may be None
        export_by_date: bool; if True, creates output directories in form YYYY-MM-DD
        dest: top-level destination directory
        dry_run: bool; if True, runs in dry-run mode and does not create output directories
        strip: if True, strips leading/trailing white space from resulting template
        edited: if True, sets {edited_version} field to True, otherwise it gets set to False; set if you want template evaluated for edited version

    Returns:
        list of export directories

    Raises:
        click.BadOptionUsage if template is invalid
    """

    if export_by_date:
        date_created = DateTimeFormatter(photo.date)
        dest_path = os.path.join(
            dest, date_created.year, date_created.mm, date_created.dd
        )
        if not (dry_run or os.path.isdir(dest_path)):
            os.makedirs(dest_path)
        dest_paths = [dest_path]
    elif directory:
        # got a directory template, render it and check results are valid
        try:
            options = RenderOptions(dirname=True, edited_version=edited)
            dirnames, unmatched = photo.render_template(directory, options)
        except ValueError as e:
            raise click.BadOptionUsage(
                "directory", f"Invalid template '{directory}': {e}"
            )
        if not dirnames or unmatched:
            raise click.BadOptionUsage(
                "directory",
                f"Invalid template '{directory}': unknown field={unmatched}",
            )

        dest_paths = []
        for dirname in dirnames:
            if strip:
                dirname = dirname.strip()
            dirname = sanitize_filepath(dirname)
            dest_path = os.path.join(dest, dirname)
            if not is_valid_filepath(dest_path):
                raise ValueError(f"Invalid file path: '{dest_path}'")
            if not dry_run and not os.path.isdir(dest_path):
                os.makedirs(dest_path)
            dest_paths.append(dest_path)
    else:
        dest_paths = [dest]
    return dest_paths


def find_files_in_branch(pathname, filename):
    """Search a directory branch to find file(s) named filename
        The branch searched includes all folders below pathname and
        the parent tree of pathname but not pathname itself.

        e.g. find filename in children folders and parent folders

    Args:
        pathname: str, full path of directory to search
        filename: str, filename to search for

    Returns: list of full paths to any matching files
    """

    pathname = pathlib.Path(pathname).resolve()
    files = []

    # walk down the tree
    for root, _, filenames in os.walk(pathname):
        # for directory in directories:
        for fname in filenames:
            if fname == filename and pathlib.Path(root) != pathname:
                files.append(os.path.join(root, fname))

    # walk up the tree
    path = pathlib.Path(pathname)
    for root in path.parents:
        filenames = os.listdir(root)
        for fname in filenames:
            filepath = os.path.join(root, fname)
            if fname == filename and os.path.isfile(filepath):
                files.append(os.path.join(root, fname))

    return files


def collect_files_to_keep(
    keep: Iterable[str], export_dir: str
) -> Tuple[List[str], List[str]]:
    """Collect all files to keep for --keep/--cleanup.

    Args:
        keep: Iterable of patterns to keep; each pattern is a pattern that follows gitignore syntax
        export_dir: the export directory which will be used to resolve paths when paths in keep are relative instead of absolute

    Returns:
        tuple of [files_to_keep], [dirs_to_keep]
    """
    export_dir = pathlib.Path(export_dir).expanduser()
    export_dir_str = str(export_dir)

    KEEP_RULEs = []

    # parse .osxphotos_keep file if it exists
    keep_file: pathlib.Path = export_dir / ".osxphotos_keep"
    if keep_file.is_file():
        for line in keep_file.read_text().splitlines():
            line = line.rstrip("\r\n")
            KEEP_RULEs.append(line)

    # parse any patterns passed via --keep
    # do this after the file so negations to the file could be applied via --keep
    for k in keep:
        if k.startswith(export_dir_str):
            # allow full path to be specified for keep (e.g. --keep /path/to/file)
            KEEP_RULEs.append(k.replace(export_dir_str, ""))
        else:
            KEEP_RULEs.append(k)

    if not KEEP_RULEs:
        return [], []

    # have some rules to apply
    matcher = osxphotos.gitignorefile.parse_pattern_list(KEEP_RULEs, export_dir)
    keepers = []
    keepers = [path for path in export_dir.rglob("*") if matcher(path)]
    files_to_keep = [str(k) for k in keepers if k.is_file()]
    dirs_to_keep = [str(k) for k in keepers if k.is_dir()]
    return files_to_keep, dirs_to_keep


def cleanup_files(dest_path, files_to_keep, dirs_to_keep, fileutil, verbose):
    """cleanup dest_path by deleting and files and empty directories
        not in files_to_keep

    Args:
        dest_path: path to directory to clean
        files_to_keep: list of full file paths to keep (not delete)
        dirs_to_keep: list of full dir paths to keep (not delete if they are empty)
        fileutil: FileUtil object
        verbose: verbose callable for printing verbose output

    Returns:
        tuple of (list of files deleted, list of directories deleted)
    """
    keepers = {
        normalize_fs_path(str(filename).lower()): 1 for filename in files_to_keep
    }

    deleted_files = []
    for p in pathlib.Path(dest_path).rglob("*"):
        if p.is_file() and normalize_fs_path(str(p).lower()) not in keepers:
            verbose(f"Deleting [filepath]{p}")
            try:
                fileutil.unlink(p)
                deleted_files.append(str(p))
            except OSError as e:
                # ignore errors deleting files, #987
                verbose(f"Error deleting file {p}: {e}")

    # delete empty directories
    deleted_dirs = []
    # walk directory tree bottom up and verify contents are empty
    for dirpath, _, _ in os.walk(dest_path, topdown=False):
        if dirpath in dirs_to_keep:
            continue
        if not list(pathlib.Path(dirpath).glob("*")):
            # directory and directory is empty
            verbose(f"Deleting empty directory {dirpath}")
            try:
                fileutil.rmdir(dirpath)
                deleted_dirs.append(str(dirpath))
            except OSError as e:
                # ignore errors deleting directories, #987
                verbose(f"Error deleting directory {dirpath}: {e}")

    return (deleted_files, deleted_dirs)


def write_finder_tags(
    photo,
    files,
    keywords=False,
    keyword_template=None,
    album_keyword=None,
    person_keyword=None,
    exiftool_merge_keywords=None,
    finder_tag_template=None,
    strip=False,
    export_dir=None,
    verbose=noop,
):
    """Write Finder tags (extended attributes) to files; only writes attributes if attributes on file differ from what would be written

    Args:
        photo: a PhotoInfo object
        files: list of file paths to write Finder tags to
        keywords: if True, sets Finder tags to all keywords including any evaluated from keyword_template, album_keyword, person_keyword, exiftool_merge_keywords
        keyword_template: list of keyword templates to evaluate for determining keywords
        album_keyword: if True, use album names as keywords
        person_keyword: if True, use person in image as keywords
        exiftool_merge_keywords: if True, include any keywords in the exif data of the source image as keywords
        finder_tag_template: list of templates to evaluate for determining Finder tags
        export_dir: value to use for {export_dir} template
        verbose: function to call to print verbose messages

    Returns:
        (list of file paths that were updated with new Finder tags, list of file paths skipped because Finder tags didn't need updating)
    """

    tags = []
    written = []
    skipped = []
    if keywords:
        # match whatever keywords would've been used in --exiftool or --sidecar
        export_options = ExportOptions(
            use_albums_as_keywords=album_keyword,
            use_persons_as_keywords=person_keyword,
            keyword_template=keyword_template,
            merge_exif_keywords=exiftool_merge_keywords,
            rich=True,
        )
        # TODO: Need a better way to do this
        # use photo.path as the source for EXIF if merge is used
        # this means that if file is not present (e.g. export done with photokit)
        # then the tags won't be available for merging
        exif = ExifWriter(photo).exiftool_dict(
            options=exif_options_from_options(export_options)
        )
        try:
            if exif["IPTC:Keywords"]:
                tags.extend(exif["IPTC:Keywords"])
        except KeyError:
            pass

    if finder_tag_template:
        rendered_tags = []
        for template_str in finder_tag_template:
            try:
                options = RenderOptions(
                    none_str=_OSXPHOTOS_NONE_SENTINEL,
                    path_sep="/",
                    export_dir=export_dir,
                )
                rendered, unmatched = photo.render_template(template_str, options)
            except ValueError as e:
                raise click.BadOptionUsage(
                    "finder_tag_template",
                    f"Invalid template for --finder-tag-template '{template_str}': {e}",
                )

            if unmatched:
                rich_echo(
                    f"[warning]Warning: unknown field for template: {template_str} unknown field = {unmatched}"
                )
            rendered_tags.extend(rendered)

        # filter out any template values that didn't match by looking for sentinel
        if strip:
            rendered_tags = [value.strip() for value in rendered_tags]

        rendered_tags = [
            value.replace(_OSXPHOTOS_NONE_SENTINEL, "") for value in rendered_tags
        ]
        tags.extend(rendered_tags)

    tags = [Tag(tag, 0) for tag in set(tags)]
    for f in files:
        md = OSXMetaData(f)
        if sorted(md.tags) != sorted(tags):
            verbose(f"Writing Finder tags to [filepath]{f}[/]")
            md.tags = tags
            written.append(f)
        else:
            verbose(f"Skipping Finder tags for [filepath]{f}[/]: nothing to do")
            skipped.append(f)

    return (written, skipped)


def write_extended_attributes(
    photo,
    files,
    xattr_template,
    strip=False,
    export_dir=None,
    verbose=noop,
):
    """Writes extended attributes to exported files

    Args:
        photo: a PhotoInfo object
        files: list of file paths to write extended attributes to
        xattr_template: list of tuples: (attribute name, attribute template)
        strip:   xattr_template: list of tuples: (attribute name, attribute template)
        export_dir: value to use for {export_dir} template
        verbose: function to call to print verbose messages

    Returns:
        tuple(list of file paths that were updated with new attributes, list of file paths skipped because attributes didn't need updating)
    """

    attributes = {}
    for xattr, template_str in xattr_template:
        try:
            options = RenderOptions(
                none_str=_OSXPHOTOS_NONE_SENTINEL, path_sep="/", export_dir=export_dir
            )
            rendered, unmatched = photo.render_template(template_str, options)
        except ValueError as e:
            raise click.BadOptionUsage(
                "xattr_template",
                f"Invalid template for --xattr-template '{template_str}': {e}",
            )
        if unmatched:
            rich_echo(
                f"[warning]Warning: unmatched template substitution for template: {template_str} unknown field={unmatched}"
            )

        # filter out any template values that didn't match by looking for sentinel
        if strip:
            rendered = [value.strip() for value in rendered]

        rendered = [value.replace(_OSXPHOTOS_NONE_SENTINEL, "") for value in rendered]

        try:
            attributes[xattr].extend(rendered)
        except KeyError:
            attributes[xattr] = rendered

    written = set()
    skipped = set()
    for f in files:
        md = OSXMetaData(f)
        for attr, value in attributes.items():
            attr_type = get_metadata_attribute_type(attr) or "str"
            if value:
                value = sorted(list(value)) if attr_type == "list" else ", ".join(value)
            file_value = md.get(attr)

            if file_value and attr_type == "lists":
                file_value = sorted(file_value)

            if (not file_value and not value) or file_value == value:
                # if both not set or both equal, nothing to do
                # get returns None if not set and value will be [] if not set so can't directly compare
                verbose(
                    f"Skipping extended attribute [bold]{attr}[/] for [filepath]{f}[/]: nothing to do"
                )
                skipped.add(f)
            else:
                verbose(
                    f"Writing extended attribute [bold]{attr}[/] to [filepath]{f}[/]"
                )
                md.set(attr, value)
                written.add(f)

    return list(written), [f for f in skipped if f not in written]


def run_post_function(
    photo: osxphotos.PhotoInfo,
    post_function: tuple[
        tuple[
            Callable[
                [osxphotos.PhotoInfo, ExportResults, Callable[[Any], None]],
                None | ExportResults,
            ],
            str,
        ],
        ...,
    ],
    export_results: ExportResults,
    verbose: Callable[[Any], None],
    dry_run: bool,
) -> ExportResults:
    """Run the --post-function functions"""
    returned_results = ExportResults()
    for function in post_function:
        # post function is tuple of (function, filename.py::function_name)
        verbose(f"Calling post-function [bold]{function[1]}")
        if not dry_run:
            try:
                if results := function[0](photo, export_results, verbose):
                    returned_results += results
            except Exception as e:
                rich_echo_error(
                    f"[error]Error running post-function [italic]{function[1]}[/italic]: {e}"
                )
                raise e
    return returned_results


def run_post_command(
    photo: osxphotos.PhotoInfo,
    post_command: tuple[tuple[str, str]],
    export_results: ExportResults,
    export_dir: str | pathlib.Path,
    dry_run: bool,
    exiftool_path: str,
    on_error: Literal["break", "continue"] | None,
    verbose: Callable[[Any], None],
):
    """Run --post-command commands"""
    # todo: pass in RenderOptions from export? (e.g. so it contains strip, etc?)

    for category, command_template in post_command:
        files = getattr(export_results, category)
        for f in files:
            # some categories, like error, return a tuple of (file, error str)
            if isinstance(f, tuple):
                f = f[0]
            render_options = RenderOptions(export_dir=export_dir, filepath=f)
            template = PhotoTemplate(photo, exiftool_path=exiftool_path)
            command, _ = template.render(command_template, options=render_options)
            command = command[0] if command else None
            if command:
                verbose(f'Running command: "{command}"')
                if not dry_run:
                    cwd = pathlib.Path(f).parent
                    run_error = None
                    run_results = None
                    try:
                        run_results = subprocess.run(command, shell=True, cwd=cwd)
                    except Exception as e:
                        run_error = e
                    finally:
                        returncode = run_results.returncode if run_results else None
                        if run_error or returncode:
                            # there was an error running the command
                            error_str = f'Error running command "{command}": return code: {returncode}, exception: {run_error}'
                            rich_echo_error(f"[error]{error_str}[/]")
                            if not on_error:
                                # no error handling specified, raise exception
                                raise RuntimeError(error_str)
                            if on_error == "break":
                                # break out of loop and return
                                return
                            # else on_error must be continue


def render_and_validate_report(report: str, exiftool_path: str, export_dir: str) -> str:
    """Render a report file template and validate the filename

    Args:
        report: the template string
        exiftool_path: the path to the exiftool binary
        export_dir: the export directory

    Returns:
        the rendered report filename

    Note:
        Exits with error if the report filename is invalid
    """
    # render report template and validate the filename
    template = PhotoTemplate(PhotoInfoNone(), exiftool_path=exiftool_path)
    render_options = RenderOptions(export_dir=export_dir)
    report_file, _ = template.render(report, options=render_options)
    report = report_file[0]

    if os.path.isdir(report):
        rich_click_echo(
            f"[error]Report '{report}' is a directory, must be file name",
            err=True,
        )
        sys.exit(1)

    return report


def get_metadata_attribute_type(attr: str) -> Optional[str]:
    """Get the type of a metadata attribute

    Args:
        attr: attribute name

    Returns:
        type of attribute as string or None if type is not known
    """
    if attr in MDITEM_ATTRIBUTE_SHORT_NAMES:
        attr = MDITEM_ATTRIBUTE_SHORT_NAMES[attr]
    return (
        "list"
        if attr in _TAGS_NAMES
        else MDITEM_ATTRIBUTE_DATA[attr]["python_type"]
        if attr in MDITEM_ATTRIBUTE_DATA
        else None
    )
