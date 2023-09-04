""" Custom template system for osxphotos, implements metadata template language (MTL) """


import datetime
import locale
import os
import pathlib
import re
import shlex
import sys
from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional, Tuple

from textx import TextXSyntaxError, metamodel_from_file

import osxphotos.template_counter as counter

from ._constants import _UNKNOWN_PERSON, TEXT_DETECTION_CONFIDENCE_THRESHOLD
from ._version import __version__
from .datetime_formatter import DateTimeFormatter
from .exiftool import ExifToolCaching
from .path_utils import sanitize_dirname, sanitize_filename, sanitize_pathpart
from .utils import expand_and_validate_filepath, load_function, uuid_to_shortuuid

__all__ = [
    "RenderOptions",
    "PhotoTemplateParser",
    "PhotoTemplate",
    "parse_default_kv",
    "get_template_help",
    "format_str_value",
]

# TODO: a lot of values are passed from function to function like path_sep--make these all class properties

# ensure locale set to user's locale
locale.setlocale(locale.LC_ALL, "")

MTL_GRAMMAR_MODEL = str(pathlib.Path(__file__).parent / "phototemplate.tx")

"""TextX metamodel for osxphotos template language """

PHOTO_VIDEO_TYPE_DEFAULTS = {"photo": "photo", "video": "video"}

MEDIA_TYPE_DEFAULTS = {
    "selfie": "selfie",
    "time_lapse": "time_lapse",
    "panorama": "panorama",
    "slow_mo": "slow_mo",
    "screenshot": "screenshot",
    "portrait": "portrait",
    "live_photo": "live_photo",
    "burst": "burst",
    "photo": "photo",
    "video": "video",
}

# Permitted substitutions (each of these returns a single value or None)
TEMPLATE_SUBSTITUTIONS = {
    "{name}": "Current filename of the photo",
    "{original_name}": "Photo's original filename when imported to Photos",
    "{title}": "Title of the photo",
    "{descr}": "Description of the photo",
    "{media_type}": (
        f"Special media type resolved in this precedence: {', '.join(t for t in MEDIA_TYPE_DEFAULTS)}. "
        "Defaults to 'photo' or 'video' if no special type. "
        "Customize one or more media types using format: '{media_type,video=vidéo;time_lapse=vidéo_accélérée}'"
    ),
    "{photo_or_video}": "'photo' or 'video' depending on what type the image is. To customize, use default value as in '{photo_or_video,photo=fotos;video=videos}'",
    "{hdr}": "Photo is HDR?; True/False value, use in format '{hdr?VALUE_IF_TRUE,VALUE_IF_FALSE}'",
    "{edited}": "True if photo has been edited (has adjustments), otherwise False; use in format '{edited?VALUE_IF_TRUE,VALUE_IF_FALSE}'",
    "{edited_version}": "True if template is being rendered for the edited version of a photo, otherwise False. ",
    "{favorite}": "Photo has been marked as favorite?; True/False value, use in format '{favorite?VALUE_IF_TRUE,VALUE_IF_FALSE}'",
    "{created}": "Photo's creation date in ISO format, e.g. '2020-03-22'",
    "{created.date}": "Photo's creation date in ISO format, e.g. '2020-03-22'",
    "{created.year}": "4-digit year of photo creation time",
    "{created.yy}": "2-digit year of photo creation time",
    "{created.mm}": "2-digit month of the photo creation time (zero padded)",
    "{created.month}": "Month name in user's locale of the photo creation time",
    "{created.mon}": "Month abbreviation in the user's locale of the photo creation time",
    "{created.dd}": "2-digit day of the month (zero padded) of photo creation time",
    "{created.dow}": "Day of week in user's locale of the photo creation time",
    "{created.doy}": "3-digit day of year (e.g Julian day) of photo creation time, starting from 1 (zero padded)",
    "{created.hour}": "2-digit hour of the photo creation time",
    "{created.min}": "2-digit minute of the photo creation time",
    "{created.sec}": "2-digit second of the photo creation time",
    "{created.strftime}": "Apply strftime template to file creation date/time. Should be used in form "
    + "{created.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. "
    + "{created.strftime,%Y-%U} would result in year-week number of year: '2020-23'. "
    + "If used with no template will return null value. "
    + "See https://strftime.org/ for help on strftime templates.",
    "{modified}": "Photo's modification date in ISO format, e.g. '2020-03-22'; uses creation date if photo is not modified",
    "{modified.date}": "Photo's modification date in ISO format, e.g. '2020-03-22'; uses creation date if photo is not modified",
    "{modified.year}": "4-digit year of photo modification time; uses creation date if photo is not modified",
    "{modified.yy}": "2-digit year of photo modification time; uses creation date if photo is not modified",
    "{modified.mm}": "2-digit month of the photo modification time (zero padded); uses creation date if photo is not modified",
    "{modified.month}": "Month name in user's locale of the photo modification time; uses creation date if photo is not modified",
    "{modified.mon}": "Month abbreviation in the user's locale of the photo modification time; uses creation date if photo is not modified",
    "{modified.dd}": "2-digit day of the month (zero padded) of the photo modification time; uses creation date if photo is not modified",
    "{modified.dow}": "Day of week in user's locale of the photo modification time; uses creation date if photo is not modified",
    "{modified.doy}": "3-digit day of year (e.g Julian day) of photo modification time, starting from 1 (zero padded); uses creation date if photo is not modified",
    "{modified.hour}": "2-digit hour of the photo modification time; uses creation date if photo is not modified",
    "{modified.min}": "2-digit minute of the photo modification time; uses creation date if photo is not modified",
    "{modified.sec}": "2-digit second of the photo modification time; uses creation date if photo is not modified",
    "{modified.strftime}": "Apply strftime template to file modification date/time. Should be used in form "
    + "{modified.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. "
    + "{modified.strftime,%Y-%U} would result in year-week number of year: '2020-23'. "
    + "If used with no template will return null value. Uses creation date if photo is not modified. "
    + "See https://strftime.org/ for help on strftime templates.",
    "{today}": "Current date in iso format, e.g. '2020-03-22'",
    "{today.date}": "Current date in iso format, e.g. '2020-03-22'",
    "{today.year}": "4-digit year of current date",
    "{today.yy}": "2-digit year of current date",
    "{today.mm}": "2-digit month of the current date (zero padded)",
    "{today.month}": "Month name in user's locale of the current date",
    "{today.mon}": "Month abbreviation in the user's locale of the current date",
    "{today.dd}": "2-digit day of the month (zero padded) of current date",
    "{today.dow}": "Day of week in user's locale of the current date",
    "{today.doy}": "3-digit day of year (e.g Julian day) of current date, starting from 1 (zero padded)",
    "{today.hour}": "2-digit hour of the current date",
    "{today.min}": "2-digit minute of the current date",
    "{today.sec}": "2-digit second of the current date",
    "{today.strftime}": "Apply strftime template to current date/time. Should be used in form "
    + "{today.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. "
    + "{today.strftime,%Y-%U} would result in year-week number of year: '2020-23'. "
    + "If used with no template will return null value. "
    + "See https://strftime.org/ for help on strftime templates.",
    "{place.name}": "Place name from the photo's reverse geolocation data, as displayed in Photos",
    "{place.country_code}": "The ISO country code from the photo's reverse geolocation data",
    "{place.name.country}": "Country name from the photo's reverse geolocation data",
    "{place.name.state_province}": "State or province name from the photo's reverse geolocation data",
    "{place.name.city}": "City or locality name from the photo's reverse geolocation data",
    "{place.name.area_of_interest}": "Area of interest name (e.g. landmark or public place) from the photo's reverse geolocation data",
    "{place.address}": "Postal address from the photo's reverse geolocation data, e.g. '2007 18th St NW, Washington, DC 20009, United States'",
    "{place.address.street}": "Street part of the postal address, e.g. '2007 18th St NW'",
    "{place.address.city}": "City part of the postal address, e.g. 'Washington'",
    "{place.address.state_province}": "State/province part of the postal address, e.g. 'DC'",
    "{place.address.postal_code}": "Postal code part of the postal address, e.g. '20009'",
    "{place.address.country}": "Country name of the postal address, e.g. 'United States'",
    "{place.address.country_code}": "ISO country code of the postal address, e.g. 'US'",
    "{searchinfo.season}": "Season of the year associated with a photo, e.g. 'Summer'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).",
    "{exif.camera_make}": "Camera make from original photo's EXIF information as imported by Photos, e.g. 'Apple'",
    "{exif.camera_model}": "Camera model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s'",
    "{exif.lens_model}": "Lens model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s back camera 4.15mm f/2.2'",
    "{moment}": "The moment title of the photo",
    "{uuid}": "Photo's internal universally unique identifier (UUID) for the photo, a 36-character string unique to the photo, e.g. '128FB4C6-0B16-4E7D-9108-FB2E90DA1546'",
    "{shortuuid}": "A shorter representation of photo's internal universally unique identifier (UUID) for the photo, "
    + "a 22-character string unique to the photo, e.g. 'JYsxugP9UjetmCbBCHXcmu'",
    "{id}": "A unique number for the photo based on its primary key in the Photos database. "
    + "A sequential integer, e.g. 1, 2, 3...etc.  Each asset associated with a photo (e.g. an image and Live Photo preview) will share the same id. "
    + "May be formatted using a python string format code. "
    + "For example, to format as a 5-digit integer and pad with zeros, use '{id:05d}' which results in "
    + "00001, 00002, 00003...etc. ",
    "{counter}": "A sequential counter, starting at 0, that increments each time it is evaluated."
    + "To start counting at a value other than 0, append append '(starting_value)' to the field name."
    + "For example, to start counting at 1 instead of 0: '{counter(1)}'."
    + "May be formatted using a python string format code."
    + "For example, to format as a 5-digit integer and pad with zeros, use '{counter:05d(1)}'"
    + "which results in 00001, 00002, 00003...etc."
    + "You may also specify a stop value which causes the counter to reset to the starting value"
    + "when the stop value is reached and a step size which causes the counter to increment by"
    + "the specified value instead of 1. Use the format '{counter(start,stop,step)}' where start,"
    + "stop, and step are integers. For example, to count from 1 to 10 by 2, use '{counter(1,11,2)}'."
    + "Note that the counter stops counting when the stop value is reached and does not return the"
    + "stop value. Start, stop, and step are optional and may be omitted. For example, to count"
    + "from 0 by 2s, use '{counter(,,2)}'."
    + "You may create an arbitrary number of counters by appending a unique name to the field name"
    + "preceded by a period: '{counter.a}', '{counter.b}', etc. Each counter will have its own state"
    + "and will start at 0 and increment by 1 unless otherwise specified."
    + " Note: {counter} is not suitable for use with 'export' and '--update' "
    + "as the counter associated with a photo may change between export sessions. See also {id}.",
    "{album_seq}": "An integer, starting at 0, indicating the photo's index (sequence) in the containing album. "
    + "Only valid when used in a '--filename' template and only when '{album}' or '{folder_album}' is used in the '--directory' template. "
    + 'For example \'--directory "{folder_album}" --filename "{album_seq}_{original_name}"\'. '
    + "To start counting at a value other than 0, append append '(starting_value)' to the field name.  "
    + "For example, to start counting at 1 instead of 0: '{album_seq(1)}'. "
    + "May be formatted using a python string format code. "
    + "For example, to format as a 5-digit integer and pad with zeros, use '{album_seq:05d}' which results in "
    + "00000, 00001, 00002...etc. "
    + "To format while also using a starting value: '{album_seq:05d(1)}' which results in 0001, 00002...etc."
    + "This may result in incorrect sequences if you have duplicate albums with the same name; see also '{folder_album_seq}'.",
    "{folder_album_seq}": "An integer, starting at 0, indicating the photo's index (sequence) in the containing album and folder path. "
    + "Only valid when used in a '--filename' template and only when '{folder_album}' is used in the '--directory' template. "
    + 'For example \'--directory "{folder_album}" --filename "{folder_album_seq}_{original_name}"\'. '
    + "To start counting at a value other than 0, append '(starting_value)' to the field name. "
    + "For example, to start counting at 1 instead of 0: '{folder_album_seq(1)}' "
    + "May be formatted using a python string format code. "
    + "For example, to format as a 5-digit integer and pad with zeros, use '{folder_album_seq:05d}' which results in "
    + "00000, 00001, 00002...etc. "
    + "To format while also using a starting value: '{folder_album_seq:05d(1)}' which results in 0001, 00002...etc."
    + "This may result in incorrect sequences if you have duplicate albums with the same name in the same folder; see also '{album_seq}'. ",
    "{comma}": "A comma: ','",
    "{semicolon}": "A semicolon: ';'",
    "{questionmark}": "A question mark: '?'",
    "{pipe}": "A vertical pipe: '|'",
    "{openbrace}": "An open brace: '{'",
    "{closebrace}": "A close brace: '}'",
    "{openparens}": "An open parentheses: '('",
    "{closeparens}": "A close parentheses: ')'",
    "{openbracket}": "An open bracket: '['",
    "{closebracket}": "A close bracket: ']'",
    "{newline}": r"A newline: '\n'",
    "{lf}": r"A line feed: '\n', alias for {newline}",
    "{cr}": r"A carriage return: '\r'",
    "{crlf}": r"A carriage return + line feed: '\r\n'",
    "{tab}": r":A tab: '\t'",
    "{osxphotos_version}": f"The osxphotos version, e.g. '{__version__}'",
    "{osxphotos_cmd_line}": "The full command line used to run osxphotos",
}

