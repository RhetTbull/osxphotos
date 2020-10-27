""" PhotoInfo and FaceInfo classes to expose info about persons and faces in the Photos library """

import json
import logging
import math


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

    @property
    def face_info(self):
        """ Returns a list of FaceInfo objects associated with this person sorted by quality score
            Highest quality face is result[0] and lowest quality face is result[n] 
        """
        try:
            faces = self._db._db_faceinfo_person[self._pk]
            return sorted(
                [FaceInfo(db=self._db, pk=face) for face in faces],
                key=lambda face: face.quality,
                reverse=True,
            )
        except KeyError:
            # no faces
            return []

    def asdict(self):
        """ Returns dictionary representation of class instance """
        keyphoto = self.keyphoto.uuid if self.keyphoto is not None else None
        return {
            "uuid": self.uuid,
            "name": self.name,
            "displayname": self.display_name,
            "keyface": self.keyface,
            "facecount": self.facecount,
            "keyphoto": keyphoto,
        }

    def json(self):
        """ Returns JSON representation of class instance """
        return json.dumps(self.asdict())

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


class FaceInfo:
    """ Info about a face in the Photos library
    """

    def __init__(self, db=None, pk=None):
        """ Creates a new FaceInfo instance

        Arguments:
            db: instance of PhotosDB object
            pk: primary key value of face to init the object with    
        
        Returns:
            FaceInfo instance
        """
        self._db = db
        self._pk = pk

        face = self._db._db_faceinfo_pk[pk]
        self._info = face
        self.uuid = face["uuid"]
        self.name = face["fullname"]
        self.asset_uuid = face["asset_uuid"]
        self._person_pk = face["person"]
        self.center_x = face["centerx"]
        self.center_y = face["centery"]
        self.mouth_x = face["mouthx"]
        self.mouth_y = face["mouthy"]
        self.left_eye_x = face["lefteyex"]
        self.left_eye_y = face["lefteyey"]
        self.right_eye_x = face["righteyex"]
        self.right_eye_y = face["righteyey"]
        self.size = face["size"]
        self.quality = face["quality"]
        self.source_width = face["sourcewidth"]
        self.source_height = face["sourceheight"]
        self.has_smile = face["has_smile"]
        self.left_eye_closed = face["left_eye_closed"]
        self.right_eye_closed = face["right_eye_closed"]
        self.manual = face["manual"]
        self.face_type = face["facetype"]
        self.age_type = face["agetype"]
        self.bald_type = face["baldtype"]
        self.eye_makeup_type = face["eyemakeuptype"]
        self.eye_state = face["eyestate"]
        self.facial_hair_type = face["facialhairtype"]
        self.gender_type = face["gendertype"]
        self.glasses_type = face["glassestype"]
        self.hair_color_type = face["haircolortype"]
        self.intrash = face["intrash"]
        self.lip_makeup_type = face["lipmakeuptype"]
        self.smile_type = face["smiletype"]

    @property
    def center(self):
        """ Coordinates, in PIL format, for center of face 

        Returns:
            tuple of coordinates in form (x, y)
        """
        return self._make_point((self.center_x, self.center_y))

    @property
    def size_pixels(self):
        """ Size of face in pixels (centered around center_x, center_y)

        Returns:
            size, in int pixels, of a circle drawn around the center of the face
        """
        photo = self.photo
        size_reference = photo.width if photo.width > photo.height else photo.height
        return self.size * size_reference

    @property
    def mouth(self):
        """ Coordinates, in PIL format, for mouth position

        Returns:
            tuple of coordinates in form (x, y)
        """
        return self._make_point_with_rotation((self.mouth_x, self.mouth_y))

    @property
    def left_eye(self):
        """ Coordinates, in PIL format, for left eye position

        Returns:
            tuple of coordinates in form (x, y)
        """
        return self._make_point_with_rotation((self.left_eye_x, self.left_eye_y))

    @property
    def right_eye(self):
        """ Coordinates, in PIL format, for right eye position

        Returns:
            tuple of coordinates in form (x, y)
        """
        return self._make_point_with_rotation((self.right_eye_x, self.right_eye_y))

    @property
    def person_info(self):
        """ PersonInfo instance for person associated with this face """
        try:
            return self._person
        except AttributeError:
            self._person = PersonInfo(db=self._db, pk=self._person_pk)
            return self._person

    @property
    def photo(self):
        """ PhotoInfo instance associated with this face """
        try:
            return self._photo
        except AttributeError:
            self._photo = self._db.get_photo(self.asset_uuid)
            if self._photo is None:
                logging.warning(f"Could not get photo for uuid: {self.asset_uuid}")
            return self._photo

    def face_rect(self):
        """ Get face rectangle coordinates for current version of the associated image
            If image has been edited, rectangle applies to edited version, otherwise original version
            Coordinates in format and reference frame used by PIL

        Returns:
            list [(x0, x1), (y0, y1)] of coordinates in reference frame used by PIL
        """
        photo = self.photo
        size_reference = photo.width if photo.width > photo.height else photo.height
        radius = (self.size / 2) * size_reference
        x, y = self._make_point((self.center_x, self.center_y))
        x0, y0 = x - radius, y - radius
        x1, y1 = x + radius, y + radius
        return [(x0, y0), (x1, y1)]

    def roll_pitch_yaw(self):
        """ Roll, pitch, yaw of face in radians as tuple """
        info = self._info
        roll = 0 if info["roll"] is None else info["roll"]
        pitch = 0 if info["pitch"] is None else info["pitch"]
        yaw = 0 if info["yaw"] is None else info["yaw"]

        return (roll, pitch, yaw)

    @property
    def roll(self):
        """ Return roll angle in radians of the face region """
        roll, _, _ = self.roll_pitch_yaw()
        return roll

    @property
    def pitch(self):
        """ Return pitch angle in radians of the face region """
        _, pitch, _ = self.roll_pitch_yaw()
        return pitch

    @property
    def yaw(self):
        """ Return yaw angle in radians of the face region """
        _, _, yaw = self.roll_pitch_yaw()
        return yaw

    def _make_point(self, xy):
        """ Translate an (x, y) tuple based on image orientation
            and convert to image coordinates

        Arguments:
            xy: tuple of (x, y) coordinates for point to translate
                in format used by Photos (percent of height/width)
        
        Returns:
            (x, y) tuple of translated coordinates in pixels in PIL format/reference frame
        """
        # Reference: https://github.com/neilpa/phace/blob/7594776480505d0c389688a42099c94ac5d34f3f/cmd/phace/draw.go#L79-L94

        orientation = self.photo.orientation
        x, y = xy
        dx = self.photo.width
        dy = self.photo.height
        if orientation in [1, 2]:
            y = 1.0 - y
        elif orientation in [3, 4]:
            x = 1.0 - x
        elif orientation in [5, 6]:
            x, y = 1.0 - y, 1.0 - x
            dx, dy = dy, dx
        elif orientation in [7, 8]:
            x, y = y, x
            dx, dy = dy, dx
        else:
            logging.warning(f"Unhandled orientation: {orientation}")

        return (int(x * dx), int(y * dy))

    def _make_point_with_rotation(self, xy):
        """ Translate an (x, y) tuple based on image orientation and rotation
            and convert to image coordinates

        Arguments:
            xy: tuple of (x, y) coordinates for point to translate
                in format used by Photos (percent of height/width)
        
        Returns:
            (x, y) tuple of translated coordinates in pixels in PIL format/reference frame
        """

        # convert to image coordinates
        x, y = self._make_point(xy)

        # rotate about center
        xmid, ymid = self.center
        roll, _, _ = self.roll_pitch_yaw()
        xr, yr = rotate_image_point(x, y, xmid, ymid, roll)

        return (int(xr), int(yr))

    def asdict(self):
        """ Returns dict representation of class instance """
        roll, pitch, yaw = self.roll_pitch_yaw()
        return {
            "_pk": self._pk,
            "uuid": self.uuid,
            "name": self.name,
            "asset_uuid": self.asset_uuid,
            "_person_pk": self._person_pk,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "center": self.center,
            "mouth_x": self.mouth_x,
            "mouth_y": self.mouth_y,
            "mouth": self.mouth,
            "left_eye_x": self.left_eye_x,
            "left_eye_y": self.left_eye_y,
            "left_eye": self.left_eye,
            "right_eye_x": self.right_eye_x,
            "right_eye_y": self.right_eye_y,
            "right_eye": self.right_eye,
            "size": self.size,
            "face_rect": self.face_rect(),
            "roll": roll,
            "pitch": pitch,
            "yaw": yaw,
            "quality": self.quality,
            "source_width": self.source_width,
            "source_height": self.source_height,
            "has_smile": self.has_smile,
            "left_eye_closed": self.left_eye_closed,
            "right_eye_closed": self.right_eye_closed,
            "manual": self.manual,
            "face_type": self.face_type,
            "age_type": self.age_type,
            "bald_type": self.bald_type,
            "eye_makeup_type": self.eye_makeup_type,
            "eye_state": self.eye_state,
            "facial_hair_type": self.facial_hair_type,
            "gender_type": self.gender_type,
            "glasses_type": self.glasses_type,
            "hair_color_type": self.hair_color_type,
            "intrash": self.intrash,
            "lip_makeup_type": self.lip_makeup_type,
            "smile_type": self.smile_type,
        }

    def json(self):
        """ Return JSON representation of FaceInfo instance """
        return json.dumps(self.asdict())

    def __str__(self):
        return f"FaceInfo(uuid={self.uuid}, center_x={self.center_x}, center_y = {self.center_y}, size={self.size}, person={self.name}, asset_uuid={self.asset_uuid})"

    def __repr__(self):
        return f"FaceInfo(db={self._db}, pk={self._pk})"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            getattr(self, field) == getattr(other, field) for field in ["_db", "_pk"]
        )

    def __ne__(self, other):
        return not self.__eq__(other)


def rotate_image_point(x, y, xmid, ymid, angle):
    """ rotate image point about xm, ym by angle in radians

    Arguments:
        x: x coordinate of point to rotate    
        y: y coordinate of point to rotate
        xmid: x coordinate of center point to rotate about
        ymid: y coordinate of center point to rotate about
        angle: angle in radians about which to coordinate, 
            counter-clockwise is positive

    Returns:
        tuple of rotated points (xr, yr)
    """
    # translate point relative to the mid point
    x = x - xmid
    y = y - ymid

    # rotate by angle and translate back
    # the photo coordinate system is downwards y is positive so
    # need to adjust the rotation accordingly
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    xr = x * cos_angle + y * sin_angle + xmid
    yr = -x * sin_angle + y * cos_angle + ymid

    return (xr, yr)
