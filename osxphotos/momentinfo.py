__all__ = ["MomentInfo"]
"""MomentInfo class with details about photo moments."""


class MomentInfo:
    """Info about a photo moment"""

    def __init__(self, db, moment_pk):
        """Initialize with a moment PK; returns None if PK not found."""
        self._db = db
        self._pk = moment_pk

        self._moment = self._db._db_moment_pk.get(moment_pk)
        if not self._moment:
            raise ValueError(f"No moment with PK {moment_pk}")

    @property
    def pk(self):
        """Primary key of the moment."""
        return self._pk

    @property
    def location(self):
        """Location of the moment."""
        return (self._moment.get("latitude"), self._moment.get("longitude"))

    @property
    def title(self):
        """Title of the moment."""
        return self._moment.get("title")

    @property
    def subtitle(self):
        """Subtitle of the moment."""
        return self._moment.get("subtitle")

    @property
    def start_date(self):
        """Start date of the moment."""
        return self._moment.get("startDate")

    @property
    def end_date(self):
        """Stop date of the moment."""
        return self._moment.get("endDate")

    @property
    def date(self):
        """Date of the moment."""
        return self._moment.get("representativeDate")

    @property
    def modification_date(self):
        """Modification date of the moment."""
        return self._moment.get("modificationDate")

    @property
    def photos(self):
        """All photos in this moment"""
        try:
            return self._photos
        except AttributeError:
            photo_uuids = [
                uuid
                for uuid, photo in self._db._dbphotos.items()
                if photo["momentID"] == self._pk
            ]

            self._photos = self._db.photos_by_uuid(photo_uuids)
            return self._photos

    def asdict(self):
        """Returns all moment info as dictionary"""
        return {
            "pk": self.pk,
            "location": self.location,
            "title": self.title,
            "subtitle": self.subtitle,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "date": self.date.isoformat() if self.date else None,
            "modification_date": self.modification_date.isoformat()
            if self.modification_date
            else None,
            "photos": self.photos,
        }