TEMPLATE_SUBSTITUTIONS_PATHLIB = {
    "{export_dir}": "The full path to the export directory",
    "{filepath}": "The full path to the exported file",
}

# Permitted multi-value substitutions (each of these returns None or 1 or more values)
TEMPLATE_SUBSTITUTIONS_MULTI_VALUED = {
    "{album}": "Album(s) photo is contained in",
    "{folder_album}": "Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder",
    "{project}": "Project(s) photo is contained in (such as greeting cards, calendars, slideshows)",
    "{album_project}": "Album(s) and project(s) photo is contained in; treats projects as regular albums",
    "{folder_album_project}": "Folder path + album (includes projects as albums) photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder",
    "{keyword}": "Keyword(s) assigned to photo",
    "{person}": "Person(s) / face(s) in a photo",
    "{label}": "Image categorization label associated with a photo (Photos 5+ only). "
    "Labels are added automatically by Photos using machine learning algorithms to categorize images. "
    "These are not the same as {keyword} which refers to the user-defined keywords/tags applied in Photos.",
    "{label_normalized}": "All lower case version of 'label' (Photos 5+ only)",
    "{comment}": "Comment(s) on shared Photos; format is 'Person name: comment text' (Photos 5+ only)",
    "{exiftool}": "Format: '{exiftool:GROUP:TAGNAME}'; use exiftool (https://exiftool.org) to extract metadata, in form GROUP:TAGNAME, from image.  "
    "E.g. '{exiftool:EXIF:Make}' to get camera make, or {exiftool:IPTC:Keywords} to extract keywords. "
    "See https://exiftool.org/TagNames/ for list of valid tag names.  You must specify group (e.g. EXIF, IPTC, etc) "
    "as used in `exiftool -G`. exiftool must be installed in the path to use this template.",
    "{searchinfo.holiday}": "Holiday names associated with a photo, e.g. 'Christmas Day'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).",
    "{searchinfo.activity}": "Activities associated with a photo, e.g. 'Sporting Event'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).",
    "{searchinfo.venue}": "Venues associated with a photo, e.g. name of restaurant; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).",
    "{searchinfo.venue_type}": "Venue types associated with a photo, e.g. 'Restaurant'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).",
    "{photo}": "Provides direct access to the PhotoInfo object for the photo. "
    + "Must be used in format '{photo.property}' where 'property' represents a PhotoInfo property. "
    + "For example: '{photo.favorite}' is the same as '{favorite}' and '{photo.place.name}' is the same as '{place.name}'. "
    + "'{photo}' provides access to properties that are not available as separate template fields but it assumes some knowledge of "
    + "the underlying PhotoInfo class.  See https://rhettbull.github.io/osxphotos/ for additional documentation on the PhotoInfo class.",
    "{detected_text}": "List of text strings found in the image after performing text detection. "
    + "Using '{detected_text}' will cause osxphotos to perform text detection on your photos using the built-in macOS text detection algorithms which will slow down your export. "
    + "The results for each photo will be cached in the export database so that future exports with '--update' do not need to reprocess each photo. "
    + "You may pass a confidence threshold value between 0.0 and 1.0 after a colon as in '{detected_text:0.5}'; "
    + f"The default confidence threshold is {TEXT_DETECTION_CONFIDENCE_THRESHOLD}. "
    + "'{detected_text}' works only on macOS Catalina (10.15) or later. "
    + "Note: this feature is not the same thing as Live Text in macOS Monterey, which osxphotos does not yet support.",
    "{shell_quote}": "Use in form '{shell_quote,TEMPLATE}'; quotes the rendered TEMPLATE value(s) for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.",
    "{strip}": "Use in form '{strip,TEMPLATE}'; strips whitespace from begining and end of rendered TEMPLATE value(s).",
    "{format}": "Use in form, '{format:TYPE:FORMAT,TEMPLATE}'; converts TEMPLATE value to TYPE then formats the value "
    + "using Python string formatting codes specified by FORMAT; TYPE is one of: 'int', 'float', or 'str'. "
    "For example, '{format:float:.1f,{exiftool:EXIF:FocalLength}}' will format focal length to 1 decimal place (e.g. '100.0'). ",
    "{function}": "Execute a python function from an external file and use return value as template substitution. "
    + "Use in format: {function:file.py::function_name} where 'file.py' is the name of the python file and 'function_name' is the name of the function to call. "
    + "The function will be passed the PhotoInfo object for the photo. "
    + "See https://github.com/RhetTbull/osxphotos/blob/master/examples/template_function.py for an example of how to implement a template function.",
}

