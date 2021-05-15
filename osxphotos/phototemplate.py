""" Custom template system for osxphotos, implements osxphotos template language (OTL) """

import datetime
import locale
import os
import pathlib
import sys

from textx import TextXSyntaxError, metamodel_from_file

from ._constants import _UNKNOWN_PERSON
from ._version import __version__
from .datetime_formatter import DateTimeFormatter
from .exiftool import ExifToolCaching
from .path_utils import sanitize_dirname, sanitize_filename, sanitize_pathpart
from .utils import load_function

# ensure locale set to user's locale
locale.setlocale(locale.LC_ALL, "")

OTL_GRAMMAR_MODEL = str(pathlib.Path(__file__).parent / "phototemplate.tx")

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
    "{uuid}": "Photo's internal universally unique identifier (UUID) for the photo, a 36-character string unique to the photo, e.g. '128FB4C6-0B16-4E7D-9108-FB2E90DA1546'",
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
    "{crlf}": r"a carriage return + line feed: '\r\n'",
    "{osxphotos_version}": f"The osxphotos version, e.g. '{__version__}'",
    "{osxphotos_cmd_line}": "The full command line used to run osxphotos"
}

# Permitted multi-value substitutions (each of these returns None or 1 or more values)
TEMPLATE_SUBSTITUTIONS_MULTI_VALUED = {
    "{album}": "Album(s) photo is contained in",
    "{folder_album}": "Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder",
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
    "function": "Run custom python function to filter value; use in format 'function:/path/to/file.py::function_name'. See example at https://github.com/RhetTbull/osxphotos/blob/master/examples/template_filter.py"
}

# Just the substitutions without the braces
SINGLE_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "") for field in TEMPLATE_SUBSTITUTIONS
]

# Just the multi-valued substitution names without the braces
MULTI_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "")
    for field in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
]

FIELD_NAMES = SINGLE_VALUE_SUBSTITUTIONS + MULTI_VALUE_SUBSTITUTIONS

# default values for string manipulation template options
INPLACE_DEFAULT = ","
PATH_SEP_DEFAULT = os.path.sep

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
}


class PhotoTemplateParser:
    """Parser for PhotoTemplate """

    # implemented as Singleton

    def __new__(cls, *args, **kwargs):
        """ create new object or return instance of already created singleton """
        if not hasattr(cls, "instance") or not cls.instance:
            cls.instance = super().__new__(cls)

        return cls.instance

    def __init__(self):
        """ return existing singleton or create a new one """

        if hasattr(self, "metamodel"):
            return

        self.metamodel = metamodel_from_file(OTL_GRAMMAR_MODEL, skipws=False)

    def parse(self, template_statement):
        """Parse a template_statement string """
        return self.metamodel.model_from_str(template_statement)


