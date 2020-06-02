""" Custom template system for osxphotos (implemented in PhotoInfo.render_template) """


# Rolled my own template system because:
# 1. Needed to handle multiple values (e.g. album, keyword)
# 2. Needed to handle default values if template not found
# 3. Didn't want user to need to know python (e.g. by using Mako which is
#    already used elsewhere in this project)
# 4. Couldn't figure out how to do #1 and #2 with str.format()
#
# This code isn't elegant but it seems to work well.  PRs gladly accepted.
import locale
import os
import re
import pathlib

from ._constants import _UNKNOWN_PERSON
from .datetime_formatter import DateTimeFormatter

# ensure locale set to user's locale
locale.setlocale(locale.LC_ALL, "")

# Permitted substitutions (each of these returns a single value or None)
TEMPLATE_SUBSTITUTIONS = {
    "{name}": "Current filename of the photo",
    "{original_name}": "Photo's original filename when imported to Photos",
    "{title}": "Title of the photo",
    "{descr}": "Description of the photo",
    "{created.date}": "Photo's creation date in ISO format, e.g. '2020-03-22'",
    "{created.year}": "4-digit year of file creation time",
    "{created.yy}": "2-digit year of file creation time",
    "{created.mm}": "2-digit month of the file creation time (zero padded)",
    "{created.month}": "Month name in user's locale of the file creation time",
    "{created.mon}": "Month abbreviation in the user's locale of the file creation time",
    "{created.dd}": "2-digit day of the month (zero padded) of file creation time",
    "{created.dow}": "Day of week in user's locale of the file creation time",
    "{created.doy}": "3-digit day of year (e.g Julian day) of file creation time, starting from 1 (zero padded)",
    "{modified.date}": "Photo's modification date in ISO format, e.g. '2020-03-22'",
    "{modified.year}": "4-digit year of file modification time",
    "{modified.yy}": "2-digit year of file modification time",
    "{modified.mm}": "2-digit month of the file modification time (zero padded)",
    "{modified.month}": "Month name in user's locale of the file modification time",
    "{modified.mon}": "Month abbreviation in the user's locale of the file modification time",
    "{modified.dd}": "2-digit day of the month (zero padded) of the file modification time",
    "{modified.doy}": "3-digit day of year (e.g Julian day) of file modification time, starting from 1 (zero padded)",
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
}

# Permitted multi-value substitutions (each of these returns None or 1 or more values)
TEMPLATE_SUBSTITUTIONS_MULTI_VALUED = {
    "{album}": "Album(s) photo is contained in",
    "{folder_album}": "Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder",
    "{keyword}": "Keyword(s) assigned to photo",
    "{person}": "Person(s) / face(s) in a photo",
    "{label}": "Image categorization label associated with a photo (Photos 5 only)",
    "{label_normalized}": "All lower case version of 'label' (Photos 5 only)",
}

# Just the multi-valued substitution names without the braces
MULTI_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "")
    for field in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
]


