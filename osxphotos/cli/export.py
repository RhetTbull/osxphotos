"""export command for osxphotos CLI"""

import atexit
import cProfile
import csv
import io
import os
import pathlib
import pstats
import shlex
import subprocess
import sys
import time
from typing import Dict

import click
import osxmetadata

import osxphotos
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
    PROFILE_SORT_KEYS,
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
from osxphotos.debug import is_debug, set_debug
from osxphotos.exiftool import get_exiftool_path
from osxphotos.export_db import ExportDB, ExportDBInMemory
from osxphotos.fileutil import FileUtil, FileUtilNoOp
from osxphotos.path_utils import is_valid_filepath, sanitize_filename, sanitize_filepath
from osxphotos.photoexporter import ExportOptions, ExportResults, PhotoExporter
from osxphotos.photokit import (
    check_photokit_authorization,
    request_photokit_authorization,
)
from osxphotos.photosalbum import PhotosAlbum
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.queryoptions import QueryOptions
from osxphotos.uti import get_preferred_uti_extension
from osxphotos.utils import format_sec_to_hhmmss, normalize_fs_path

from .click_rich_echo import (
    rich_click_echo,
    rich_echo,
    rich_echo_error,
    set_rich_console,
    set_rich_theme,
    set_rich_timestamp,
)
from .color_themes import get_theme
from .common import (
    CLI_COLOR_ERROR,
    CLI_COLOR_WARNING,
    DB_ARGUMENT,
    DB_OPTION,
    DEBUG_OPTIONS,
    DELETED_OPTIONS,
    JSON_OPTION,
    OSXPHOTOS_CRASH_LOG,
    OSXPHOTOS_HIDDEN,
    QUERY_OPTIONS,
    get_photos_db,
    load_uuid_from_file,
    noop,
)
from .help import ExportCommand, get_help_msg
from .list import _list_libraries
from .param_types import ExportDBType, FunctionCall
from .rich_progress import rich_progress
from .verbose import get_verbose_console, time_stamp, verbose_print


