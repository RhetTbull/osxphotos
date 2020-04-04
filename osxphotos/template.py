""" Custom template system for osxphotos """

# Rolled my own template system because:
# 1. Needed to handle multiple values (e.g. album, keyword)
# 2. Needed to handle default values if template not found
# 3. Didn't want user to need to know python (e.g. by using Mako which is
#    already used elsewhere in this project)
# 4. Couldn't figure out how to do #1 and #2 with str.format()
#
# This code isn't elegant but it seems to work well.  PRs gladly accepted.

import datetime
import pathlib
import re
from typing import Tuple, List  # pylint: disable=syntax-error

from .photoinfo import PhotoInfo
from ._constants import _UNKNOWN_PERSON

# Permitted substitutions (each of these returns a single value or None)
TEMPLATE_SUBSTITUTIONS = {
    "{name}": "Filename of the photo",
    "{original_name}": "Photo's original filename when imported to Photos",
    "{title}": "Title of the photo",
    "{descr}": "Description of the photo",
    "{created.date}": "Photo's creation date in ISO format, e.g. '2020-03-22'",
    "{created.year}": "4-digit year of file creation time",
    "{created.yy}": "2-digit year of file creation time",
    "{created.mm}": "2-digit month of the file creation time (zero padded)",
    "{created.month}": "Month name in user's locale of the file creation time",
    "{created.mon}": "Month abbreviation in the user's locale of the file creation time",
    "{created.doy}": "3-digit day of year (e.g Julian day) of file creation time, starting from 1 (zero padded)",
    "{modified.date}": "Photo's modification date in ISO format, e.g. '2020-03-22'",
    "{modified.year}": "4-digit year of file modification time",
    "{modified.yy}": "2-digit year of file modification time",
    "{modified.mm}": "2-digit month of the file modification time (zero padded)",
    "{modified.month}": "Month name in user's locale of the file modification time",
    "{modified.mon}": "Month abbreviation in the user's locale of the file modification time",
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
    "{keyword}": "Keyword(s) assigned to photo",
    "{person}": "Person(s) / face(s) in a photo",
}

# Just the multi-valued substitution names without the braces
MULTI_VALUE_SUBSTITUTIONS = [
    field.replace("{", "").replace("}", "")
    for field in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.keys()
]


def get_template_value(lookup, photo):
    """ lookup template value (single-value template substitutions) for use in make_subst_function
        lookup: value to find a match for
        photo: PhotoInfo object whose data will be used for value substitutions
        returns: either the matching template value (which may be None)
        raises: KeyError if no rule exists for lookup """

    # must be a valid keyword
    if lookup == "name":
        return pathlib.Path(photo.filename).stem

    if lookup == "original_name":
        return pathlib.Path(photo.original_filename).stem

    if lookup == "title":
        return photo.title

    if lookup == "descr":
        return photo.description

    if lookup == "created.date":
        return DateTimeFormatter(photo.date).date

    if lookup == "created.year":
        return DateTimeFormatter(photo.date).year

    if lookup == "created.yy":
        return DateTimeFormatter(photo.date).yy

    if lookup == "created.mm":
        return DateTimeFormatter(photo.date).mm

    if lookup == "created.month":
        return DateTimeFormatter(photo.date).month

    if lookup == "created.mon":
        return DateTimeFormatter(photo.date).mon

    if lookup == "created.doy":
        return DateTimeFormatter(photo.date).doy

    if lookup == "modified.date":
        return (
            DateTimeFormatter(photo.date_modified).date if photo.date_modified else None
        )

    if lookup == "modified.year":
        return (
            DateTimeFormatter(photo.date_modified).year if photo.date_modified else None
        )

    if lookup == "modified.yy":
        return (
            DateTimeFormatter(photo.date_modified).yy if photo.date_modified else None
        )

    if lookup == "modified.mm":
        return (
            DateTimeFormatter(photo.date_modified).mm if photo.date_modified else None
        )

    if lookup == "modified.month":
        return (
            DateTimeFormatter(photo.date_modified).month
            if photo.date_modified
            else None
        )

    if lookup == "modified.mon":
        return (
            DateTimeFormatter(photo.date_modified).mon if photo.date_modified else None
        )

    if lookup == "modified.doy":
        return (
            DateTimeFormatter(photo.date_modified).doy if photo.date_modified else None
        )

    if lookup == "place.name":
        return photo.place.name if photo.place else None

    if lookup == "place.country_code":
        return photo.place.country_code if photo.place else None

    if lookup == "place.name.country":
        return (
            photo.place.names.country[0]
            if photo.place and photo.place.names.country
            else None
        )

    if lookup == "place.name.state_province":
        return (
            photo.place.names.state_province[0]
            if photo.place and photo.place.names.state_province
            else None
        )

    if lookup == "place.name.city":
        return (
            photo.place.names.city[0]
            if photo.place and photo.place.names.city
            else None
        )

    if lookup == "place.name.area_of_interest":
        return (
            photo.place.names.area_of_interest[0]
            if photo.place and photo.place.names.area_of_interest
            else None
        )

    if lookup == "place.address":
        return (
            photo.place.address_str if photo.place and photo.place.address_str else None
        )

    if lookup == "place.address.street":
        return (
            photo.place.address.street
            if photo.place and photo.place.address.street
            else None
        )

    if lookup == "place.address.city":
        return (
            photo.place.address.city
            if photo.place and photo.place.address.city
            else None
        )

    if lookup == "place.address.state_province":
        return (
            photo.place.address.state_province
            if photo.place and photo.place.address.state_province
            else None
        )

    if lookup == "place.address.postal_code":
        return (
            photo.place.address.postal_code
            if photo.place and photo.place.address.postal_code
            else None
        )

    if lookup == "place.address.country":
        return (
            photo.place.address.country
            if photo.place and photo.place.address.country
            else None
        )

    if lookup == "place.address.country_code":
        return (
            photo.place.address.iso_country_code
            if photo.place and photo.place.address.iso_country_code
            else None
        )

    # if here, didn't get a match
    raise KeyError(f"No rule for processing {lookup}")