FILTER_VALUES = {
    "lower": "Convert value to lower case, e.g. 'Value' => 'value'.",
    "upper": "Convert value to upper case, e.g. 'Value' => 'VALUE'.",
    "strip": "Strip whitespace from beginning/end of value, e.g. ' Value ' => 'Value'.",
    "titlecase": "Convert value to title case, e.g. 'my value' => 'My Value'.",
    "capitalize": "Capitalize first word of value and convert other words to lower case, e.g. 'MY VALUE' => 'My value'.",
    "braces": "Enclose value in curly braces, e.g. 'value => '{value}'.",
    "parens": "Enclose value in parentheses, e.g. 'value' => '(value')",
    "brackets": "Enclose value in brackets, e.g. 'value' => '[value]'",
    "shell_quote": "Quotes the value for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.",
    "function": "Run custom python function to filter value; use in format 'function:/path/to/file.py::function_name'. See example at https://github.com/RhetTbull/osxphotos/blob/master/examples/template_filter.py",
    "split(x)": "Split value into a list of values using x as delimiter, e.g. 'value1;value2' => ['value1', 'value2'] if used with split(;).",
    "autosplit": "Automatically split delimited string into separate values; will split strings delimited by comma, semicolon, or space, e.g. 'value1,value2' => ['value1', 'value2'].",
    "chop(x)": "Remove x characters off the end of value, e.g. chop(1): 'Value' => 'Valu'; when applied to a list, chops characters from each list value, e.g. chop(1): ['travel', 'beach']=> ['trave', 'beac'].",
    "chomp(x)": "Remove x characters from the beginning of value, e.g. chomp(1): ['Value'] => ['alue']; when applied to a list, removes characters from each list value, e.g. chomp(1): ['travel', 'beach']=> ['ravel', 'each'].",
    "sort": "Sort list of values, e.g. ['c', 'b', 'a'] => ['a', 'b', 'c'].",
    "rsort": "Sort list of values in reverse order, e.g. ['a', 'b', 'c'] => ['c', 'b', 'a'].",
    "reverse": "Reverse order of values, e.g. ['a', 'b', 'c'] => ['c', 'b', 'a'].",
    "uniq": "Remove duplicate values, e.g. ['a', 'b', 'c', 'b', 'a'] => ['a', 'b', 'c'].",
    "join(x)": "Join list of values with delimiter x, e.g. join(,): ['a', 'b', 'c'] => 'a,b,c'; "
    + "the DELIM option functions similar to join(x) but with DELIM, the join happens before being passed to any filters."
    + "May optionally be used without an argument, that is 'join()' which joins values together with no delimiter. "
    + "e.g. join(): ['a', 'b', 'c'] => 'abc'.",
    "append(x)": "Append x to list of values, e.g. append(d): ['a', 'b', 'c'] => ['a', 'b', 'c', 'd'].",
    "prepend(x)": "Prepend x to list of values, e.g. prepend(d): ['a', 'b', 'c'] => ['d', 'a', 'b', 'c'].",
    "appends(x)": "Append s[tring] Append x to each value of list of values, e.g. appends(d): ['a', 'b', 'c'] => ['ad', 'bd', 'cd'].",
    "prepends(x)": "Prepend s[tring] x to each value of list of values, e.g. prepends(d): ['a', 'b', 'c'] => ['da', 'db', 'dc'].",
    "remove(x)": "Remove x from list of values, e.g. remove(b): ['a', 'b', 'c'] => ['a', 'c'].",
    "slice(start:stop:step)": "Slice list using same semantics as Python's list slicing, "
    + "e.g. slice(1:3): ['a', 'b', 'c', 'd'] => ['b', 'c']; slice(1:4:2): ['a', 'b', 'c', 'd'] => ['b', 'd']; "
    + "slice(1:): ['a', 'b', 'c', 'd'] => ['b', 'c', 'd']; slice(:-1): ['a', 'b', 'c', 'd'] => ['a', 'b', 'c']; "
    + "slice(::-1): ['a', 'b', 'c', 'd'] => ['d', 'c', 'b', 'a']. See also sslice().",
    "sslice(start:stop:step)": "[s(tring) slice] Slice values in a list using same semantics as Python's string slicing, "
    + "e.g. sslice(1:3):'abcd => 'bc'; sslice(1:4:2): 'abcd' => 'bd', etc. See also slice().",
    "filter(x)": "Filter list of values using predicate x; for example, `{folder_album|filter(contains Events)}` returns only folders/albums containing the word 'Events' in their path.",
    "int": "Convert values in list to integer, e.g. 1.0 => 1. If value cannot be converted to integer, remove value from list. "
    + "['1.1', 'x'] => ['1']. See also float.",
    "float": "Convert values in list to floating point number, e.g. 1 => 1.0. If value cannot be converted to float, remove value from list. "
    + "['1', 'x'] => ['1.0']. See also int.",
}

# Just the substitutions without the braces
SINGLE_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "") for field in TEMPLATE_SUBSTITUTIONS
]

PATHLIB_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "") for field in TEMPLATE_SUBSTITUTIONS_PATHLIB
]

MULTI_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "")
    for field in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
]

FIELD_NAMES = (
    SINGLE_VALUE_SUBSTITUTIONS + MULTI_VALUE_SUBSTITUTIONS + PATHLIB_SUBSTITUTIONS
)

# default values for string manipulation template options
INPLACE_DEFAULT = ","
PATH_SEP_DEFAULT = os.path.sep

# globals for tracking {seq} substitutions
_global_seq_count = 0

PUNCTUATION = {
    "comma": ",",
    "semicolon": ";",
    "pipe": "|",
    "openbrace": "{",
    "closebrace": "}",
    "openparens": "(",
    "closeparens": ")",
    "openbracket": "[",
    "closebracket": "]",
    "questionmark": "?",
    "newline": "\n",
    "lf": "\n",
    "cr": "\r",
    "crlf": "\r\n",
    "tab": "\t",
}


