""" Simple formatting of datetime.datetime objects """

import datetime


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
    def dd(self):
        """ 2-digit day of the month """
        dd = f"{self.dt.strftime('%d')}"
        return dd

    @property
    def dow(self):
        """ Day of week as locale's name """
        dow = f"{self.dt.strftime('%A')}"
        return dow

    @property
    def doy(self):
        """ Julian day of year starting from 001 """
        doy = f"{self.dt.strftime('%j')}"
        return doy