class PhotoTemplate:
    """ PhotoTemplate class to render a template string from a PhotoInfo object """

    def __init__(self, photo, exiftool_path=None):
        """ Inits PhotoTemplate class with photo

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

        # should {edited_version} render True?
        self.edited_version = False

    def render(
        self,
        template,
        none_str="_",
        path_sep=None,
        expand_inplace=False,
        inplace_sep=None,
        filename=False,
        dirname=False,
        strip=False,
        edited_version=False,
    ):
        """ Render a filename or directory template 

        Args:
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

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """

        if path_sep is None:
            path_sep = PATH_SEP_DEFAULT

        if inplace_sep is None:
            inplace_sep = INPLACE_DEFAULT

        if type(template) is not str:
            raise TypeError(f"template must be type str, not {type(template)}")

        try:
            model = self.parser.parse(template)
        except TextXSyntaxError as e:
            raise ValueError(f"SyntaxError: {e}")

        if not model:
            # empty string
            return [], []

        self.edited_version = edited_version

        return self._render_statement(
            model,
            none_str=none_str,
            path_sep=path_sep,
            expand_inplace=expand_inplace,
            inplace_sep=inplace_sep,
            filename=filename,
            dirname=dirname,
            strip=strip,
        )

    def _render_statement(
        self,
        statement,
        none_str="_",
        path_sep=None,
        expand_inplace=False,
        inplace_sep=None,
        filename=False,
        dirname=False,
        strip=False,
    ):
        results = []
        unmatched = []
        for ts in statement.template_strings:
            results, unmatched = self._render_template_string(
                ts,
                none_str=none_str,
                path_sep=path_sep,
                expand_inplace=expand_inplace,
                inplace_sep=inplace_sep,
                filename=filename,
                dirname=dirname,
                results=results,
                unmatched=unmatched,
            )

        rendered_strings = results

        if filename:
            rendered_strings = [
                sanitize_filename(rendered_str) for rendered_str in rendered_strings
            ]

        if strip:
            rendered_strings = [
                rendered_str.strip() for rendered_str in rendered_strings
            ]

        return rendered_strings, unmatched

    def _render_template_string(
        self,
        ts,
        none_str="_",
        path_sep=None,
        expand_inplace=False,
        inplace_sep=None,
        filename=False,
        dirname=False,
        results=None,
        unmatched=None,
    ):
        """Render a TemplateString object """

        results = results or [""]
        unmatched = unmatched or []

        if ts.template:
            # have a template field to process
            field = ts.template.field
            if field not in FIELD_NAMES and not field.startswith("photo"):
                unmatched.append(field)
                return [], unmatched

            subfield = ts.template.subfield

            # process filters
            filters = []
            if ts.template.filter is not None:
                filters = ts.template.filter.value

            # process path_sep
            if ts.template.pathsep is not None:
                path_sep = ts.template.pathsep.value

            # process delim
            if ts.template.delim is not None:
                # if value is None, means format was {+field}
                delim = ts.template.delim.value or ""
            else:
                delim = None

            if ts.template.bool is not None:
                is_bool = True
                if ts.template.bool.value is not None:
                    bool_val, u = self._render_statement(
                        ts.template.bool.value,
                        none_str=none_str,
                        path_sep=path_sep,
                        expand_inplace=expand_inplace,
                        inplace_sep=inplace_sep,
                        filename=filename,
                        dirname=dirname,
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
                        none_str=none_str,
                        path_sep=path_sep,
                        expand_inplace=expand_inplace,
                        inplace_sep=inplace_sep,
                        filename=filename,
                        dirname=dirname,
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
                    conditional_value, u = self._render_statement(
                        ts.template.conditional.value,
                        none_str=none_str,
                        path_sep=path_sep,
                        expand_inplace=expand_inplace,
                        inplace_sep=inplace_sep,
                        filename=filename,
                        dirname=dirname,
                    )
                    unmatched.extend(u)
                else:
                    # this shouldn't happen
                    conditional_value = [""]
            else:
                operator = None
                negation = None
                conditional_value = []

            vals = []
            if field in SINGLE_VALUE_SUBSTITUTIONS:
                vals = self.get_template_value(
                    field,
                    default=default,
                    delim=delim or inplace_sep,
                    path_sep=path_sep,
                    filename=filename,
                    dirname=dirname,
                )
            elif field == "exiftool":
                if subfield is None:
                    raise ValueError(
                        "SyntaxError: GROUP:NAME subfield must not be null with {exiftool:GROUP:NAME}'"
                    )
                vals = self.get_template_value_exiftool(
                    subfield, filename=filename, dirname=dirname
                )
            elif field == "function":
                if subfield is None:
                    raise ValueError(
                        "SyntaxError: filename and function must not be null with {function::filename.py:function_name}"
                    )
                vals = self.get_template_value_function(
                    subfield, filename=filename, dirname=dirname
                )
            elif field in MULTI_VALUE_SUBSTITUTIONS or field.startswith("photo"):
                vals = self.get_template_value_multi(
                    field, path_sep=path_sep, filename=filename, dirname=dirname
                )
            else:
                unmatched.append(field)
                return [], unmatched

            vals = [val for val in vals if val is not None]

            if expand_inplace or delim is not None:
                sep = delim if delim is not None else inplace_sep
                vals = [sep.join(sorted(vals))]

            for filter_ in filters:
                vals = self.get_template_value_filter(filter_, vals)

            # process find/replace
            if ts.template.findreplace:
                new_vals = []
                for val in vals:
                    for pair in ts.template.findreplace.pairs:
                        find = pair.find or ""
                        repl = pair.replace or ""
                        val = val.replace(find, repl)
                    new_vals.append(val)
                vals = new_vals

            if operator:
                # have a conditional operator

                def string_test(test_function):
                    """ Perform string comparison using test_function; closure to capture conditional_value, vals, negation """
                    match = False
                    for c in conditional_value:
                        for v in vals:
                            if test_function(v, c):
                                match = True
                                break
                        if match:
                            break
                    if (match and not negation) or (negation and not match):
                        return ["True"]
                    else:
                        return []

                def comparison_test(test_function):
                    """ Perform numerical comparisons using test_function; closure to capture conditional_val, vals, negation """
                    if len(vals) != 1 or len(conditional_value) != 1:
                        raise ValueError(
                            f"comparison operators may only be used with a single value: {vals} {conditional_value}"
                        )
                    try:
                        match = (
                            True
                            if test_function(
                                float(vals[0]), float(conditional_value[0])
                            )
                            else False
                        )
                        if (match and not negation) or (negation and not match):
                            return ["True"]
                        else:
                            return []
                    except ValueError as e:
                        raise ValueError(
                            f"comparison operators may only be used with values that can be converted to numbers: {vals} {conditional_value}"
                        )

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
                    if (match and not negation) or (negation and not match):
                        vals = ["True"]
                    else:
                        vals = []
                elif operator == "!=":
                    match = sorted(vals) != sorted(conditional_value)
                    if (match and not negation) or (negation and not match):
                        vals = ["True"]
                    else:
                        vals = []
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
            elif not vals:
                vals = default or [none_str]

            pre = ts.pre or ""
            post = ts.post or ""

            rendered = [pre + val + post for val in vals]
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

    def get_template_value(
        self,
        field,
        default,
        bool_val=None,
        delim=None,
        path_sep=None,
        filename=False,
        dirname=False,
    ):
        """lookup value for template field (single-value template substitutions)

        Args:
            field: template field to find value for.
            default: the default value provided by the user
            bool_val: True value if expression is boolean 
            delim: delimiter for expand in place
            path_sep: path separator for fields that are path-like
            filename: if True, template output will be sanitized to produce valid file name
            dirname: if True, template output will be sanitized to produce valid directory name 
        
        Returns:
            The matching template value (which may be None).

        Raises:
            ValueError if no rule exists for field.
        """
        if field not in FIELD_NAMES:
            raise ValueError(f"SyntaxError: Unknown field: {field}")

        # initialize today with current date/time if needed
        if self.today is None:
            self.today = datetime.datetime.now()

        value = None

        # wouldn't a switch/case statement be nice...
        if field == "name":
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
        elif field == "created.date":
            value = DateTimeFormatter(self.photo.date).date
        elif field == "created.year":
            value = DateTimeFormatter(self.photo.date).year
        elif field == "created.yy":
            value = DateTimeFormatter(self.photo.date).yy
        elif field == "created.mm":
            value = DateTimeFormatter(self.photo.date).mm
        elif field == "created.month":
            value = DateTimeFormatter(self.photo.date).month
        elif field == "created.mon":
            value = DateTimeFormatter(self.photo.date).mon
        elif field == "created.dd":
            value = DateTimeFormatter(self.photo.date).dd
        elif field == "created.dow":
            value = DateTimeFormatter(self.photo.date).dow
        elif field == "created.doy":
            value = DateTimeFormatter(self.photo.date).doy
        elif field == "created.hour":
            value = DateTimeFormatter(self.photo.date).hour
        elif field == "created.min":
            value = DateTimeFormatter(self.photo.date).min
        elif field == "created.sec":
            value = DateTimeFormatter(self.photo.date).sec
        elif field == "created.strftime":
            if default:
                try:
                    value = self.photo.date.strftime(default[0])
                except:
                    raise ValueError(f"Invalid strftime template: '{default}'")
            else:
                value = None
        elif field == "modified.date":
            value = (
                DateTimeFormatter(self.photo.date_modified).date
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).date
            )
        elif field == "modified.year":
            value = (
                DateTimeFormatter(self.photo.date_modified).year
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).year
            )
        elif field == "modified.yy":
            value = (
                DateTimeFormatter(self.photo.date_modified).yy
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).yy
            )
        elif field == "modified.mm":
            value = (
                DateTimeFormatter(self.photo.date_modified).mm
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).mm
            )
        elif field == "modified.month":
            value = (
                DateTimeFormatter(self.photo.date_modified).month
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).month
            )
        elif field == "modified.mon":
            value = (
                DateTimeFormatter(self.photo.date_modified).mon
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).mon
            )
        elif field == "modified.dd":
            value = (
                DateTimeFormatter(self.photo.date_modified).dd
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).dd
            )
        elif field == "modified.dow":
            value = (
                DateTimeFormatter(self.photo.date_modified).dow
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).dow
            )
        elif field == "modified.doy":
            value = (
                DateTimeFormatter(self.photo.date_modified).doy
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).doy
            )
        elif field == "modified.hour":
            value = (
                DateTimeFormatter(self.photo.date_modified).hour
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).hour
            )
        elif field == "modified.min":
            value = (
                DateTimeFormatter(self.photo.date_modified).min
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).min
            )
        elif field == "modified.sec":
            value = (
                DateTimeFormatter(self.photo.date_modified).sec
                if self.photo.date_modified
                else DateTimeFormatter(self.photo.date).sec
            )
        elif field == "modified.strftime":
            if default:
                try:
                    date = self.photo.date_modified or self.photo.date
                    value = date.strftime(default[0])
                except:
                    raise ValueError(f"Invalid strftime template: '{default}'")
            else:
                value = None
        elif field == "today.date":
            value = DateTimeFormatter(self.today).date
        elif field == "today.year":
            value = DateTimeFormatter(self.today).year
        elif field == "today.yy":
            value = DateTimeFormatter(self.today).yy
        elif field == "today.mm":
            value = DateTimeFormatter(self.today).mm
        elif field == "today.month":
            value = DateTimeFormatter(self.today).month
        elif field == "today.mon":
            value = DateTimeFormatter(self.today).mon
        elif field == "today.dd":
            value = DateTimeFormatter(self.today).dd
        elif field == "today.dow":
            value = DateTimeFormatter(self.today).dow
        elif field == "today.doy":
            value = DateTimeFormatter(self.today).doy
        elif field == "today.hour":
            value = DateTimeFormatter(self.today).hour
        elif field == "today.min":
            value = DateTimeFormatter(self.today).min
        elif field == "today.sec":
            value = DateTimeFormatter(self.today).sec
        elif field == "today.strftime":
            if default:
                try:
                    value = self.today.strftime(default[0])
                except:
                    raise ValueError(f"Invalid strftime template: '{default}'")
            else:
                value = None
        elif field == "place.name":
            value = self.photo.place.name if self.photo.place else None
        elif field == "place.country_code":
            value = self.photo.place.country_code if self.photo.place else None
        elif field == "place.name.country":
            value = (
                self.photo.place.names.country[0]
                if self.photo.place and self.photo.place.names.country
                else None
            )
        elif field == "place.name.state_province":
            value = (
                self.photo.place.names.state_province[0]
                if self.photo.place and self.photo.place.names.state_province
                else None
            )
        elif field == "place.name.city":
            value = (
                self.photo.place.names.city[0]
                if self.photo.place and self.photo.place.names.city
                else None
            )
        elif field == "place.name.area_of_interest":
            value = (
                self.photo.place.names.area_of_interest[0]
                if self.photo.place and self.photo.place.names.area_of_interest
                else None
            )
        elif field == "place.address":
            value = (
                self.photo.place.address_str
                if self.photo.place and self.photo.place.address_str
                else None
            )
        elif field == "place.address.street":
            value = (
                self.photo.place.address.street
                if self.photo.place and self.photo.place.address.street
                else None
            )
        elif field == "place.address.city":
            value = (
                self.photo.place.address.city
                if self.photo.place and self.photo.place.address.city
                else None
            )
        elif field == "place.address.state_province":
            value = (
                self.photo.place.address.state_province
                if self.photo.place and self.photo.place.address.state_province
                else None
            )
        elif field == "place.address.postal_code":
            value = (
                self.photo.place.address.postal_code
                if self.photo.place and self.photo.place.address.postal_code
                else None
            )
        elif field == "place.address.country":
            value = (
                self.photo.place.address.country
                if self.photo.place and self.photo.place.address.country
                else None
            )
        elif field == "place.address.country_code":
            value = (
                self.photo.place.address.iso_country_code
                if self.photo.place and self.photo.place.address.iso_country_code
                else None
            )
        elif field == "searchinfo.season":
            value = self.photo.search_info.season if self.photo.search_info else None
        elif field == "exif.camera_make":
            value = self.photo.exif_info.camera_make if self.photo.exif_info else None
        elif field == "exif.camera_model":
            value = self.photo.exif_info.camera_model if self.photo.exif_info else None
        elif field == "exif.lens_model":
            value = self.photo.exif_info.lens_model if self.photo.exif_info else None
        elif field == "uuid":
            value = self.photo.uuid
        elif field in PUNCTUATION:
            value = PUNCTUATION[field]
        elif field == "osxphotos_version":
            value = __version__
        elif field == "osxphotos_cmd_line":
            value = " ".join(sys.argv)
        else:
            # if here, didn't get a match
            raise ValueError(f"Unhandled template value: {field}")

        if filename:
            value = sanitize_pathpart(value)
        elif dirname:
            value = sanitize_dirname(value)

        return [value]

    def get_template_value_filter(self, filter_, values):
        if filter_ == "lower":
            if values and type(values) == list:
                value = [v.lower() for v in values]
            else:
                value = [values.lower()] if values else []
        elif filter_ == "upper":
            if values and type(values) == list:
                value = [v.upper() for v in values]
            else:
                value = [values.upper()] if values else []
        elif filter_ == "strip":
            if values and type(values) == list:
                value = [v.strip() for v in values]
            else:
                value = [values.strip()] if values else []
        elif filter_ == "capitalize":
            if values and type(values) == list:
                value = [v.capitalize() for v in values]
            else:
                value = [values.capitalize()] if values else []
        elif filter_ == "titlecase":
            if values and type(values) == list:
                value = [v.title() for v in values]
            else:
                value = [values.title()] if values else []
        elif filter_ == "braces":
            if values and type(values) == list:
                value = ["{" + v + "}" for v in values]
            else:
                value = ["{" + values + "}"] if values else []
        elif filter_ == "parens":
            if values and type(values) == list:
                value = ["(" + v + ")" for v in values]
            else:
                value = ["(" + values + ")"] if values else []
        elif filter_ == "brackets":
            if values and type(values) == list:
                value = ["[" + v + "]" for v in values]
            else:
                value = ["[" + values + "]"] if values else []
        elif filter_.startswith("function:"):
            value = self.get_template_value_filter_function(filter_, values)
        else:
            value = []
        return value

    def get_template_value_multi(self, field, path_sep, filename=False, dirname=False):
        """lookup value for template field (multi-value template substitutions)

        Args:
            field: template field to find value for.
            path_sep: path separator to use for folder_album field
            dirname: if True, values will be sanitized to be valid directory names; default = False
        
        Returns:
            List of the matching template values or [].

        Raises:
            ValueError if no rule exists for field.
        """

        """ return list of values for a multi-valued template field """
        values = []
        if field == "album":
            values = self.photo.burst_albums if self.photo.burst else self.photo.albums
        elif field == "keyword":
            values = self.photo.keywords
        elif field == "person":
            values = self.photo.persons
            # remove any _UNKNOWN_PERSON values
            values = [val for val in values if val != _UNKNOWN_PERSON]
        elif field == "label":
            values = self.photo.labels
        elif field == "label_normalized":
            values = self.photo.labels_normalized
        elif field == "folder_album":
            values = []
            # photos must be in an album to be in a folder
            if self.photo.burst:
                album_info = self.photo.burst_album_info
            else:
                album_info = self.photo.album_info
            for album in album_info:
                if album.folder_names:
                    # album in folder
                    if dirname:
                        # being used as a filepath so sanitize each part
                        folder = path_sep.join(
                            sanitize_dirname(f) for f in album.folder_names
                        )
                        folder += path_sep + sanitize_dirname(album.title)
                    else:
                        folder = path_sep.join(album.folder_names)
                        folder += path_sep + album.title
                    values.append(folder)
                else:
                    # album not in folder
                    if dirname:
                        values.append(sanitize_dirname(album.title))
                    else:
                        values.append(album.title)
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
                except AttributeError:
                    raise ValueError(
                        "Invalid property for {photo} template: " + f"'{property_}'"
                    )
            if obj is None:
                values = []
            elif isinstance(obj, bool):
                values = [property_] if obj else []
            elif isinstance(obj, (str, int, float)):
                values = [str(obj)]
            else:
                values = [val for val in obj]
        else:
            raise ValueError(f"Unhandled template value: {field}")

        # sanitize directory names if needed, folder_album handled differently above
        if filename:
            values = [sanitize_pathpart(value) for value in values]
        elif dirname and field != "folder_album":
            # skip folder_album because it would have been handled above
            values = [sanitize_dirname(value) for value in values]

        # If no values, insert None so code below will substitute none_str for None
        values = values or []
        return values

    def get_template_value_exiftool(self, subfield, filename=None, dirname=None):
        """Get template value for format "{exiftool:EXIF:Model}" """

        if not self.photo.path:
            return []

        exif = ExifToolCaching(self.photo.path, exiftool=self.exiftool_path)
        exifdict = exif.asdict(normalized=True)
        subfield = subfield.lower()
        if subfield in exifdict:
            values = exifdict[subfield]
            values = [values] if not isinstance(values, list) else values
            values = [str(v) for v in values]

            # sanitize directory names if needed
            if filename:
                values = [sanitize_pathpart(value) for value in values]
            elif dirname:
                values = [sanitize_dirname(value) for value in values]
        else:
            values = []

        return values

    def get_template_value_function(self, subfield, filename=None, dirname=None):
        """Get template value from external function """

        if "::" not in subfield:
            raise ValueError(
                f"SyntaxError: could not parse function name from '{subfield}'"
            )

        filename, funcname = subfield.split("::")

        if not pathlib.Path(filename).is_file():
            raise ValueError(f"'{filename}' does not appear to be a file")

        template_func = load_function(filename, funcname)
        values = template_func(self.photo)

        if not isinstance(values, (str, list)):
            raise TypeError(
                f"Invalid return type for function {funcname}: expected str or list"
            )
        if type(values) == str:
            values = [values]

        # sanitize directory names if needed
        if filename:
            values = [sanitize_pathpart(value) for value in values]
        elif dirname:
            values = [sanitize_dirname(value) for value in values]

        return values

    def get_template_value_filter_function(self, filter_, values):
        """Filter template value from external function """

        filter_ = filter_.replace("function:","")

        if "::" not in filter_:
            raise ValueError(
                f"SyntaxError: could not parse function name from '{filter_}'"
            )

        filename, funcname = filter_.split("::")

        if not pathlib.Path(filename).is_file():
            raise ValueError(f"'{filename}' does not appear to be a file")

        template_func = load_function(filename, funcname)

        if not isinstance(values, (list, tuple)):
            values = [values]
        values = template_func(values)

        if not isinstance(values, list):
            raise TypeError(
                f"Invalid return type for function {funcname}: expected list"
            )

        return values


    def get_photo_video_type(self, default):
        """ return media type, e.g. photo or video """
        default_dict = parse_default_kv(default, PHOTO_VIDEO_TYPE_DEFAULTS)
        if self.photo.isphoto:
            return default_dict["photo"]
        else:
            return default_dict["video"]

    def get_media_type(self, default):
        """ return special media type, e.g. slow_mo, panorama, etc., defaults to photo or video if no special type """
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
        # get value for a PhotoInfo bool attribute
        val = getattr(self.photo, attr)
        if val:
            return bool_val
        else:
            return default


def parse_default_kv(default, default_dict):
    """ parse a string in form key1=value1;key2=value2,... as used for some template fields

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
    """Return help for template system as markdown string """
    # TODO: would be better to use importlib.abc.ResourceReader but I can't find a single example of how to do this
    help_file = pathlib.Path(__file__).parent / "phototemplate.md"
    with open(help_file, "r") as fd:
        md = fd.read()
    return md
