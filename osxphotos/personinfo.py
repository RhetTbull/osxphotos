""" PhotoInfo methods to expose info about person in the Photos library """

import json
import logging


class PersonInfo:
    """ Info about a person in the Photos library
    """

    def __init__(self, db=None, pk=None):
        """ Creates a new PersonInfo instance

        Arguments:
            db: instance of PhotosDB object
            pk: primary key value of person to initialize PersonInfo with    
        
        Returns:
            PersonInfo instance
        """
        self._db = db
        self._pk = pk

        person = self._db._dbpersons_pk[pk]
        self.uuid = person["uuid"]
        self.name = person["fullname"]
        self.display_name = person["displayname"]
        self.keyface = person["keyface"]
        self.facecount = person["facecount"]

    @property
    def keyphoto(self):
        try:
            return self._keyphoto
        except AttributeError:
            person = self._db._dbpersons_pk[self._pk]
            if person["photo_uuid"]:
                try:
                    key_photo = self._db.get_photo(person["photo_uuid"])
                except IndexError:
                    key_photo = None
            else:
                key_photo = None
            self._keyphoto = key_photo
            return self._keyphoto

    @property
    def photos(self):
        """ Returns list of PhotoInfo objects associated with this person """
        return self._db.photos_by_uuid(self._db._dbfaces_pk[self._pk])

    def json(self):
        """ Returns JSON representation of class instance """
        keyphoto = self.keyphoto.uuid if self.keyphoto is not None else None
        person = {
            "uuid": self.uuid,
            "name": self.name,
            "displayname": self.display_name,
            "keyface": self.keyface,
            "facecount": self.facecount,
            "keyphoto": keyphoto,
        }
        return json.dumps(person)

    def __str__(self):
        return f"PersonInfo(name={self.name}, display_name={self.display_name}, uuid={self.uuid}, facecount={self.facecount})"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            getattr(self, field) == getattr(other, field) for field in ["_db", "_pk"]
        )

    def __ne__(self, other):
        return not self.__eq__(other)