@click.command(cls=ExportCommand)
@DB_OPTION
@click.option("--verbose", "-V", "verbose", is_flag=True, help="Print verbose output.")
@click.option("--timestamp", is_flag=True, help="Add time stamp to verbose output")
@click.option(
    "--no-progress", is_flag=True, help="Do not display progress bar during export."
)
@QUERY_OPTIONS
@click.option(
    "--missing",
    is_flag=True,
    help="Export only photos missing from the Photos library; must be used with --download-missing.",
)
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
)
@click.option(
    "--directory",
    metavar="DIRECTORY",
    default=None,
    help="Optional template for specifying name of output directory in the form '{name,DEFAULT}'. "
    "See below for additional details on templating system.",
)
@click.option(
    "--filename",
    "filename_template",
    metavar="FILENAME",
    default=None,
    help="Optional template for specifying name of output file in the form '{name,DEFAULT}'. "
    "File extension will be added automatically--do not include an extension in the FILENAME template. "
    "See below for additional details on templating system.",
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
)
@click.option(
    "--original-suffix",
    metavar="SUFFIX",
    help="Optional suffix template for naming original photos.  Default name for original photos is in form "
    "'filename.ext'. For example, with '--original-suffix _original', the original photo "
    "would be named 'filename_original.ext'.  The default suffix is '' (no suffix). "
    "Multi-value templates (see Templating System) are not permitted with --original-suffix.",
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
    metavar="<path to export report>",
    help="Write a CSV formatted report of all files that were exported.",
    type=click.Path(),
)
@click.option(
    "--cleanup",
    is_flag=True,
    help="Cleanup export directory by deleting any files which were not included in this export set. "
    "For example, photos which had previously been exported and were subsequently deleted in Photos. "
    "WARNING: --cleanup will delete *any* files in the export directory that were not exported by osxphotos, "
    "for example, your own scripts or other files.  Be sure this is what you intend before using "
    "--cleanup.  Use --dry-run with --cleanup first if you're not certain.",
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
    type=(click.Choice(POST_COMMAND_CATEGORIES, case_sensitive=False), str),
    multiple=True,
    help="Run COMMAND on exported files of category CATEGORY.  CATEGORY can be one of: "
    f"{', '.join(list(POST_COMMAND_CATEGORIES.keys()))}. "
    "COMMAND is an osxphotos template string, for example: '--post-command exported \"echo {filepath|shell_quote} >> {export_dir}/exported.txt\"', "
    "which appends the full path of all exported files to the file 'exported.txt'. "
    "You can run more than one command by repeating the '--post-command' option with different arguments. "
    "See Post Command below.",
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
    "--load-config",
    required=False,
    metavar="<config file path>",
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
    metavar="<config file path>",
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
    "--beta",
    is_flag=True,
    default=False,
    hidden=OSXPHOTOS_HIDDEN,
    help="Enable beta options.",
)
@click.option(
    "--profile",
    is_flag=True,
    default=False,
    hidden=OSXPHOTOS_HIDDEN,
    help="Run export with code profiler.",
)
@click.option(
    "--profile-sort",
    default=None,
    hidden=OSXPHOTOS_HIDDEN,
    multiple=True,
    metavar="SORT_KEY",
    type=click.Choice(
        PROFILE_SORT_KEYS,
        case_sensitive=True,
    ),
    help="Sort profiler output by SORT_KEY as specified at https://docs.python.org/3/library/profile.html#pstats.Stats.sort_stats. "
    f"Can be specified multiple times. Valid options are: {PROFILE_SORT_KEYS}. "
    "Default = 'cumulative'.",
)
@click.option(
    "--theme",
    metavar="THEME",
    type=click.Choice(["dark", "light", "mono", "plain"], case_sensitive=False),
    help="Specify the color theme to use for --verbose output. "
    "Valid themes are 'dark', 'light', 'mono', and 'plain'. "
    "Defaults to 'dark' or 'light' depending on system dark mode setting.",
)
@DEBUG_OPTIONS
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
    keyword,
    person,
    album,
    folder,
    uuid,
    name,
    uuid_from_file,
    title,
    no_title,
    description,
    no_description,
    uti,
    ignore_case,
    edited,
    external_edit,
    favorite,
    not_favorite,
    hidden,
    not_hidden,
    shared,
    not_shared,
    from_date,
    to_date,
    from_time,
    to_time,
    verbose,
    timestamp,
    no_progress,
    missing,
    update,
    force_update,
    ignore_signature,
    only_new,
    dry_run,
    export_as_hardlink,
    touch_file,
    overwrite,
    retry,
    export_by_date,
    skip_edited,
    skip_original_if_edited,
    skip_bursts,
    skip_live,
    skip_raw,
    skip_uuid,
    skip_uuid_from_file,
    person_keyword,
    album_keyword,
    keyword_template,
    replace_keywords,
    description_template,
    finder_tag_template,
    finder_tag_keywords,
    xattr_template,
    current_name,
    convert_to_jpeg,
    jpeg_quality,
    sidecar,
    sidecar_drop_ext,
    only_photos,
    only_movies,
    burst,
    not_burst,
    live,
    not_live,
    download_missing,
    dest,
    exiftool,
    exiftool_path,
    exiftool_option,
    exiftool_merge_keywords,
    exiftool_merge_persons,
    ignore_date_modified,
    portrait,
    not_portrait,
    screenshot,
    not_screenshot,
    slow_mo,
    not_slow_mo,
    time_lapse,
    not_time_lapse,
    hdr,
    not_hdr,
    selfie,
    not_selfie,
    panorama,
    not_panorama,
    has_raw,
    directory,
    filename_template,
    jpeg_ext,
    strip,
    edited_suffix,
    original_suffix,
    place,
    no_place,
    location,
    no_location,
    has_comment,
    no_comment,
    has_likes,
    no_likes,
    label,
    deleted,
    deleted_only,
    use_photos_export,
    use_photokit,
    report,
    cleanup,
    add_exported_to_album,
    add_skipped_to_album,
    add_missing_to_album,
    exportdb,
    ramdb,
    tmpdir,
    load_config,
    save_config,
    config_only,
    is_reference,
    beta,
    in_album,
    not_in_album,
    min_size,
    max_size,
    regex,
    selected,
    exif,
    query_eval,
    query_function,
    duplicate,
    post_command,
    post_function,
    preview,
    preview_suffix,
    preview_if_missing,
    profile,
    profile_sort,
    theme,
    debug,  # debug, watch, breakpoint handled in cli/__init__.py
    watch,
    breakpoint,
):
    """Export photos from the Photos database.
    Export path DEST is required.
    Optionally, query the Photos database using 1 or more search options;
    if more than one option is provided, they are treated as "AND"
    (e.g. search for photos matching all options).
    If no query options are provided, all photos will be exported.
    By default, all versions of all photos will be exported including edited
    versions, live photo movies, burst photos, and associated raw images.
    See --skip-edited, --skip-live, --skip-bursts, and --skip-raw options
    to modify this behavior.
    """

    # capture locals for use with ConfigOptions before changing any of them
    locals_ = locals()

    set_crash_data("locals", locals_)

    if profile:
        click.echo("Profiling...")
        profile_sort = profile_sort or ["cumulative"]
        click.echo(f"Profile sort_stats order: {profile_sort}")
        pr = cProfile.Profile()
        pr.enable()

        def at_exit():
            pr.disable()
            click.echo("Profiling completed")
            s = io.StringIO()
            pstats.Stats(pr, stream=s).strip_dirs().sort_stats(
                *profile_sort
            ).print_stats()
            click.echo(s.getvalue())

        atexit.register(at_exit)

    # NOTE: because of the way ConfigOptions works, Click options must not
    # set defaults which are not None or False. If defaults need to be set
    # do so below after load_config and save_config are handled.
    cfg = ConfigOptions(
        "export",
        locals_,
        ignore=["ctx", "cli_obj", "dest", "load_config", "save_config", "config_only"],
    )

    color_theme = get_theme(theme)
    verbose_ = verbose_print(
        verbose, timestamp, rich=True, theme=color_theme, highlight=False
    )
    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

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
        add_exported_to_album = cfg.add_exported_to_album
        add_missing_to_album = cfg.add_missing_to_album
        add_skipped_to_album = cfg.add_skipped_to_album
        album = cfg.album
        album_keyword = cfg.album_keyword
        beta = cfg.beta
        burst = cfg.burst
        cleanup = cfg.cleanup
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
        export_as_hardlink = cfg.export_as_hardlink
        export_by_date = cfg.export_by_date
        exportdb = cfg.exportdb
        external_edit = cfg.external_edit
        favorite = cfg.favorite
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
        jpeg_ext = cfg.jpeg_ext
        jpeg_quality = cfg.jpeg_quality
        keyword = cfg.keyword
        keyword_template = cfg.keyword_template
        label = cfg.label
        live = cfg.live
        location = cfg.location
        max_size = cfg.max_size
        min_size = cfg.min_size
        missing = cfg.missing
        name = cfg.name
        no_comment = cfg.no_comment
        no_description = cfg.no_description
        no_likes = cfg.no_likes
        no_location = cfg.no_location
        no_place = cfg.no_place
        no_progress = cfg.no_progress
        no_title = cfg.no_title
        not_burst = cfg.not_burst
        not_favorite = cfg.not_favorite
        not_hdr = cfg.not_hdr
        not_hidden = cfg.not_hidden
        not_in_album = cfg.not_in_album
        not_live = cfg.not_live
        not_panorama = cfg.not_panorama
        not_portrait = cfg.not_portrait
        not_screenshot = cfg.not_screenshot
        not_selfie = cfg.not_selfie
        not_shared = cfg.not_shared
        not_slow_mo = cfg.not_slow_mo
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
        post_function = cfg.post_function
        preview = cfg.preview
        preview_if_missing = cfg.preview_if_missing
        preview_suffix = cfg.preview_suffix
        query_eval = cfg.query_eval
        query_function = cfg.query_function
        ramdb = cfg.ramdb
        regex = cfg.regex
        replace_keywords = cfg.replace_keywords
        report = cfg.report
        retry = cfg.retry
        screenshot = cfg.screenshot
        selected = cfg.selected
        selfie = cfg.selfie
        shared = cfg.shared
        sidecar = cfg.sidecar
        sidecar_drop_ext = cfg.sidecar_drop_ext
        skip_bursts = cfg.skip_bursts
        skip_edited = cfg.skip_edited
        skip_live = cfg.skip_live
        skip_original_if_edited = cfg.skip_original_if_edited
        skip_raw = cfg.skip_raw
        skip_uuid = cfg.skip_uuid
        skip_uuid_from_file = cfg.skip_uuid_from_file
        slow_mo = cfg.slow_mo
        strip = cfg.strip
        theme = cfg.theme
        time_lapse = cfg.time_lapse
        timestamp = cfg.timestamp
        title = cfg.title
        tmpdir = cfg.tmpdir
        to_date = cfg.to_date
        to_time = cfg.to_time
        touch_file = cfg.touch_file
        update = cfg.update
        use_photokit = cfg.use_photokit
        use_photos_export = cfg.use_photos_export
        uti = cfg.uti
        uuid = cfg.uuid
        uuid_from_file = cfg.uuid_from_file
        verbose = cfg.verbose
        xattr_template = cfg.xattr_template

        # config file might have changed verbose
        color_theme = get_theme(theme)
        verbose_ = verbose_print(
            verbose, timestamp, rich=True, theme=color_theme, highlight=False
        )
        # set console for rich_echo to be same as for verbose_
        set_rich_console(get_verbose_console())
        set_rich_timestamp(timestamp)

        verbose_(f"Loaded options from file [filepath]{load_config}")

        set_crash_data("cfg", cfg.asdict())

    verbose_(f"osxphotos version {__version__}")

    # validate options
    exclusive_options = [
        ("favorite", "not_favorite"),
        ("hidden", "not_hidden"),
        ("title", "no_title"),
        ("description", "no_description"),
        ("only_photos", "only_movies"),
        ("burst", "not_burst"),
        ("live", "not_live"),
        ("portrait", "not_portrait"),
        ("screenshot", "not_screenshot"),
        ("slow_mo", "not_slow_mo"),
        ("time_lapse", "not_time_lapse"),
        ("hdr", "not_hdr"),
        ("selfie", "not_selfie"),
        ("panorama", "not_panorama"),
        ("export_by_date", "directory"),
        ("export_as_hardlink", "exiftool"),
        ("place", "no_place"),
        ("deleted", "deleted_only"),
        ("skip_edited", "skip_original_if_edited"),
        ("export_as_hardlink", "convert_to_jpeg"),
        ("export_as_hardlink", "download_missing"),
        ("shared", "not_shared"),
        ("has_comment", "no_comment"),
        ("has_likes", "no_likes"),
        ("in_album", "not_in_album"),
        ("location", "no_location"),
    ]
    dependent_options = [
        ("missing", ("download_missing", "use_photos_export")),
        ("jpeg_quality", ("convert_to_jpeg")),
        ("ignore_signature", ("update", "force_update")),
        ("only_new", ("update", "force_update")),
        ("exiftool_option", ("exiftool")),
        ("exiftool_merge_keywords", ("exiftool", "sidecar")),
        ("exiftool_merge_persons", ("exiftool", "sidecar")),
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
            "[error]--config-only must be used with --save-config",
            err=True,
        )
        sys.exit(1)

    if all(x in [s.lower() for s in sidecar] for x in ["json", "exiftool"]):
        rich_click_echo(
            "[error]Cannot use --sidecar json with --sidecar exiftool due to name collisions",
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
        verbose_(f"Saving options to config file '[filepath]{save_config}'")
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
    retry = 0 if not retry else retry

    if not os.path.isdir(dest):
        rich_click_echo(f"[error]DEST {dest} must be valid path", err=True)
        sys.exit(1)

    dest = str(pathlib.Path(dest).resolve())

    if report and os.path.isdir(report):
        rich_click_echo(
            f"[error]report is a directory, must be file name",
            err=True,
        )
        sys.exit(1)

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
        verbose_(f"exiftool path: [filepath]{exiftool_path}")

    # default searches for everything
    photos = True
    movies = True
    if only_movies:
        photos = False
    if only_photos:
        movies = False

    # load UUIDs if necessary and append to any uuids passed with --uuid
    if uuid_from_file:
        uuid_list = list(uuid)  # Click option is a tuple
        uuid_list.extend(load_uuid_from_file(uuid_from_file))
        uuid = tuple(uuid_list)

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
        click.confirm("Do you want to continue?", abort=True)

    if dry_run:
        export_db = ExportDBInMemory(dbfile=export_db_path, export_dir=dest)
        fileutil = FileUtilNoOp
    else:
        export_db = (
            ExportDBInMemory(dbfile=export_db_path, export_dir=dest)
            if ramdb
            else ExportDB(dbfile=export_db_path, export_dir=dest)
        )
        fileutil = FileUtil

    if verbose_:
        if export_db.was_created:
            verbose_(f"Created export database [filepath]{export_db_path}")
        else:
            verbose_(f"Using export database [filepath]{export_db_path}")
        upgraded = export_db.was_upgraded
        if upgraded:
            verbose_(
                f"Upgraded export database [filepath]{export_db_path}[/] from version [num]{upgraded[0]}[/] to [num]{upgraded[1]}[/]"
            )

    # save config to export_db
    export_db.set_config(cfg.write_to_str())

    photosdb = osxphotos.PhotosDB(
        dbfile=db, verbose=verbose_, exiftool=exiftool_path, rich=True
    )

    # enable beta features if requested
    photosdb._beta = beta

    query_options = QueryOptions(
        keyword=keyword,
        person=person,
        album=album,
        folder=folder,
        uuid=uuid,
        title=title,
        no_title=no_title,
        description=description,
        no_description=no_description,
        ignore_case=ignore_case,
        edited=edited,
        external_edit=external_edit,
        favorite=favorite,
        not_favorite=not_favorite,
        hidden=hidden,
        not_hidden=not_hidden,
        missing=missing,
        not_missing=None,
        shared=shared,
        not_shared=not_shared,
        photos=photos,
        movies=movies,
        uti=uti,
        burst=burst,
        not_burst=not_burst,
        live=live,
        not_live=not_live,
        cloudasset=False,
        not_cloudasset=False,
        incloud=False,
        not_incloud=False,
        from_date=from_date,
        to_date=to_date,
        from_time=from_time,
        to_time=to_time,
        portrait=portrait,
        not_portrait=not_portrait,
        screenshot=screenshot,
        not_screenshot=not_screenshot,
        slow_mo=slow_mo,
        not_slow_mo=not_slow_mo,
        time_lapse=time_lapse,
        not_time_lapse=not_time_lapse,
        hdr=hdr,
        not_hdr=not_hdr,
        selfie=selfie,
        not_selfie=not_selfie,
        panorama=panorama,
        not_panorama=not_panorama,
        has_raw=has_raw,
        place=place,
        no_place=no_place,
        location=location,
        no_location=no_location,
        label=label,
        deleted=deleted,
        deleted_only=deleted_only,
        has_comment=has_comment,
        no_comment=no_comment,
        has_likes=has_likes,
        no_likes=no_likes,
        is_reference=is_reference,
        in_album=in_album,
        not_in_album=not_in_album,
        burst_photos=export_bursts,
        # skip missing bursts if using --download-missing by itself as AppleScript otherwise causes errors
        missing_bursts=(download_missing and use_photokit) or not download_missing,
        name=name,
        min_size=min_size,
        max_size=max_size,
        regex=regex,
        selected=selected,
        exif=exif,
        query_eval=query_eval,
        function=query_function,
        duplicate=duplicate,
    )

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
        # TODO: photos or photo appears several times, pull into a separate function
        photo_str = "photos" if num_photos > 1 else "photo"
        rich_echo(
            f"Exporting [num]{num_photos}[/num] {photo_str} to [filepath]{dest}[/]..."
        )
        start_time = time.perf_counter()
        # though the command line option is current_name, internally all processing
        # logic uses original_name which is the boolean inverse of current_name
        # because the original code used --original-name as an option
        original_name = not current_name

        # set up for --add-export-to-album if needed
        album_export = (
            PhotosAlbum(add_exported_to_album, verbose=verbose_)
            if add_exported_to_album
            else None
        )
        album_skipped = (
            PhotosAlbum(add_skipped_to_album, verbose=verbose_)
            if add_skipped_to_album
            else None
        )
        album_missing = (
            PhotosAlbum(add_missing_to_album, verbose=verbose_)
            if add_missing_to_album
            else None
        )

        photo_num = 0
        with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
            task = progress.add_task(
                f"Exporting [num]{num_photos}[/] photos", total=num_photos
            )
            for p in photos:
                photo_num += 1
                export_results = export_photo(
                    photo=p,
                    dest=dest,
                    album_keyword=album_keyword,
                    convert_to_jpeg=convert_to_jpeg,
                    description_template=description_template,
                    directory=directory,
                    download_missing=download_missing,
                    dry_run=dry_run,
                    edited_suffix=edited_suffix,
                    exiftool_merge_keywords=exiftool_merge_keywords,
                    exiftool_merge_persons=exiftool_merge_persons,
                    exiftool_option=exiftool_option,
                    exiftool=exiftool,
                    export_as_hardlink=export_as_hardlink,
                    export_by_date=export_by_date,
                    export_db=export_db,
                    export_dir=dest,
                    export_edited=export_edited,
                    export_live=export_live,
                    export_preview=preview,
                    export_raw=export_raw,
                    filename_template=filename_template,
                    fileutil=fileutil,
                    force_update=force_update,
                    ignore_date_modified=ignore_date_modified,
                    ignore_signature=ignore_signature,
                    jpeg_ext=jpeg_ext,
                    jpeg_quality=jpeg_quality,
                    keyword_template=keyword_template,
                    num_photos=num_photos,
                    original_name=original_name,
                    original_suffix=original_suffix,
                    overwrite=overwrite,
                    person_keyword=person_keyword,
                    photo_num=photo_num,
                    preview_if_missing=preview_if_missing,
                    preview_suffix=preview_suffix,
                    replace_keywords=replace_keywords,
                    retry=retry,
                    sidecar_drop_ext=sidecar_drop_ext,
                    sidecar=sidecar,
                    skip_original_if_edited=skip_original_if_edited,
                    strip=strip,
                    touch_file=touch_file,
                    update=update,
                    use_photokit=use_photokit,
                    use_photos_export=use_photos_export,
                    verbose_=verbose_,
                    tmpdir=tmpdir,
                )

                if post_function:
                    for function in post_function:
                        # post function is tuple of (function, filename.py::function_name)
                        verbose_(f"Calling post-function [bold]{function[1]}")
                        if not dry_run:
                            try:
                                function[0](p, export_results, verbose_)
                            except Exception as e:
                                rich_echo_error(
                                    f"[error]Error running post-function [italic]{function[1]}[/italic]: {e}"
                                )

                run_post_command(
                    photo=p,
                    post_command=post_command,
                    export_results=export_results,
                    export_dir=dest,
                    dry_run=dry_run,
                    exiftool_path=exiftool_path,
                    export_db=export_db,
                    verbose_=verbose_,
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
                        verbose_=verbose_,
                    )
                    results.xattr_written.extend(tags_written)
                    results.xattr_skipped.extend(tags_skipped)

                if xattr_template:
                    xattr_written, xattr_skipped = write_extended_attributes(
                        p,
                        photo_files,
                        xattr_template,
                        strip=strip,
                        export_dir=dest,
                        verbose_=verbose_,
                    )
                    results.xattr_written.extend(xattr_written)
                    results.xattr_skipped.extend(xattr_skipped)

                progress.advance(task)

        photo_str_total = "photos" if len(photos) != 1 else "photo"
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
        rich_echo(summary)
        stop_time = time.perf_counter()
        rich_echo(f"Elapsed time: [time]{format_sec_to_hhmmss(stop_time-start_time)}")
    else:
        rich_echo("Did not find any photos to export")

    # cleanup files and do report if needed
    if cleanup:
        db_file = str(pathlib.Path(export_db_path).resolve())
        db_files = [db_file, db_file + "-wal", db_file + "-shm"]
        all_files = (
            results.exported
            + results.skipped
            + results.exif_updated
            + results.touched
            + results.converted_to_jpeg
            + results.sidecar_json_written
            + results.sidecar_json_skipped
            + results.sidecar_exiftool_written
            + results.sidecar_exiftool_skipped
            + results.sidecar_xmp_written
            + results.sidecar_xmp_skipped
            # include missing so a file that was already in export directory
            # but was missing on --update doesn't get deleted
            # (better to have old version than none)
            + results.missing
            # include files that have error in case they exist from previous export
            + [r[0] for r in results.error]
            + db_files
        )
        rich_echo(f"Cleaning up [filepath]{dest}")
        cleaned_files, cleaned_dirs = cleanup_files(
            dest, all_files, fileutil, verbose_=verbose_
        )
        file_str = "files" if len(cleaned_files) != 1 else "file"
        dir_str = "directories" if len(cleaned_dirs) != 1 else "directory"
        rich_echo(
            f"Deleted: [num]{len(cleaned_files)}[/num] {file_str}, [num]{len(cleaned_dirs)}[/num] {dir_str}"
        )
        results.deleted_files = cleaned_files
        results.deleted_directories = cleaned_dirs

    if report:
        verbose_(f"Writing export report to [filepath]{report}")
        write_export_report(report, results)

    # close export_db and write changes if needed
    if ramdb and not dry_run:
        verbose_(f"Writing export database changes back to [filepath]{export_db.path}")
        export_db.write_to_disk()
    export_db.close()


def _export_with_profiler(args: Dict):
    """ "Run export with cProfile"""
    try:
        args.pop("profile")
    except KeyError:
        pass

    cProfile.runctx(
        "_export(**args)", globals=globals(), locals=locals(), sort="tottime"
    )


def export_photo(
    photo=None,
    dest=None,
    verbose_=None,
    export_by_date=None,
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
    filename_template=None,
    export_raw=None,
    album_keyword=None,
    person_keyword=None,
    keyword_template=None,
    description_template=None,
    export_db=None,
    fileutil=FileUtil,
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
):
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
        sidecar_drop_ext: bool; if True, drops photo extension from sidecar name
        sidecar: list zero, 1 or 2 of ["json","xmp"] of sidecar variety to export
        skip_original_if_edited: bool; if True does not export original if photo has been edited
        touch_file: bool; sets file's modification time to match photo date
        update: bool, only export updated photos
        use_photos_export: bool; if True forces the use of AppleScript to export even if photo not missing
        verbose_: callable for verbose output
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
            verbose_(
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

            verbose_(
                f"Exporting [filename]{photo.original_filename}[/] ([filename]{photo.filename}[/]) as [filepath]{original_filename}[/] ([count]{photo_num}/{num_photos}[/])"
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
                sidecar_drop_ext=sidecar_drop_ext,
                sidecar_flags=sidecar_flags,
                touch_file=touch_file,
                update=update,
                use_photos_export=use_photos_export,
                use_photokit=use_photokit,
                verbose_=verbose_,
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

                verbose_(
                    f"Exporting edited version of [filename]{photo.original_filename}[/filename] ([filename]{photo.filename}[/filename]) as [filepath]{edited_filename}[/filepath]"
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
                    sidecar_drop_ext=sidecar_drop_ext,
                    sidecar_flags=sidecar_flags if not export_original else 0,
                    touch_file=touch_file,
                    update=update,
                    use_photos_export=use_photos_export,
                    use_photokit=use_photokit,
                    verbose_=verbose_,
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
    sidecar_drop_ext,
    sidecar_flags,
    touch_file,
    update,
    use_photos_export,
    use_photokit,
    verbose_,
    tmpdir,
):
    """Export photo to directory dest_path"""

    results = ExportResults()

    # don't try to export photos in the trash if they're missing
    photo_path = photo.path if export_original else photo.path_edited
    if photo.intrash and not photo_path and not preview_if_missing:
        # skip deleted files if they're missing
        # as AppleScript/PhotoKit cannot export deleted photos
        verbose_(
            f"Skipping missing deleted photo {photo.original_filename} ({photo.uuid})"
        )
        results.missing.append(str(pathlib.Path(dest_path) / filename))
        return results

    render_options = RenderOptions(export_dir=export_dir, dest_path=dest_path)

    if not export_original and not edited:
        verbose_(f"Skipping original version of [filename]{photo.original_filename}")
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
                exiftool_flags=exiftool_option,
                exiftool=exiftool,
                export_as_hardlink=export_as_hardlink,
                export_db=export_db,
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
                preview_suffix=preview_suffix,
                preview=export_preview or (missing and preview_if_missing),
                raw_photo=export_raw,
                render_options=render_options,
                replace_keywords=replace_keywords,
                sidecar_drop_ext=sidecar_drop_ext,
                sidecar=sidecar_flags,
                touch_file=touch_file,
                update=update,
                use_albums_as_keywords=album_keyword,
                use_persons_as_keywords=person_keyword,
                use_photokit=use_photokit,
                use_photos_export=use_photos_export,
                verbose=verbose_,
                tmpdir=tmpdir,
                rich=True,
            )
            exporter = PhotoExporter(photo)
            export_results = exporter.export(
                dest=dest_path, filename=filename, options=export_options
            )
            for warning_ in export_results.exiftool_warning:
                verbose_(
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
                results.error.append((str(pathlib.Path(dest) / filename), e))
                break
            else:
                rich_echo(
                    f"Retrying export for photo ([uuid]{photo.uuid}[/uuid]: [filename]{photo.original_filename}[/filename])"
                )

    if verbose_:
        if update or force_update:
            for new in results.new:
                verbose_(f"Exported new file [filepath]{new}")
            for updated in results.updated:
                verbose_(f"Exported updated file [filepath]{updated}")
            for skipped in results.skipped:
                verbose_(f"Skipped up to date file [filepath]{skipped}")
        else:
            for exported in results.exported:
                verbose_(f"Exported [filepath]{exported}")
        for touched in results.touched:
            verbose_(f"Touched date on file [filepath]{touched}")

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
        # print(os.path.join(root, directory))
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


def write_export_report(report_file, results):

    """write CSV report with results from export

    Args:
        report_file: path to report file
        results: ExportResults object
    """

    # Collect results for reporting
    all_results = {
        result: {
            "filename": result,
            "exported": 0,
            "new": 0,
            "updated": 0,
            "skipped": 0,
            "exif_updated": 0,
            "touched": 0,
            "converted_to_jpeg": 0,
            "sidecar_xmp": 0,
            "sidecar_json": 0,
            "sidecar_exiftool": 0,
            "missing": 0,
            "error": "",
            "exiftool_warning": "",
            "exiftool_error": "",
            "extended_attributes_written": 0,
            "extended_attributes_skipped": 0,
            "cleanup_deleted_file": 0,
            "cleanup_deleted_directory": 0,
            "exported_album": "",
        }
        for result in results.all_files()
        + results.deleted_files
        + results.deleted_directories
    }

    for result in results.exported:
        all_results[result]["exported"] = 1

    for result in results.new:
        all_results[result]["new"] = 1

    for result in results.updated:
        all_results[result]["updated"] = 1

    for result in results.skipped:
        all_results[result]["skipped"] = 1

    for result in results.exif_updated:
        all_results[result]["exif_updated"] = 1

    for result in results.touched:
        all_results[result]["touched"] = 1

    for result in results.converted_to_jpeg:
        all_results[result]["converted_to_jpeg"] = 1

    for result in results.sidecar_xmp_written:
        all_results[result]["sidecar_xmp"] = 1
        all_results[result]["exported"] = 1

    for result in results.sidecar_xmp_skipped:
        all_results[result]["sidecar_xmp"] = 1
        all_results[result]["skipped"] = 1

    for result in results.sidecar_json_written:
        all_results[result]["sidecar_json"] = 1
        all_results[result]["exported"] = 1

    for result in results.sidecar_json_skipped:
        all_results[result]["sidecar_json"] = 1
        all_results[result]["skipped"] = 1

    for result in results.sidecar_exiftool_written:
        all_results[result]["sidecar_exiftool"] = 1
        all_results[result]["exported"] = 1

    for result in results.sidecar_exiftool_skipped:
        all_results[result]["sidecar_exiftool"] = 1
        all_results[result]["skipped"] = 1

    for result in results.missing:
        all_results[result]["missing"] = 1

    for result in results.error:
        all_results[result[0]]["error"] = result[1]

    for result in results.exiftool_warning:
        all_results[result[0]]["exiftool_warning"] = result[1]

    for result in results.exiftool_error:
        all_results[result[0]]["exiftool_error"] = result[1]

    for result in results.xattr_written:
        all_results[result]["extended_attributes_written"] = 1

    for result in results.xattr_skipped:
        all_results[result]["extended_attributes_skipped"] = 1

    for result in results.deleted_files:
        all_results[result]["cleanup_deleted_file"] = 1

    for result in results.deleted_directories:
        all_results[result]["cleanup_deleted_directory"] = 1

    for result, album in results.exported_album:
        all_results[result]["exported_album"] = album

    report_columns = [
        "filename",
        "exported",
        "new",
        "updated",
        "skipped",
        "exif_updated",
        "touched",
        "converted_to_jpeg",
        "sidecar_xmp",
        "sidecar_json",
        "sidecar_exiftool",
        "missing",
        "error",
        "exiftool_warning",
        "exiftool_error",
        "extended_attributes_written",
        "extended_attributes_skipped",
        "cleanup_deleted_file",
        "cleanup_deleted_directory",
        "exported_album",
    ]

    try:
        with open(report_file, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=report_columns)
            writer.writeheader()
            for data in [result for result in all_results.values()]:
                writer.writerow(data)
    except IOError:
        rich_echo_error("[error]Could not open output file for writing"),
        sys.exit(1)


def cleanup_files(dest_path, files_to_keep, fileutil, verbose_):
    """cleanup dest_path by deleting and files and empty directories
        not in files_to_keep

    Args:
        dest_path: path to directory to clean
        files_to_keep: list of full file paths to keep (not delete)
        fileutile: FileUtil object

    Returns:
        tuple of (list of files deleted, list of directories deleted)
    """
    keepers = {
        normalize_fs_path(str(filename).lower()): 1 for filename in files_to_keep
    }

    deleted_files = []
    for p in pathlib.Path(dest_path).rglob("*"):
        if p.is_file() and normalize_fs_path(str(p).lower()) not in keepers:
            verbose_(f"Deleting [filepath]{p}")
            fileutil.unlink(p)
            deleted_files.append(str(p))

    # delete empty directories
    deleted_dirs = []
    # walk directory tree bottom up and verify contents are empty
    for dirpath, _, _ in os.walk(dest_path, topdown=False):
        if not list(pathlib.Path(dirpath).glob("*")):
            # directory and directory is empty
            verbose_(f"Deleting empty directory {dirpath}")
            fileutil.rmdir(dirpath)
            deleted_dirs.append(str(dirpath))

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
    verbose_=noop,
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
        verbose_: function to call to print verbose messages

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
        exif = PhotoExporter(photo)._exiftool_dict(options=export_options)
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

    tags = [osxmetadata.Tag(tag) for tag in set(tags)]
    for f in files:
        md = osxmetadata.OSXMetaData(f)
        if sorted(md.tags) != sorted(tags):
            verbose_(f"Writing Finder tags to {f}")
            md.tags = tags
            written.append(f)
        else:
            verbose_(f"Skipping Finder tags for {f}: nothing to do")
            skipped.append(f)

    return (written, skipped)


def write_extended_attributes(
    photo,
    files,
    xattr_template,
    strip=False,
    export_dir=None,
    verbose_=noop,
):
    """Writes extended attributes to exported files

    Args:
        photo: a PhotoInfo object
        strip:   xattr_template: list of tuples: (attribute name, attribute template)
        export_dir: value to use for {export_dir} template

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
        md = osxmetadata.OSXMetaData(f)
        for attr, value in attributes.items():
            islist = osxmetadata.ATTRIBUTES[attr].list
            if value:
                value = ", ".join(value) if not islist else sorted(value)
            file_value = md.get_attribute(attr)

            if file_value and islist:
                file_value = sorted(file_value)

            if (not file_value and not value) or file_value == value:
                # if both not set or both equal, nothing to do
                # get_attribute returns None if not set and value will be [] if not set so can't directly compare
                verbose_(f"Skipping extended attribute {attr} for {f}: nothing to do")
                skipped.add(f)
            else:
                verbose_(f"Writing extended attribute {attr} to {f}")
                md.set_attribute(attr, value)
                written.add(f)

    return list(written), [f for f in skipped if f not in written]


def run_post_command(
    photo,
    post_command,
    export_results,
    export_dir,
    dry_run,
    exiftool_path,
    export_db,
    verbose_,
):
    # todo: pass in RenderOptions from export? (e.g. so it contains strip, etc?)
    # todo: need a shell_quote template type:
    # {shell_quote,{filepath}/foo/bar}
    # that quotes everything in the default value
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
                verbose_(f'Running command: "{command}"')
                if not dry_run:
                    args = shlex.split(command)
                    cwd = pathlib.Path(f).parent
                    run_error = None
                    run_results = None
                    try:
                        run_results = subprocess.run(command, shell=True, cwd=cwd)
                    except Exception as e:
                        run_error = e
                    finally:
                        run_error = run_error or run_results.returncode
                        if run_error:
                            rich_echo_error(
                                f'[error]Error running command "{command}": {run_error}'
                            )