@dataclass
class RenderOptions:
    """Options for PhotoTemplate.render

    template: str template
    none_str: str to use default for None values, default is '_'
    path_sep: optional string to use as path separator, default is os.path.sep
    expand_inplace: expand multi-valued substitutions in-place as a single string
        instead of returning individual strings
    inplace_sep: optional string to use as separator between multi-valued keywords
    with expand_inplace; default is ','
    filename: if True, template output will be sanitized to produce valid file name
    dirname: if True, template output will be sanitized to produce valid directory name
    strip: if True, strips leading/trailing whitespace from rendered templates
    edited_version: set to True if you want {edited_version} to resolve to True (e.g. exporting edited version of photo)
    export_dir: set to the export directory if you want to evaluate {export_dir} template
    dest_path: set to the destination path of the photo (for use by {function} template), only valid with --filename
    filepath: set to value for filepath of the exported photo if you want to evaluate {filepath} template
    quote: quote path templates for execution in the shell
    caller: which command is calling the template (e.g. 'export')
    """

    none_str: str = "_"
    path_sep: Optional[str] = PATH_SEP_DEFAULT
    expand_inplace: bool = False
    inplace_sep: Optional[str] = INPLACE_DEFAULT
    filename: bool = False
    dirname: bool = False
    strip: bool = False
    edited_version: bool = False
    export_dir: Optional[str] = None
    dest_path: Optional[str] = None
    filepath: Optional[str] = None
    quote: bool = False
    caller: str = "export"


class PhotoTemplateParser:
    """Parser for PhotoTemplate"""

    # implemented as Singleton

    def __new__(cls, *args, **kwargs):
        """create new object or return instance of already created singleton"""
        if not hasattr(cls, "instance") or not cls.instance:
            cls.instance = super().__new__(cls)

        return cls.instance

    def __init__(self):
        """return existing singleton or create a new one"""

        if hasattr(self, "metamodel"):
            return

        self.metamodel = metamodel_from_file(MTL_GRAMMAR_MODEL, skipws=False)

    def parse(self, template_statement):
        """Parse a template_statement string"""
        return self.metamodel.model_from_str(template_statement)

    def fields(self, template_statement):
        """Return list of fields found in a template statement; does not verify that fields are valid"""
        model = self.parse(template_statement)
        return [ts.template.field for ts in model.template_strings if ts.template]


