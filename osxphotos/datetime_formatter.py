""" Simple formatting of datetime.datetime objects """

import datetime

__all__ = ["DateTimeFormatter"]


class DateTimeFormatter:
    """provides property access to formatted datetime.datetime strftime values"""

    def __init__(self, dt: datetime.datetime):
        self.dt = dt

    @property
    def date(self):
        """ISO date in form 2020-03-22"""
        return self.dt.date().isoformat()

    @property
    def year(self):
        """4 digit year"""
        return f"{self.dt.year}"

    @property
    def yy(self):
        """2 digit year"""
        return f"{self.dt.strftime('%y')}"

    @property
    def mm(self):
        """2 digit month"""
        return f"{self.dt.strftime('%m')}"

    @property
    def month(self):
        """Month as locale's full name"""
        return f"{self.dt.strftime('%B')}"

    @property
    def mon(self):
        """Month as locale's abbreviated name"""
        return f"{self.dt.strftime('%b')}"

    @property
    def dd(self):
        """2-digit day of the month"""
        return f"{self.dt.strftime('%d')}"

    @property
    def dow(self):
        """Day of week as locale's name"""
        return f"{self.dt.strftime('%A')}"

    @property
    def doy(self):
        """Julian day of year starting from 001"""
        return f"{self.dt.strftime('%j')}"

    @property
    def hour(self):
        """2-digit hour"""
        return f"{self.dt.strftime('%H')}"

    @property
    def min(self):
        """2-digit minute"""
        return f"{self.dt.strftime('%M')}"

    @property
    def sec(self):
        """2-digit second"""
        return f"{self.dt.strftime('%S')}"