class PhotoTemplate:
    """ PhotoTemplate class to render a template string from a PhotoInfo object """

    def __init__(self, photo):
        """ Inits PhotoTemplate class with photo, non_str, and path_sep

        Args:
            photo: a PhotoInfo instance.
        """
        self.photo = photo

    def render(self, template, none_str="_", path_sep=None):
        """ render a filename or directory template 
            template: str template 
            none_str: str to use default for None values, default is '_' 
            path_sep: optional character to use as path separator, default is os.path.sep """
        if path_sep is None:
            path_sep = os.path.sep
        elif path_sep is not None and len(path_sep) != 1:
            raise ValueError(f"path_sep must be single character: {path_sep}")

        # the rendering happens in two phases:
        # phase 1: handle all the single-value template substitutions
        #          results in a single string with all the template fields replaced
        # phase 2: loop through all the multi-value template substitutions
        #          could result in multiple strings
        #          e.g. if template is "{album}/{person}" and there are 2 albums and 3 persons in the photo
        #          there would be 6 possible renderings (2 albums x 3 persons)

        # regex to find {template_field,optional_default} in strings
        # for explanation of regex see https://regex101.com/r/4JJg42/1
        # pylint: disable=anomalous-backslash-in-string
        regex = r"(?<!\{)\{([^\\,}]+)(,{0,1}(([\w\-. ]+))?)(?=\}(?!\}))\}"
        if type(template) is not str:
            raise TypeError(f"template must be type str, not {type(template)}")

        def make_subst_function(self, none_str, get_func=self.get_template_value):
            """ returns: substitution function for use in re.sub 
                none_str: value to use if substitution lookup is None and no default provided
                get_func: function that gets the substitution value for a given template field
                        default is get_template_value which handles the single-value fields """

            # closure to capture photo, none_str in subst
            def subst(matchobj):
                groups = len(matchobj.groups())
                if groups == 4:
                    try:
                        val = get_func(matchobj.group(1))
                    except ValueError:
                        return matchobj.group(0)

                    if val is None:
                        return (
                            matchobj.group(3)
                            if matchobj.group(3) is not None
                            else none_str
                        )
                    else:
                        return val
                else:
                    raise ValueError(
                        f"Unexpected number of groups: expected 4, got {groups}"
                    )

            return subst

        subst_func = make_subst_function(self, none_str)

        # do the replacements
        rendered = re.sub(regex, subst_func, template)

        # do multi-valued placements
        # start with the single string from phase 1 above then loop through all
        # multi-valued fields and all values for each of those fields
        # rendered_strings will be updated as each field is processed
        # for example: if two albums, two keywords, and one person and template is:
        # "{created.year}/{album}/{keyword}/{person}"
        # rendered strings would do the following:
        # start (created.year filled in phase 1)
        #   ['2011/{album}/{keyword}/{person}']
        # after processing albums:
        #   ['2011/Album1/{keyword}/{person}',
        #    '2011/Album2/{keyword}/{person}',]
        # after processing keywords:
        #   ['2011/Album1/keyword1/{person}',
        #    '2011/Album1/keyword2/{person}',
        #    '2011/Album2/keyword1/{person}',
        #    '2011/Album2/keyword2/{person}',]
        # after processing person:
        #   ['2011/Album1/keyword1/person1',
        #    '2011/Album1/keyword2/person1',
        #    '2011/Album2/keyword1/person1',
        #    '2011/Album2/keyword2/person1',]

        rendered_strings = set([rendered])
        for field in MULTI_VALUE_SUBSTITUTIONS:
            # Build a regex that matches only the field being processed
            re_str = r"(?<!\\)\{(" + field + r")(,(([\w\-. ]{0,})))?\}"
            regex_multi = re.compile(re_str)

            # holds each of the new rendered_strings, set() to avoid duplicates
            new_strings = set()

            for str_template in rendered_strings:
                if regex_multi.search(str_template):
                    values = self.get_template_value_multi(field, path_sep)
                    for val in values:

                        def lookup_template_value_multi(lookup_value):
                            """ Closure passed to make_subst_function get_func 
                                Capture val and field in the closure 
                                Allows make_subst_function to be re-used w/o modification """
                            if lookup_value == field:
                                return val
                            else:
                                raise ValueError(f"Unexpected value: {lookup_value}")

                        subst = make_subst_function(
                            self, none_str, get_func=lookup_template_value_multi
                        )
                        new_string = regex_multi.sub(subst, str_template)
                        new_strings.add(new_string)

                    # update rendered_strings for the next field to process
                    rendered_strings = new_strings

        # find any {fields} that weren't replaced
        unmatched = []
        for rendered_str in rendered_strings:
            unmatched.extend(
                [
                    no_match[0]
                    for no_match in re.findall(regex, rendered_str)
                    if no_match[0] not in unmatched
                ]
            )

        # fix any escaped curly braces
        rendered_strings = [
            rendered_str.replace("{{", "{").replace("}}", "}")
            for rendered_str in rendered_strings
        ]

        return rendered_strings, unmatched

    def get_template_value(self, field):
        """lookup value for template field (single-value template substitutions)

        Args:
            field: template field to find value for.
        
        Returns:
            The matching template value (which may be None).

        Raises:
            ValueError if no rule exists for field.
        """

        # must be a valid keyword
        if field == "name":
            return pathlib.Path(self.photo.filename).stem

        if field == "original_name":
            return pathlib.Path(self.photo.original_filename).stem

        if field == "title":
            return self.photo.title

        if field == "descr":
            return self.photo.description

        if field == "created.date":
            return DateTimeFormatter(self.photo.date).date

        if field == "created.year":
            return DateTimeFormatter(self.photo.date).year

        if field == "created.yy":
            return DateTimeFormatter(self.photo.date).yy

        if field == "created.mm":
            return DateTimeFormatter(self.photo.date).mm

        if field == "created.month":
            return DateTimeFormatter(self.photo.date).month

        if field == "created.mon":
            return DateTimeFormatter(self.photo.date).mon

        if field == "created.dd":
            return DateTimeFormatter(self.photo.date).dd

        if field == "created.dow":
            return DateTimeFormatter(self.photo.date).dow

        if field == "created.doy":
            return DateTimeFormatter(self.photo.date).doy

        if field == "modified.date":
            return (
                DateTimeFormatter(self.photo.date_modified).date
                if self.photo.date_modified
                else None
            )

        if field == "modified.year":
            return (
                DateTimeFormatter(self.photo.date_modified).year
                if self.photo.date_modified
                else None
            )

        if field == "modified.yy":
            return (
                DateTimeFormatter(self.photo.date_modified).yy
                if self.photo.date_modified
                else None
            )

        if field == "modified.mm":
            return (
                DateTimeFormatter(self.photo.date_modified).mm
                if self.photo.date_modified
                else None
            )

        if field == "modified.month":
            return (
                DateTimeFormatter(self.photo.date_modified).month
                if self.photo.date_modified
                else None
            )

        if field == "modified.mon":
            return (
                DateTimeFormatter(self.photo.date_modified).mon
                if self.photo.date_modified
                else None
            )

        if field == "modified.dd":
            return (
                DateTimeFormatter(self.photo.date_modified).dd
                if self.photo.date_modified
                else None
            )

        if field == "modified.doy":
            return (
                DateTimeFormatter(self.photo.date_modified).doy
                if self.photo.date_modified
                else None
            )

        if field == "place.name":
            return self.photo.place.name if self.photo.place else None

        if field == "place.country_code":
            return self.photo.place.country_code if self.photo.place else None

        if field == "place.name.country":
            return (
                self.photo.place.names.country[0]
                if self.photo.place and self.photo.place.names.country
                else None
            )

        if field == "place.name.state_province":
            return (
                self.photo.place.names.state_province[0]
                if self.photo.place and self.photo.place.names.state_province
                else None
            )

        if field == "place.name.city":
            return (
                self.photo.place.names.city[0]
                if self.photo.place and self.photo.place.names.city
                else None
            )

        if field == "place.name.area_of_interest":
            return (
                self.photo.place.names.area_of_interest[0]
                if self.photo.place and self.photo.place.names.area_of_interest
                else None
            )

        if field == "place.address":
            return (
                self.photo.place.address_str
                if self.photo.place and self.photo.place.address_str
                else None
            )

        if field == "place.address.street":
            return (
                self.photo.place.address.street
                if self.photo.place and self.photo.place.address.street
                else None
            )

        if field == "place.address.city":
            return (
                self.photo.place.address.city
                if self.photo.place and self.photo.place.address.city
                else None
            )

        if field == "place.address.state_province":
            return (
                self.photo.place.address.state_province
                if self.photo.place and self.photo.place.address.state_province
                else None
            )

        if field == "place.address.postal_code":
            return (
                self.photo.place.address.postal_code
                if self.photo.place and self.photo.place.address.postal_code
                else None
            )

        if field == "place.address.country":
            return (
                self.photo.place.address.country
                if self.photo.place and self.photo.place.address.country
                else None
            )

        if field == "place.address.country_code":
            return (
                self.photo.place.address.iso_country_code
                if self.photo.place and self.photo.place.address.iso_country_code
                else None
            )

        # if here, didn't get a match
        raise ValueError(f"Unhandled template value: {field}")

    def get_template_value_multi(self, field, path_sep):
        """lookup value for template field (multi-value template substitutions)

        Args:
            field: template field to find value for.
            path_sep: path separator to use for folder_album field
        
        Returns:
            List of the matching template values or [None].

        Raises:
            ValueError if no rule exists for field.
        """

        """ return list of values for a multi-valued template field """
        if field == "album":
            values = self.photo.albums
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
            for album in self.photo.album_info:
                if album.folder_names:
                    # album in folder
                    folder = path_sep.join(album.folder_names)
                    folder += path_sep + album.title
                    values.append(folder)
                else:
                    # album not in folder
                    values.append(album.title)
        else:
            raise ValueError(f"Unhandleded template value: {field}")

        # If no values, insert None so code below will substite none_str for None
        values = values or [None]
        return values