class PhotoTemplate:
    """PhotoTemplate class to render a template string from a PhotoInfo object"""

    def __init__(self, photo, exiftool_path=None):
        """Inits PhotoTemplate class with photo

        Args:
            photo: a PhotoInfo instance.
            exiftool_path: optional path to exiftool for use with {exiftool:} template; if not provided, will look for exiftool in $PATH
        """
        self.photo = photo
        self.exiftool_path = exiftool_path

        # holds value of current date/time for {today.x} fields
        # gets initialized in get_template_value
        self.today = None

        # get parser singleton
        self.parser = PhotoTemplateParser()

        # initialize render options
        # this will be done in render() but for testing, some of the lookup functions are called directly
        options = RenderOptions()
        self.options = options
        self.path_sep = options.path_sep
        self.inplace_sep = options.inplace_sep
        self.edited_version = options.edited_version
        self.none_str = options.none_str
        self.expand_inplace = options.expand_inplace
        self.filename = options.filename
        self.dirname = options.dirname
        self.strip = options.strip
        self.export_dir = options.export_dir
        self.filepath = options.filepath
        self.quote = options.quote
        self.dest_path = options.dest_path
        self.variables = {}

    def render(
        self,
        template: str,
        options: RenderOptions,
    ):
        """Render a filename or directory template

        Args:
            template: str template
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """

        if not isinstance(template, str):
            raise TypeError(f"template must be type str, not {type(template)}")

        self.options = options
        self.path_sep = options.path_sep
        self.inplace_sep = options.inplace_sep
        self.edited_version = options.edited_version
        self.none_str = options.none_str
        self.expand_inplace = options.expand_inplace
        self.filename = options.filename
        self.dirname = options.dirname
        self.strip = options.strip
        self.export_dir = options.export_dir
        self.dest_path = options.dest_path
        self.filepath = options.filepath
        self.quote = options.quote
        self.dest_path = options.dest_path

        try:
            model = self.parser.parse(template)
        except TextXSyntaxError as e:
            raise ValueError(f"SyntaxError: {e}") from e

        if not model:
            # empty string
            return [], []

        return self._render_statement(model)

    def _render_statement(
        self,
        statement,
        field_arg=None,
    ):
        results = []
        unmatched = []
        for ts in statement.template_strings:
            results, unmatched = self._render_template_string(
                ts, results=results, unmatched=unmatched, field_arg=field_arg
            )

        rendered_strings = results

        if self.filename:
            rendered_strings = [
                sanitize_filename(rendered_str) for rendered_str in rendered_strings
            ]

        if self.strip:
            rendered_strings = [
                rendered_str.strip() for rendered_str in rendered_strings
            ]

        return rendered_strings, unmatched

    def _render_template_string(
        self,
        ts,
        field_arg,
        results=None,
        unmatched=None,
    ):
        """Render a TemplateString object"""

        results = results or [""]
        unmatched = unmatched or []

        if ts.template:
            # have a template field to process
            field = ts.template.field
            subfield = ts.template.subfield

            # process filters
            filters = []
            if ts.template.filter is not None:
                filters = ts.template.filter.value

            # process field arguments
            if ts.template.fieldarg is not None:
                field_arg = ts.template.fieldarg.value
            else:
                field_arg = None

            # process delim
            if ts.template.delim is not None:
                # if value is None, means format was {+field}
                delim = ts.template.delim.value or ""
                delim = self.expand_variables_to_str(delim, "delim")
            else:
                delim = None

            if ts.template.bool is not None:
                is_bool = True
                if ts.template.bool.value is not None:
                    bool_val, u = self._render_statement(
                        ts.template.bool.value,
                        field_arg=field_arg,
                    )
                    unmatched.extend(u)
                else:
                    # blank bool value
                    bool_val = [""]
            else:
                is_bool = False
                bool_val = None

            # process default
            if ts.template.default is not None:
                # default is also a TemplateString
                if ts.template.default.value is not None:
                    default, u = self._render_statement(
                        ts.template.default.value,
                        field_arg=field_arg,
                    )
                    unmatched.extend(u)
                else:
                    # blank default value
                    default = [""]
            else:
                default = []

            # process conditional
            if ts.template.conditional is not None:
                operator = ts.template.conditional.operator
                negation = ts.template.conditional.negation
                if ts.template.conditional.value is not None:
                    # conditional value is also a TemplateString
                    conditional_value = []
                    for cv in ts.template.conditional.value:
                        value, u = self._render_statement(cv)
                        conditional_value += value
                        unmatched.extend(u)
                else:
                    # this shouldn't happen
                    conditional_value = [""]
            else:
                operator = None
                negation = None
                conditional_value = []

            if field.startswith("%"):
                # variable in form {%var}
                vals = self.variables.get(field[1:], None)
                if vals is None:
                    raise SyntaxError(f"Variable '{field[1:]}' is not defined.")
            elif field == "var":
                if not subfield or not default:
                    raise SyntaxError(
                        "var must have a subfield and value in form {var:subfield,value}"
                    )
                self.variables[subfield] = default
                vals = []
            else:
                vals, u = self.get_field_values(field, subfield, field_arg, default)
                if u:
                    unmatched.extend(u)
                    return [], unmatched

            vals = [val for val in vals if val is not None]

            if self.expand_inplace or delim is not None:
                sep = delim if delim is not None else self.inplace_sep
                vals = [sep.join(vals)] if vals else []

            for filter_ in filters:
                vals = self.get_filter_values(filter_, vals)

            # process find/replace
            if ts.template.findreplace:
                new_vals = []
                for val in vals:
                    for pair in ts.template.findreplace.pairs:
                        find = pair.find or ""
                        find = self.expand_variables_to_str(find, "find/replace")
                        repl = pair.replace or ""
                        repl = self.expand_variables_to_str(repl, "find/replace")
                        val = val.replace(find, repl)
                    new_vals.append(val)
                vals = new_vals

            if operator:
                # have a conditional operator

                def string_test(test_function):
                    """Perform string comparison using test_function; closure to capture conditional_value, vals, negation"""
                    match = False
                    for c in conditional_value:
                        for v in vals:
                            if test_function(v, c):
                                match = True
                                break
                        if match:
                            break

                    return (
                        ["True"]
                        if (match and not negation) or (negation and not match)
                        else []
                    )

                def comparison_test(test_function):
                    """Perform numerical comparisons using test_function; closure to capture conditional_val, vals, negation"""
                    # returns True if any of the values match the condition
                    if len(conditional_value) != 1:
                        raise SyntaxError(
                            f"comparison operators may only be used with a single conditional value: {conditional_value}"
                        )
                    try:
                        match = any(
                            bool(test_function(float(v), float(conditional_value[0])))
                            for v in vals
                        )
                        return (
                            ["True"]
                            if (match and not negation) or (negation and not match)
                            else []
                        )
                    except ValueError as e:
                        raise SyntaxError(
                            f"comparison operators may only be used with values that can be converted to numbers: {vals} {conditional_value}"
                        ) from e

                if operator in ["contains", "matches", "startswith", "endswith"]:
                    # process any "or" values separated by "|"
                    temp_values = []
                    for c in conditional_value:
                        temp_values.extend(c.split("|"))
                    conditional_value = temp_values

                if operator == "contains":
                    vals = string_test(lambda v, c: c in v)
                elif operator == "matches":
                    vals = string_test(lambda v, c: v == c)
                elif operator == "startswith":
                    vals = string_test(lambda v, c: v.startswith(c))
                elif operator == "endswith":
                    vals = string_test(lambda v, c: v.endswith(c))
                elif operator == "==":
                    match = sorted(vals) == sorted(conditional_value)
                    vals = (
                        ["True"]
                        if (match and not negation) or (negation and not match)
                        else []
                    )
                elif operator == "!=":
                    match = sorted(vals) != sorted(conditional_value)
                    vals = (
                        ["True"]
                        if (match and not negation) or (negation and not match)
                        else []
                    )
                elif operator == "<":
                    vals = comparison_test(lambda v, c: v < c)
                elif operator == "<=":
                    vals = comparison_test(lambda v, c: v <= c)
                elif operator == ">":
                    vals = comparison_test(lambda v, c: v > c)
                elif operator == ">=":
                    vals = comparison_test(lambda v, c: v >= c)

            if is_bool:
                vals = default if not vals else bool_val
            elif not vals and field != "var":
                # don't assign default value if the template was variable assignment
                vals = default or [self.none_str]

            pre = ts.pre or ""
            post = ts.post or ""

            rendered = [pre + str(val) + post for val in vals]
            results_new = []
            for ren in rendered:
                for res in results:
                    res_new = res + ren
                    results_new.append(res_new)
            results = results_new

        else:
            # no template
            pre = ts.pre or ""
            post = ts.post or ""
            results = [r + pre + post for r in results]

        return results, unmatched

    def expand_variables_to_str(self, value: str, name: str) -> str:
        """
        Expand variables in value and return a str of the expanded value.
        Enforce that the expanded value is a single value, raises ValueError if not.

        Args:
            value: the value to expand
            name: the name of the value being expanded (used in error messages)
        """
        expanded = self.expand_variables(value)
        if len(expanded) != 1:
            raise SyntaxError(f"{name} must have a single value, not {expanded}")
        return expanded[0]

    def expand_variables(self, value: str) -> List[str]:
        """Expand variables in value"""
        # replace any variables with their values
        values = [value]
        new_values = []
        # allow %% to escape %, match variables in form %var
        variable_match = re.compile(r"(?:%%)*(%[\w]+)?")
        while True:
            for value in values:
                match = variable_match.search(value)
                if not match or not match[1]:
                    break
                var = match[1]
                var_name = var[1:]
                if var_name not in self.variables:
                    raise SyntaxError(f"Variable '{var_name}' is not defined.")
                for val in values:
                    for var_val in self.variables[var_name]:
                        new_values.append(
                            re.sub(f"(%%)*{var}", r"\g<1>" + var_val, val)
                        )
            if new_values == values or not new_values:
                break
            values = new_values.copy()
            new_values = []

        # replace %% with %
        # any %% left in the string will be replaced with %
        values = [value.replace("%%", "%") for value in values]

        return values

    def get_field_values(
        self,
        field: str,
        subfield: Optional[str],
        field_arg: Optional[str],
        default: List[str],
    ) -> Tuple[List[str], List[str]]:
        """Get the values for a field"""
        vals = []
        unmatched = []
        if (
            field in SINGLE_VALUE_SUBSTITUTIONS
            or field.split(".")[0] in SINGLE_VALUE_SUBSTITUTIONS
        ):
            vals = self.get_template_value(
                field,
                default=default,
                subfield=subfield,
                field_arg=field_arg,
            )
        elif field == "exiftool":
            if subfield is None:
                raise ValueError(
                    "SyntaxError: GROUP:NAME subfield must not be null with {exiftool:GROUP:NAME}'"
                )
            vals = self.get_template_value_exiftool(
                subfield,
            )
        elif field == "function":
            if subfield is None:
                raise ValueError(
                    "SyntaxError: filename and function must not be null with {function::filename.py:function_name}"
                )
            vals = self.get_template_value_function(
                subfield, field_arg, self.options.caller
            )
        elif field in MULTI_VALUE_SUBSTITUTIONS or field.startswith("photo"):
            vals = self.get_template_value_multi(
                field, subfield, path_sep=field_arg, default=default
            )
        elif field.split(".")[0] in PATHLIB_SUBSTITUTIONS:
            vals = self.get_template_value_pathlib(field)
        else:
            unmatched.append(field)
            return [], unmatched
        return vals, unmatched

    def get_template_value(
        self,
        field: str,
        default: List[str],
        subfield: Optional[str],
        field_arg: Optional[str],
    ):
        """lookup value for template field (single-value template substitutions)

        Args:
            field: template field to find value for.
            default: the default value provided by the user
            bool_val: True value if expression is boolean
            delim: delimiter for expand in place
            path_sep: path separator for fields that are path-like
            subfield: subfield (value after : in field)

        Returns:
            The matching template value (which may be None).

        Raises:
            ValueError if no rule exists for field.
        """

        # initialize today with current date/time if needed
        if self.today is None:
            self.today = datetime.datetime.now()

        value = None

        # wouldn't a switch/case statement be nice...
        # handle the fields that don't require a PhotoInfo object first
        if field.startswith("today"):
            value = format_date_field(self.today, field, default)
        elif field in PUNCTUATION:
            value = PUNCTUATION[field]
        elif field == "osxphotos_version":
            value = __version__
        elif field == "osxphotos_cmd_line":
            value = " ".join(sys.argv)
        elif self.photo.uuid is None:
            # if no uuid, don't have a PhotoInfo object (could be PhotoInfoNone)
            # so don't try to handle any of the photo fields
            return []
        elif field == "name":
            value = pathlib.Path(self.photo.filename).stem
        elif field == "original_name":
            value = pathlib.Path(self.photo.original_filename).stem
        elif field == "title":
            value = self.photo.title
        elif field == "descr":
            value = self.photo.description
        elif field == "media_type":
            value = self.get_media_type(default)
        elif field == "photo_or_video":
            value = self.get_photo_video_type(default)
        elif field == "hdr":
            value = "hdr" if self.photo.hdr else None
        elif field == "edited":
            value = "edited" if self.photo.hasadjustments else None
        elif field == "edited_version":
            value = "edited_version" if self.edited_version else None
        elif field == "favorite":
            value = "favorite" if self.photo.favorite else None
        elif field.startswith("created"):
            value = format_date_field(self.photo.date, field, default)
        elif field.startswith("modified"):
            # if no modified date, use photo.date
            value = format_date_field(
                self.photo.date_modified or self.photo.date, field, default
            )
        elif field.startswith("place"):
            value = get_place_value(self.photo, field)
        elif field == "searchinfo.season":
            value = self.photo.search_info.season if self.photo.search_info else None
        elif field == "exif.camera_make":
            value = self.photo.exif_info.camera_make if self.photo.exif_info else None
        elif field == "exif.camera_model":
            value = self.photo.exif_info.camera_model if self.photo.exif_info else None
        elif field == "exif.lens_model":
            value = self.photo.exif_info.lens_model if self.photo.exif_info else None
        elif field == "moment":
            value = self.photo.moment_info.title if self.photo.moment_info else None
        elif field == "uuid":
            value = self.photo.uuid
        elif field == "shortuuid":
            value = uuid_to_shortuuid(self.photo.uuid) if self.photo.uuid else None
        elif field == "id":
            value = format_str_value(self.photo._info["pk"], subfield)
        elif field.startswith("album_seq") or field.startswith("folder_album_seq"):
            if dest_path := self.dest_path:
                if field.startswith("album_seq"):
                    album = pathlib.Path(dest_path).name
                    album_info = _get_album_by_name(self.photo, album)
                else:
                    album_info = _get_album_by_path(self.photo, dest_path)
                value = album_info.photo_index(self.photo) if album_info else None
            else:
                value = None
            if value is not None:
                start_id = int(field_arg) if field_arg is not None else 0
                value = int(value) + start_id
                value = format_str_value(value, subfield)
        elif field.startswith("counter"):
            value = counter.get_counter_value(field, subfield, field_arg)
        else:
            # if here, didn't get a match
            raise ValueError(f"Unhandled template value: {field}")

        # sanitize filename or directory name if needed
        if self.filename:
            value = sanitize_pathpart(value)
        elif self.dirname:
            value = sanitize_dirname(value)

        # ensure no empty strings in value (see #512)
        value = None if value == "" else value

        return [value]

    def get_template_value_pathlib(self, field):
        """lookup value for template pathlib template fields

        Args:
            field: template field to find value for.

        Returns:
            The matching template value (which may be None).

        Raises:
            ValueError if no rule exists for field.
        """
        field_stem = field.split(".")[0]
        if field_stem not in PATHLIB_SUBSTITUTIONS:
            raise ValueError(f"SyntaxError: Unknown field: {field}")

        field_value = None
        try:
            field_value = getattr(self, field_stem)
        except AttributeError as e:
            raise ValueError(f"Unknown path-like field: {field_stem}") from e

        value = _get_pathlib_value(field, field_value, self.quote)

        if self.filename:
            value = sanitize_pathpart(value)
        elif self.dirname:
            value = sanitize_dirname(value)

        return [value]

    def get_filter_values(self, filter_: str, values: List[str]) -> List[str]:
        """Return filtered values"""

        # extract args, if any
        if re.search(r"\(.*\)", filter_):
            filter_, args = filter_.split("(", 1)
            args = args.rstrip(")")
            args = self.expand_variables_to_str(args, "Filter arguments")
        else:
            args = None

        # check that filter name (without subfields or arguments) is valid
        valid_filters = [f.split("(")[0] for f in FILTER_VALUES]
        if filter_.split(":")[0] not in valid_filters:
            raise SyntaxError(f"Unknown filter: {filter_}")

        if filter_ in [
            "append",
            "appends",
            "chomp",
            "chop",
            "filter",
            "prepend",
            "prepends",
            "remove",
            "slice",
            "split",
            "sslice",
        ] and (args is None or not len(args)):
            raise SyntaxError(f"{filter_} requires arguments")

        if filter_ == "lower":
            value = [v.lower() for v in values]
        elif filter_ == "upper":
            value = [v.upper() for v in values]
        elif filter_ == "strip":
            value = [v.strip() for v in values]
        elif filter_ == "capitalize":
            value = [v.capitalize() for v in values]
        elif filter_ == "titlecase":
            value = [v.title() for v in values]
        elif filter_ == "braces":
            value = ["{" + v + "}" for v in values]
        elif filter_ == "parens":
            value = [f"({v})" for v in values]
        elif filter_ == "brackets":
            value = [f"[{v}]" for v in values]
        elif filter_ == "shell_quote":
            value = [shlex.quote(v) for v in values]
        elif filter_ == "split":
            if delim := args:
                new_values = []
                for v in values:
                    new_values.extend(v.split(delim))
                value = new_values
            else:
                value = values
        elif filter_ == "chop":
            # chop off characters from the end
            try:
                chop = int(args)
            except ValueError as e:
                raise SyntaxError(f"Invalid value for chop: {args}") from e
            value = [v[:-chop] for v in values] if chop else values
        elif filter_ == "chomp":
            # chop off characters from the beginning
            try:
                chomp = int(args)
            except ValueError as e:
                raise SyntaxError(f"Invalid value for chomp: {args}") from e
            value = [v[chomp:] for v in values] if chomp else values
        elif filter_ == "autosplit":
            # try to split keyword strings automatically
            temp_values = [v.replace(",", " ") for v in values]
            temp_values = [v.replace(";", " ") for v in temp_values]
            value = []
            for val in temp_values:
                value.extend(val.split())
        elif filter_ == "sort":
            # sort list of values
            value = sorted(values)
        elif filter_ == "rsort":
            # reverse sort list of values
            value = sorted(values, reverse=True)
        elif filter_ == "reverse":
            # reverse list of values
            value = values[::-1]
        elif filter_ == "uniq":
            # remove duplicate values from list
            temp_values = []
            for v in values:
                if v not in temp_values:
                    temp_values.append(v)
            value = temp_values
        elif filter_ == "join":
            # join list of values with delimiter
            delim = args or ""
            value = [delim.join(values)]
        elif filter_ == "append":
            # append value to list
            value = values + [args]
        elif filter_ == "prepend":
            # prepend value to list
            value = [args] + values
        elif filter_ == "appends":
            # append value to each item in list
            value = [f"{v}{args}" for v in values]
        elif filter_ == "prepends":
            # prepend value to each item in list
            value = [f"{args}{v}" for v in values]
        elif filter_ == "remove":
            # remove value from list
            value = [v for v in values if v != args]
        elif filter_ == "slice":
            # slice list of values
            value = values[create_slice(args)]
        elif filter_ == "sslice":
            # slice each value in a list
            slice_ = create_slice(args)
            value = [v[slice_] for v in values]
        elif filter_ == "filter":
            # filter values based on a predicate
            value = [v for v in values if self.filter_predicate(v, args)]
        elif filter_ == "int":
            # convert value to integer
            value = values_to_int(values)
        elif filter_ == "float":
            # convert value to float
            value = values_to_float(values)
        elif filter_.startswith("function:"):
            value = self.get_template_value_filter_function(filter_, args, values)
        else:
            value = []
        return value

    def filter_predicate(self, value: str, args: str) -> bool:
        """Return True if value passes predicate"""

        # extract function name and arguments
        if not args:
            raise SyntaxError("Filter predicate requires arguments")
        args = args.split(None, 1)
        if args[0] == "not":
            args = args[1:]
            return not self.filter_predicate(value, " ".join(args))

        predicate = args[0]
        conditional_value = args[1].split("|")

        def comparison_test(test_function):
            """Perform numerical comparisons using test_function"""
            # returns True if any of the values match the condition
            try:
                return any(
                    bool(test_function(float(value), float(c)))
                    for c in conditional_value
                )
            except ValueError as e:
                raise SyntaxError(
                    f"comparison operators may only be used with values that can be converted to numbers: {value} {conditional_value}"
                ) from e

        predicate_is_true = False
        if predicate == "contains":
            predicate_is_true = any(c in value for c in conditional_value)
        elif predicate == "endswith":
            predicate_is_true = any(value.endswith(c) for c in conditional_value)
        elif predicate in ["matches", "=="]:
            predicate_is_true = any(value == c for c in conditional_value)
        elif predicate == "startswith":
            predicate_is_true = any(value.startswith(c) for c in conditional_value)
        elif predicate == "!=":
            predicate_is_true = any(value != c for c in conditional_value)
        elif predicate == "<":
            predicate_is_true = comparison_test(lambda v, c: v < c)
        elif predicate == "<=":
            predicate_is_true = comparison_test(lambda v, c: v <= c)
        elif predicate == ">":
            predicate_is_true = comparison_test(lambda v, c: v > c)
        elif predicate == ">=":
            predicate_is_true = comparison_test(lambda v, c: v >= c)
        else:
            raise SyntaxError(f"Invalid predicate: {predicate}")

        return predicate_is_true

    def get_template_value_multi(self, field, subfield, path_sep, default):
        """lookup value for template field (multi-value template substitutions)

        Args:
            field: template field to find value for.
            subfield: the template subfield value
            path_sep: path separator to use for folder_album field
            default: value of default field

        Returns:
            List of the matching template values or [].

        Raises:
            ValueError if no rule exists for field.
        """

        """ return list of values for a multi-valued template field """

        path_sep = path_sep or self.path_sep

        if self.photo.uuid is None:
            return []

        values = []
        if field == "album":
            values = self.photo.burst_albums if self.photo.burst else self.photo.albums
        elif field == "project":
            values = [p.title for p in self.photo.project_info]
        elif field == "album_project":
            values = self.photo.burst_albums if self.photo.burst else self.photo.albums
            values += [p.title for p in self.photo.project_info]
        elif field == "keyword":
            values = sorted(self.photo.keywords) if self.photo.keywords else []
        elif field == "person":
            values = sorted(self.photo.persons) if self.photo.persons else []
            # remove any _UNKNOWN_PERSON values
            values = [val for val in values if val != _UNKNOWN_PERSON]
        elif field == "label":
            values = sorted(self.photo.labels) if self.photo.labels else []
        elif field == "label_normalized":
            values = (
                sorted(self.photo.labels_normalized)
                if self.photo.labels_normalized
                else []
            )
        elif field in ["folder_album", "folder_album_project"]:
            values = []
            # photos must be in an album to be in a folder
            if self.photo.burst:
                album_info = self.photo.burst_album_info
            else:
                album_info = self.photo.album_info
            if field == "folder_album_project":
                album_info += self.photo.project_info
            for album in album_info:
                if album.folder_names:
                    # album in folder
                    if self.dirname:
                        # being used as a filepath so sanitize each part
                        folder = path_sep.join(
                            sanitize_dirname(f) for f in album.folder_names
                        )
                        folder += path_sep + sanitize_dirname(album.title)
                    else:
                        folder = path_sep.join(album.folder_names)
                        folder += path_sep + album.title
                    values.append(folder)
                elif self.dirname:
                    values.append(sanitize_dirname(album.title))
                else:
                    values.append(album.title)
            values = sorted(values)
        elif field == "comment":
            values = [
                f"{comment.user}: {comment.text}" for comment in self.photo.comments
            ]
        elif field == "searchinfo.holiday":
            values = self.photo.search_info.holidays if self.photo.search_info else []
        elif field == "searchinfo.activity":
            values = self.photo.search_info.activities if self.photo.search_info else []
        elif field == "searchinfo.venue":
            values = self.photo.search_info.venues if self.photo.search_info else []
        elif field == "searchinfo.venue_type":
            values = (
                self.photo.search_info.venue_types if self.photo.search_info else []
            )
        elif field == "shell_quote":
            values = [shlex.quote(v) for v in default if v]
        elif field == "strip":
            values = [v.strip() for v in default]
        elif field == "format":
            values = self.get_format_values(field, subfield, default)
        elif field.startswith("photo"):
            # provide access to PhotoInfo object
            properties = field.split(".")
            if len(properties) <= 1:
                raise ValueError(
                    "Missing property in {photo} template.  Use in form {photo.property}."
                )
            obj = self.photo
            for i in range(1, len(properties)):
                property_ = properties[i]
                try:
                    obj = getattr(obj, property_)
                    if obj is None:
                        break
                except AttributeError as e:
                    raise ValueError(
                        "Invalid property for {photo} template: " + f"'{property_}'"
                    ) from e

            if obj is None:
                values = []
            elif isinstance(obj, bool):
                values = [property_] if obj else []
            elif isinstance(obj, (str, int, float)):
                values = [str(obj)]
            else:
                try:
                    values = [str(o) for o in obj]
                except TypeError:
                    values = [str(obj)]
        elif field == "detected_text":
            values = _get_detected_text(self.photo, confidence=subfield)
        else:
            raise ValueError(f"Unhandled template value: {field}")

        # sanitize directory names if needed, folder_album handled differently above
        if self.filename:
            values = [sanitize_pathpart(value) for value in values]
        elif self.dirname and field not in ["folder_album", "folder_album_project"]:
            # skip folder_album because it would have been handled above
            values = [sanitize_dirname(value) for value in values]

        # If no values, insert None so code below will substitute none_str for None
        values = values or []
        return values

    def get_format_values(
        self, field: str, subfield: str, default: List[str]
    ) -> Optional[List[Optional[str]]]:
        """Return values for {format} templates"""

        if field != "format":
            raise ValueError(f"Unhandled template value in get_format_values: {field}")

        if not subfield or ":" not in subfield:
            raise SyntaxError("{format} requires subfield in form TYPE:FORMAT")
        type_, format_str = subfield.split(":", 1)
        if type_ not in ("int", "float", "str"):
            raise SyntaxError(
                f"'{type_}' is not a valid type for {format}: must be one of 'int', 'float', 'str'"
            )
        if type_ == "int":
            # convert to float then int to avoid error when converting a string float to int
            default_ = [int(float(v)) for v in default]
        elif type_ == "float":
            default_ = [float(v) for v in default]
        else:
            default_ = default
        format_str = self.expand_variables_to_str(format_str, "format string")
        return [format_str_value(v, format_str) for v in default_]

    def get_template_value_exiftool(
        self,
        subfield,
    ):
        """Get template value for format "{exiftool:EXIF:Model}" """

        if self.photo is None:
            return []

        if not self.photo.path:
            return []

        exif = ExifToolCaching(self.photo.path, exiftool=self.exiftool_path)
        exifdict = exif.asdict(normalized=True)
        subfield = subfield.lower()
        if subfield in exifdict:
            values = exifdict[subfield]
            values = values if isinstance(values, list) else [values]
            values = [str(v) for v in values]

            # sanitize directory names if needed
            if self.filename:
                values = [sanitize_pathpart(value) for value in values]
            elif self.dirname:
                values = [sanitize_dirname(value) for value in values]
        else:
            values = []

        return values

    def get_template_value_function(
        self,
        subfield: str,
        field_arg: Optional[str],
        caller: str,
    ):
        """Get template value from external function

        Args:
            subfield: the filename and function name in for filename.py::function
            field_arg: the argument to pass to the function
            caller: the calling source of the template ('export' or 'import')
        """

        if "::" not in subfield:
            raise ValueError(
                f"SyntaxError: could not parse function name from '{subfield}'"
            )

        filename, funcname = subfield.split("::")

        filename_validated = expand_and_validate_filepath(filename)
        if not filename_validated:
            raise ValueError(f"'{filename}' does not appear to be a file")

        template_func = load_function(filename_validated, funcname)
        if self.photo.uuid is None:
            # must be a PhotoInfoNone instance
            # if no uuid, then template is being validated but not actually run
            # so don't run the function
            values = []
        elif caller in {"export", "query"}:
            # function signature is:
            # def example(photo: PhotoInfo, options: ExportOptions, args: Optional[str] = None, **kwargs) -> Union[List, str]:
            values = template_func(self.photo, options=self.options, args=field_arg)
        elif caller == "import":
            # function signature is:
            # def example(filepath: pathlib.Path, args: Optional[str] = None, **kwargs) -> Union[List, str]:
            # the PhotoInfoFromFile class used by import sets `path` to the path of the file being imported
            values = template_func(pathlib.Path(self.photo.path), args=field_arg)
        else:
            raise ValueError(f"Unhandled caller: {caller}")

        if not isinstance(values, (str, list)):
            raise TypeError(
                f"Invalid return type for function {funcname}: expected str or list"
            )
        if isinstance(values, str):
            values = [values]

        # sanitize directory names if needed
        if self.filename:
            values = [sanitize_pathpart(value) for value in values]
        elif self.dirname:
            # sanitize but don't replace any "/" as user function may want to create sub directories
            values = [sanitize_dirname(value, replacement=None) for value in values]

        return values

    def get_template_value_filter_function(self, filter_, args, values):
        """Filter template value from external function"""
        # TODO: add args to filter function call? Would change signature of function

        filter_ = filter_.replace("function:", "")

        if "::" not in filter_:
            raise ValueError(
                f"SyntaxError: could not parse function name from '{filter_}'"
            )

        filename, funcname = filter_.split("::")

        filename_validated = expand_and_validate_filepath(filename)
        if not filename_validated:
            raise ValueError(f"'{filename}' does not appear to be a file")

        template_func = load_function(filename_validated, funcname)

        if not isinstance(values, (list, tuple)):
            values = [values]

        if self.photo.uuid is not None:
            # if uuid is None, it's a PhotoInfoNone instance and template is being validated
            # so don't run the function
            values = template_func(values)

        if not isinstance(values, list):
            raise TypeError(
                f"Invalid return type for function {funcname}: expected list"
            )

        return values

    def get_photo_video_type(self, default):
        """return media type, e.g. photo or video"""
        default_dict = parse_default_kv(default, PHOTO_VIDEO_TYPE_DEFAULTS)
        return default_dict["photo"] if self.photo.isphoto else default_dict["video"]

    def get_media_type(self, default):
        """return special media type, e.g. slow_mo, panorama, etc., defaults to photo or video if no special type"""
        default_dict = parse_default_kv(default, MEDIA_TYPE_DEFAULTS)
        p = self.photo
        if p.selfie:
            return default_dict["selfie"]
        elif p.time_lapse:
            return default_dict["time_lapse"]
        elif p.panorama:
            return default_dict["panorama"]
        elif p.slow_mo:
            return default_dict["slow_mo"]
        elif p.screenshot:
            return default_dict["screenshot"]
        elif p.portrait:
            return default_dict["portrait"]
        elif p.live_photo:
            return default_dict["live_photo"]
        elif p.burst:
            return default_dict["burst"]
        elif p.ismovie:
            return default_dict["video"]
        else:
            return default_dict["photo"]

    def get_photo_bool_attribute(self, attr, default, bool_val):
        """Return the boolean value for a photo attribute"""
        return bool_val if (val := getattr(self.photo, attr)) else default


