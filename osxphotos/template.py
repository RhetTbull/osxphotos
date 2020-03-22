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
    "{place.name}": "Place name from the photo's reverse geolocation data",
    "{place.names}": "list of place names from the photo's reverse geolocation data, joined with '_', for example, '18th St NW_Washington_DC_United States'",
    "{place.address}": "Postal address from the photo's reverse geolocation data, e.g. '2007 18th St NW, Washington, DC 20009, United States'",
    "{place.street}": "Street part of the postal address, e.g. '2007 18th St NW'",
    "{place.city}": "City part of the postal address, e.g. 'Washington'",
    "{place.state}": "State part of the postal address, e.g. 'DC'",
    "{place.postal_code}": "Postal code part of the postal address, e.g. '20009'",
    "{place.country}": "Country name of the postal code, e.g. 'United States'",
    "{place.country_code}": "ISO country code of the postal address, e.g. 'US'",
}


def render_filename_template(
    template: str, photo: PhotoInfo, none_str: str = "_"
) -> Tuple[str, list]:
    """ render a filename or directory template """

    if type(template) is not str:
        raise TypeError(f"template must be type str, not {type(template)}")

    if type(photo) is not PhotoInfo:
        raise TypeError(f"photo must be type osxphotos.PhotoInfo, not {type(photo)}")

    rendered = template
    original_name = pathlib.Path(photo.original_filename).stem
    current_name = pathlib.Path(photo.filename).stem
    created = DateTimeFormatter(photo.date)
    if photo.date_modified:
        modified = DateTimeFormatter(photo.date_modified)
    else:
        modified = None

    # make substitutions
    rendered = rendered.replace("{name}", current_name)
    rendered = rendered.replace("{original_name}", original_name)

    title = photo.title if photo.title is not None else none_str
    rendered = rendered.replace("{title}", f"{title}")

    descr = photo.description if photo.description is not None else none_str
    rendered = rendered.replace("{descr}", f"{descr}")

    rendered = rendered.replace("{created.date}", photo.date.date().isoformat())
    rendered = rendered.replace("{created.year}", created.year)
    rendered = rendered.replace("{created.yy}", created.yy)
    rendered = rendered.replace("{created.mm}", created.mm)
    rendered = rendered.replace("{created.month}", created.month)
    rendered = rendered.replace("{created.mon}", created.mon)
    rendered = rendered.replace("{created.doy}", created.doy)

    if modified is not None:
        rendered = rendered.replace(
            "{modified.date}", photo.date_modified.date().isoformat()
        )
        rendered = rendered.replace("{modified.year}", modified.year)
        rendered = rendered.replace("{modified.yy}", modified.yy)
        rendered = rendered.replace("{modified.mm}", modified.mm)
        rendered = rendered.replace("{modified.month}", modified.month)
        rendered = rendered.replace("{modified.mon}", modified.mon)
        rendered = rendered.replace("{modified.doy}", modified.doy)
    else:
        rendered = rendered.replace("{modified.year}", none_str)
        rendered = rendered.replace("{modified.yy}", none_str)
        rendered = rendered.replace("{modified.mm}", none_str)
        rendered = rendered.replace("{modified.month}", none_str)
        rendered = rendered.replace("{modified.mon}", none_str)
        rendered = rendered.replace("{modified.doy}", none_str)

    place_name = photo.place.name if photo.place and photo.place.name else none_str
    rendered = rendered.replace("{place.name}", place_name)

    place_names = (
        "_".join(photo.place.names) if photo.place and photo.place.names else none_str
    )
    rendered = rendered.replace("{place.names}", place_names)

    address = (
        photo.place.address_str if photo.place and photo.place.address_str else none_str
    )
    rendered = rendered.replace("{place.address}", address)

    street = (
        photo.place.address.street
        if photo.place and photo.place.address.street
        else none_str
    )
    rendered = rendered.replace("{place.street}", street)

    city = (
        photo.place.address.city
        if photo.place and photo.place.address.city
        else none_str
    )
    rendered = rendered.replace("{place.city}", city)

    state = (
        photo.place.address.state
        if photo.place and photo.place.address.state
        else none_str
    )
    rendered = rendered.replace("{place.state}", state)

    postal_code = (
        photo.place.address.state
        if photo.place and photo.place.address.postal_code
        else none_str
    )
    rendered = rendered.replace("{place.postal_code}", postal_code)

    country = (
        photo.place.address.state
        if photo.place and photo.place.address.country
        else none_str
    )
    rendered = rendered.replace("{place.country}", country)

    country_code = (
        photo.place.country_code
        if photo.place and photo.place.country_code
        else none_str
    )
    rendered = rendered.replace("{place.country_code}", country_code)

    # fix any escaped curly braces
    rendered = re.sub(r"\\{", "{", rendered)
    rendered = re.sub(r"\\}", "}", rendered)

    # find any {words} that weren't replaced
    unmatched = re.findall(r"{\w+}", rendered)

    return (rendered, unmatched)


class DateTimeFormatter:
    """ provides property access to formatted datetime.datetime strftime values """

    def __init__(self, dt: datetime.datetime):
        self.dt = dt

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
