import datetime
import pathlib
import re
from typing import Tuple  # pylint: disable=syntax-error

from .photoinfo import PhotoInfo

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


def get_template_value(lookup, photo):
    """ lookup: value to find a match for
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


def render_filepath_template(
    template: str, photo: PhotoInfo, none_str: str = "_"
) -> Tuple[str, list]:
    """ render a filename or directory template """

    # pylint: disable=anomalous-backslash-in-string
    regex = r"""(?<!\\)\{([^\\,}]+)(,{0,1}(([\w\-. ]+))?)\}"""

    # pylint: disable=anomalous-backslash-in-string
    unmatched_regex = r"(?<!\\)(\{[^\\,}]+\})"

    # Explanation for regex:
    # (?<!\\) Negative Lookbehind to skip escaped braces
    #     assert regex following does not match "\" preceeding "{"
    # \{ Match the opening brace
    # 1st Capturing Group ([^\\,}]+)  Don't match "\", ",", or "}"
    # 2nd Capturing Group (,?(([\w\-. ]+))?)
    #     ,{0,1} optional ","
    # 3rd Capturing Group (([\w\-. ]+))?
    #     Matches the comma and any word characters after
    # 4th Capturing Group ([\w\-. ]+)
    #     Matches just the characters after the comma
    # \} Matches the closing brace

    if type(template) is not str:
        raise TypeError(f"template must be type str, not {type(template)}")

    if type(photo) is not PhotoInfo:
        raise TypeError(f"photo must be type osxphotos.PhotoInfo, not {type(photo)}")

    def make_subst_function(photo, none_str):
        """ returns: substitution function for use in re.sub """
        # closure to capture photo, none_str in subst
        def subst(matchobj):
            groups = len(matchobj.groups())
            if groups == 4:
                try:
                    val = get_template_value(matchobj.group(1), photo)
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

    # find any {words} that weren't replaced
    unmatched = re.findall(unmatched_regex, rendered)

    # fix any escaped curly braces
    rendered = re.sub(r"\\{", "{", rendered)
    rendered = re.sub(r"\\}", "}", rendered)

    return rendered, unmatched


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