def parse_default_kv(default, default_dict):
    """parse a string in form key1=value1;key2=value2,... as used for some template fields

    Args:
        default: str, in form 'photo=foto;video=vidéo'
        default_dict: dict, in form {"photo": "fotos", "video": "vidéos"} with default values

    Returns:
        dict in form {"photo": "fotos", "video": "vidéos"}
    """

    default_dict_ = default_dict.copy()
    if default:
        defaults = default[0].split(";")
        for kv in defaults:
            try:
                k, v = kv.split("=")
                k = k.strip()
                v = v.strip()
                default_dict_[k] = v
            except ValueError:
                pass
    return default_dict_


def get_template_help():
    """Return help for template system as markdown string"""
    # TODO: would be better to use importlib.abc.ResourceReader but I can't find a single example of how to do this
    help_file = pathlib.Path(__file__).parent / "phototemplate.md"
    with open(help_file, "r") as fd:
        md = fd.read()
    return md


def get_template_field_table():
    """Return markdown table of template field substitutions"""
    template_table = "| Field | Description |" + "\n|--------------|-------------|"
    for subst, descr in [
        *TEMPLATE_SUBSTITUTIONS.items(),
        *TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items(),
    ]:
        # replace '|' with '\|' to avoid markdown parsing issues (e.g. in {pipe} description)
        descr = descr.replace("'|'", r"'\|'")
        template_table += f"\n|{subst}|{descr}|"
    return template_table