def render_filepath_template(template, photo, none_str="_"):
    """ render a filename or directory template 
        template: str template 
        photo: PhotoInfo object
        none_str: str to use default for None values, default is '_' """

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

    if type(photo) is not PhotoInfo:
        raise TypeError(f"photo must be type osxphotos.PhotoInfo, not {type(photo)}")

    def make_subst_function(photo, none_str, get_func=get_template_value):
        """ returns: substitution function for use in re.sub 
            photo: a PhotoInfo object
            none_str: value to use if substitution lookup is None and no default provided
            get_func: function that gets the substitution value for a given template field
                      default is get_template_value which handles the single-value fields """

        # closure to capture photo, none_str in subst
        def subst(matchobj):
            groups = len(matchobj.groups())
            if groups == 4:
                try:
                    val = get_func(matchobj.group(1), photo)
                except KeyError:
                    return matchobj.group(0)

                if val is None:
                    return (
                        matchobj.group(3) if matchobj.group(3) is not None else none_str
                    )
                else:
                    return val
            else:
                raise ValueError(
                    f"Unexpected number of groups: expected 4, got {groups}"
                )

        return subst

    subst_func = make_subst_function(photo, none_str)

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
        if field == "album":
            values = photo.albums
        elif field == "keyword":
            values = photo.keywords
        elif field == "person":
            values = photo.persons
            # remove any _UNKNOWN_PERSON values
            values = [val for val in values if val != _UNKNOWN_PERSON]
        else:
            raise ValueError(f"Unhandleded template value: {field}")

        # If no values, insert None so code below will substite none_str for None
        values = values or [None]

        # Build a regex that matches only the field being processed
        re_str = r"(?<!\\)\{(" + field + r")(,{0,1}(([\w\-. ]+))?)\}"
        regex_multi = re.compile(re_str)

        # holds each of the new rendered_strings, set() to avoid duplicates
        new_strings = set()

        for str_template in rendered_strings:
            for val in values:

                def get_template_value_multi(lookup_value, photo):
                    """ Closure passed to make_subst_function get_func 
                        Capture val and field in the closure 
                        Allows make_subst_function to be re-used w/o modification """
                    if lookup_value == field:
                        return val
                    else:
                        raise KeyError(f"Unexpected value: {lookup_value}")

                subst = make_subst_function(
                    photo, none_str, get_func=get_template_value_multi
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


class DateTimeFormatter:
    """ provides property access to formatted datetime.datetime strftime values """

    def __init__(self, dt: datetime.datetime):
        self.dt = dt

    @property
    def date(self):
        """ ISO date in form 2020-03-22 """
        date = self.dt.date().isoformat()
        return date

    @property
    def year(self):
        """ 4 digit year """
        year = f"{self.dt.year}"
        return year

    @property
    def yy(self):
        """ 2 digit year """
        yy = f"{self.dt.strftime('%y')}"
        return yy

    @property
    def mm(self):
        """ 2 digit month """
        mm = f"{self.dt.strftime('%m')}"
        return mm

    @property
    def month(self):
        """ Month as locale's full name """
        month = f"{self.dt.strftime('%B')}"
        return month

    @property
    def mon(self):
        """ Month as locale's abbreviated name """
        mon = f"{self.dt.strftime('%b')}"
        return mon

    @property
    def doy(self):
        """ Julian day of year starting from 001 """
        doy = f"{self.dt.strftime('%j')}"
        return doy