def _get_pathlib_value(field, value, quote):
    """Get the value for a pathlib.Path type template

    Args:
        field: the path field, e.g. "filename.stem"
        value: the value for the path component
        quote: bool; if true, quotes the returned path for safe execution in the shell
    """
    parts = field.split(".")

    if len(parts) == 1:
        return shlex.quote(str(value)) if quote else str(value)

    path = pathlib.Path(value)
    for attribute in parts[1:]:
        try:
            val = getattr(path, attribute)
            path = pathlib.Path(val)
        except AttributeError as e:
            raise ValueError(f"Illegal value for filepath template: {attribute}") from e

    val_str = str(val)
    if quote:
        val_str = shlex.quote(val_str)
    return val_str


def format_str_value(value, format_str):
    """Format value based on format code in field in format id:02d"""
    if not format_str:
        return str(value)
    format_str = "{0:" + f"{format_str}" + "}"
    return format_str.format(value)


def _get_album_by_name(photo, album):
    """Finds first album named album that photo is in and returns the AlbumInfo object, otherwise returns None"""
    return next(
        (album_info for album_info in photo.album_info if album_info.title == album),
        None,
    )


def _get_album_by_path(photo, folder_album_path):
    """finds the first album whose folder_album path matches and folder_album_path and returns the AlbumInfo object, otherwise, returns None"""
    for album_info in photo.album_info:
        # following code is how {folder_album} builds the folder path
        folder = "/".join(sanitize_dirname(f) for f in album_info.folder_names)
        folder += f"/{sanitize_dirname(album_info.title)}"
        if folder_album_path.endswith(folder):
            return album_info
    return None


def _get_detected_text(photo, confidence=TEXT_DETECTION_CONFIDENCE_THRESHOLD):
    """Returns the detected text for a photo
    {detected_text} uses this instead of PhotoInfo.detected_text() to cache the text for all confidence values
    """
    if not photo.isphoto:
        return []

    confidence = (
        float(confidence)
        if confidence is not None
        else TEXT_DETECTION_CONFIDENCE_THRESHOLD
    )

    # _detected_text caches the text detection results in an extended attribute
    # so the first time this gets called is slow but repeated accesses are fast
    detected_text = photo._detected_text()
    return [text for text, conf in detected_text if conf >= confidence]


def create_slice(args):
    """Create a slice object from a string of args in form "start:end:step" """
    slice_args = args.split(":")
    if len(slice_args) == 1:
        start = int(slice_args[0] or 0)
        end = None
        step = None
    elif len(slice_args) == 2:
        start, end = slice_args
        start = int(start) if start != "" else None
        end = int(end) if end != "" else None
        step = None
    elif len(slice_args) == 3:
        start, end, step = slice_args
        start = int(start) if start != "" else None
        end = int(end) if end != "" else None
        step = int(step) if step != "" else None
    else:
        raise SyntaxError(f"Invalid slice: {args}")
    return slice(start, end, step)


def values_to_int(values: List[str]) -> List[str]:
    """Convert a list of strings to str representation of ints, if possible, otherwise strip values from list"""
    int_values = []
    for v in values:
        with suppress(ValueError):
            int_values.append(str(int(float(v))))
    return int_values


def values_to_float(values: List[str]) -> List[str]:
    """Convert a list of strings to str representation of float, if possible, otherwise strip values from list"""
    float_values = []
    for v in values:
        with suppress(ValueError):
            float_values.append(str(float(v)))
    return float_values


def format_date_field(dt: datetime.datetime, field: str, args: List[str]) -> str:
    """Format a date template field in format 'created', 'create.year' etc.

    Args:
        dt: datetime object
        field: the field to format, e.g. 'created.year', 'today.strftime'
        args: the argument to the field, e.g. '%Y' for strftime
    """
    fields = field.split(".")
    if len(fields) == 1:
        # no subfield, just return the formatted date str
        return dt.date().isoformat()
    if len(fields) > 2:
        raise ValueError(f"Unhandled template value: {field}")
    subfield = fields[1]
    if subfield == "strftime":
        if not args:
            return None
        try:
            return dt.strftime(args[0])
        except:
            raise ValueError(f"Invalid strftime template: '{args}'")
    else:
        try:
            return getattr(DateTimeFormatter(dt), subfield)
        except AttributeError as e:
            raise ValueError(f"Unhandled template value: {field}") from e


def get_place_value(photo: "PhotoInfo", field: str):  # noqa: F821
    """Get the value of a 'place' field by attribute

    Args:
        photo: the PhotoInfo object
        field: the field to get, e.g. 'place.name'
    """
    if not photo.place:
        return None

    fields = field.split(".")
    if len(fields) < 2:
        raise ValueError(f"Invalid place field: {field}")
    subfields = fields[1:]
    if subfields[0] in ["name", "country_code"] and len(subfields) == 1:
        return getattr(photo.place, subfields[0]) or None
    elif subfields[0] == "name" and len(subfields) > 1:
        if subfields[1] == "country":
            return photo.place.names.country[0] if photo.place.names.country else None
        elif subfields[1] == "state_province":
            return (
                photo.place.names.state_province[0]
                if photo.place.names.state_province
                else None
            )
        elif subfields[1] == "city":
            return photo.place.names.city[0] if photo.place.names.city else None
        elif subfields[1] == "area_of_interest":
            return (
                photo.place.names.area_of_interest[0]
                if photo.place.names.area_of_interest
                else None
            )
    elif subfields[0] == "address":
        if len(subfields) == 1:
            return photo.place.address_str
        elif subfields[1] in [
            "street",
            "city",
            "state_province",
            "postal_code",
            "country",
        ]:
            return getattr(photo.place.address, subfields[1]) or None
        elif subfields[1] == "country_code":
            return photo.place.address.iso_country_code or None
    # did not find a match
    raise ValueError(f"Unhandled template value: {field}")
