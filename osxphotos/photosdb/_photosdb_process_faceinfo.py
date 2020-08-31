""" Methods for PhotosDB to add Photos face info 
"""

import logging

from .._constants import _DB_TABLE_NAMES, _PHOTOS_4_VERSION
from ..utils import _open_sql_file, normalize_unicode
from .photosdb_utils import get_db_version


"""
    This module should be imported in the class defintion of PhotosDB in photosdb.py
    Do not import this module directly
    This module adds the following method to PhotosDB:
        _process_faceinfo: process photo face info 

    The following data structures are added to PhotosDB
        self._db_faceinfo_pk: {pk: {faceinfo}}
        self._db_faceinfo_uuid: {photo uuid: [face pk]}
        self._db_faceinfo_person: {person_pk: [face_pk]}
"""


def _process_faceinfo(self):
    """ Process face information
    """

    self._db_faceinfo_pk = {}
    self._db_faceinfo_uuid = {}
    self._db_faceinfo_person = {}

    if self._db_version <= _PHOTOS_4_VERSION:
        _process_faceinfo_4(self)
    else:
        _process_faceinfo_5(self)


def _process_faceinfo_4(photosdb):
    """ Process face information for Photos 4 databases

    Args:
        photosdb: an OSXPhotosDB instance
    """
    db = photosdb._tmp_db

    (conn, cursor) = _open_sql_file(db)

    result = cursor.execute(
        """
        SELECT
        RKFace.modelId,
        RKVersion.uuid, 
        RKFace.uuid,
        RKPerson.name,
        RKFace.isInTrash,
        RKFace.personId,
        RKFace.imageModelId, 
        RKFace.sourceWidth,
        RKFace.sourceHeight, 
        RKFace.centerX,
        RKFace.centerY,
        RKFace.size,
        RKFace.leftEyeX, 
        RKFace.leftEyeY,
        RKFace.rightEyeX, 
        RKFace.rightEyeY, 
        RKFace.mouthX,
        RKFace.mouthY, 
        RKFace.hidden, 
        RKFace.manual, 
        RKFace.hasSmile, 
        RKFace.isLeftEyeClosed, 
        RKFace.isRightEyeClosed, 
        RKFace.poseRoll, 
        RKFace.poseYaw, 
        RKFace.posePitch, 
        RKFace.faceType,
        RKFace.qualityMeasure
        FROM
        RKFace
        JOIN RKPerson on RKPerson.modelId = RKFace.personId
        JOIN RKVersion on RKVersion.modelId = RKFace.imageModelId
        """
    )

    # 0     RKFace.modelId,
    # 1     RKVersion.uuid,
    # 2     RKFace.uuid,
    # 3     RKPerson.name,
    # 4     RKFace.isInTrash,
    # 5     RKFace.personId,
    # 6     RKFace.imageModelId,
    # 7     RKFace.sourceWidth,
    # 8     RKFace.sourceHeight,
    # 9     RKFace.centerX,
    # 10    RKFace.centerY,
    # 11    RKFace.size,
    # 12    RKFace.leftEyeX,
    # 13    RKFace.leftEyeY,
    # 14    RKFace.rightEyeX,
    # 15    RKFace.rightEyeY,
    # 16    RKFace.mouthX,
    # 17    RKFace.mouthY,
    # 18    RKFace.hidden,
    # 19    RKFace.manual,
    # 20    RKFace.hasSmile,
    # 21    RKFace.isLeftEyeClosed,
    # 22    RKFace.isRightEyeClosed,
    # 23    RKFace.poseRoll,
    # 24    RKFace.poseYaw,
    # 25    RKFace.posePitch,
    # 26    RKFace.faceType,
    # 27    RKFace.qualityMeasure

    for row in result:
        modelid = row[0]
        asset_uuid = row[1]
        person_id = row[5]
        face = {}
        face["pk"] = modelid
        face["asset_uuid"] = asset_uuid
        face["uuid"] = row[2]
        face["person"] = person_id
        face["fullname"] = normalize_unicode(row[3])
        face["sourcewidth"] = row[7]
        face["sourceheight"] = row[8]
        face["centerx"] = row[9]
        face["centery"] = row[10]
        face["size"] = row[11]
        face["lefteyex"] = row[12]
        face["lefteyey"] = row[13]
        face["righteyex"] = row[14]
        face["righteyey"] = row[15]
        face["mouthx"] = row[16]
        face["mouthy"] = row[17]
        face["hidden"] = row[18]
        face["manual"] = row[19]
        face["has_smile"] = row[20]
        face["left_eye_closed"] = row[21]
        face["right_eye_closed"] = row[22]
        face["roll"] = row[23]
        face["yaw"] = row[24]
        face["pitch"] = row[25]
        face["facetype"] = row[26]
        face["quality"] = row[27]

        # Photos 5 only
        face["agetype"] = None
        face["baldtype"] = None
        face["eyemakeuptype"] = None
        face["eyestate"] = None
        face["facialhairtype"] = None
        face["gendertype"] = None
        face["glassestype"] = None
        face["haircolortype"] = None
        face["intrash"] = None
        face["lipmakeuptype"] = None
        face["smiletype"] = None

        photosdb._db_faceinfo_pk[modelid] = face

        try:
            photosdb._db_faceinfo_uuid[asset_uuid].append(modelid)
        except KeyError:
            photosdb._db_faceinfo_uuid[asset_uuid] = [modelid]

        try:
            photosdb._db_faceinfo_person[person_id].append(modelid)
        except KeyError:
            photosdb._db_faceinfo_person[person_id] = [modelid]

    conn.close()


def _process_faceinfo_5(photosdb):
    """ Process face information for Photos 5 databases

    Args:
        photosdb: an OSXPhotosDB instance
    """

    db = photosdb._tmp_db

    asset_table = _DB_TABLE_NAMES[photosdb._photos_ver]["ASSET"]

    (conn, cursor) = _open_sql_file(db)

    result = cursor.execute(
        f""" 
        SELECT
        ZDETECTEDFACE.Z_PK,
        {asset_table}.ZUUID,
        ZDETECTEDFACE.ZUUID,
        ZDETECTEDFACE.ZPERSON,
        ZPERSON.ZFULLNAME,
        ZDETECTEDFACE.ZAGETYPE,
        ZDETECTEDFACE.ZBALDTYPE,
        ZDETECTEDFACE.ZEYEMAKEUPTYPE,
        ZDETECTEDFACE.ZEYESSTATE,
        ZDETECTEDFACE.ZFACIALHAIRTYPE,
        ZDETECTEDFACE.ZGENDERTYPE,
        ZDETECTEDFACE.ZGLASSESTYPE,
        ZDETECTEDFACE.ZHAIRCOLORTYPE,
        ZDETECTEDFACE.ZHASSMILE,
        ZDETECTEDFACE.ZHIDDEN,
        ZDETECTEDFACE.ZISINTRASH,
        ZDETECTEDFACE.ZISLEFTEYECLOSED,
        ZDETECTEDFACE.ZISRIGHTEYECLOSED,
        ZDETECTEDFACE.ZLIPMAKEUPTYPE,
        ZDETECTEDFACE.ZMANUAL,
        ZDETECTEDFACE.ZQUALITYMEASURE,
        ZDETECTEDFACE.ZSMILETYPE,
        ZDETECTEDFACE.ZSOURCEHEIGHT,
        ZDETECTEDFACE.ZSOURCEWIDTH,
        ZDETECTEDFACE.ZBLURSCORE,
        ZDETECTEDFACE.ZCENTERX,
        ZDETECTEDFACE.ZCENTERY,
        ZDETECTEDFACE.ZLEFTEYEX,
        ZDETECTEDFACE.ZLEFTEYEY,
        ZDETECTEDFACE.ZMOUTHX,
        ZDETECTEDFACE.ZMOUTHY,
        ZDETECTEDFACE.ZPOSEYAW,
        ZDETECTEDFACE.ZQUALITY,
        ZDETECTEDFACE.ZRIGHTEYEX,
        ZDETECTEDFACE.ZRIGHTEYEY,
        ZDETECTEDFACE.ZROLL,
        ZDETECTEDFACE.ZSIZE,
        ZDETECTEDFACE.ZYAW,
        ZDETECTEDFACE.ZMASTERIDENTIFIER
        FROM ZDETECTEDFACE
        JOIN {asset_table} ON {asset_table}.Z_PK = ZDETECTEDFACE.ZASSET
        JOIN ZPERSON ON ZPERSON.Z_PK = ZDETECTEDFACE.ZPERSON;
        """
    )

    # 0    ZDETECTEDFACE.Z_PK
    # 1    ZGENERICASSET.ZUUID,
    # 2    ZDETECTEDFACE.ZUUID,
    # 3    ZDETECTEDFACE.ZPERSON,
    # 4    ZPERSON.ZFULLNAME,
    # 5    ZDETECTEDFACE.ZAGETYPE,
    # 6    ZDETECTEDFACE.ZBALDTYPE,
    # 7    ZDETECTEDFACE.ZEYEMAKEUPTYPE,
    # 8    ZDETECTEDFACE.ZEYESSTATE,
    # 9    ZDETECTEDFACE.ZFACIALHAIRTYPE,
    # 10   ZDETECTEDFACE.ZGENDERTYPE,
    # 11   ZDETECTEDFACE.ZGLASSESTYPE,
    # 12   ZDETECTEDFACE.ZHAIRCOLORTYPE,
    # 13   ZDETECTEDFACE.ZHASSMILE,
    # 14   ZDETECTEDFACE.ZHIDDEN,
    # 15   ZDETECTEDFACE.ZISINTRASH,
    # 16   ZDETECTEDFACE.ZISLEFTEYECLOSED,
    # 17   ZDETECTEDFACE.ZISRIGHTEYECLOSED,
    # 18   ZDETECTEDFACE.ZLIPMAKEUPTYPE,
    # 19   ZDETECTEDFACE.ZMANUAL,
    # 20   ZDETECTEDFACE.ZQUALITYMEASURE,
    # 21   ZDETECTEDFACE.ZSMILETYPE,
    # 22   ZDETECTEDFACE.ZSOURCEHEIGHT,
    # 23   ZDETECTEDFACE.ZSOURCEWIDTH,
    # 24   ZDETECTEDFACE.ZBLURSCORE,
    # 25   ZDETECTEDFACE.ZCENTERX,
    # 26   ZDETECTEDFACE.ZCENTERY,
    # 27   ZDETECTEDFACE.ZLEFTEYEX,
    # 28   ZDETECTEDFACE.ZLEFTEYEY,
    # 29   ZDETECTEDFACE.ZMOUTHX,
    # 30   ZDETECTEDFACE.ZMOUTHY,
    # 31   ZDETECTEDFACE.ZPOSEYAW,
    # 32   ZDETECTEDFACE.ZQUALITY,
    # 33   ZDETECTEDFACE.ZRIGHTEYEX,
    # 34   ZDETECTEDFACE.ZRIGHTEYEY,
    # 35   ZDETECTEDFACE.ZROLL,
    # 36   ZDETECTEDFACE.ZSIZE,
    # 37   ZDETECTEDFACE.ZYAW,
    # 38   ZDETECTEDFACE.ZMASTERIDENTIFIER

    for row in result:
        pk = row[0]
        asset_uuid = row[1]
        person_pk = row[3]
        face = {}
        face["pk"] = pk
        face["asset_uuid"] = asset_uuid
        face["uuid"] = row[2]
        face["person"] = person_pk
        face["fullname"] = normalize_unicode(row[4])
        face["agetype"] = row[5]
        face["baldtype"] = row[6]
        face["eyemakeuptype"] = row[7]
        face["eyestate"] = row[8]
        face["facialhairtype"] = row[9]
        face["gendertype"] = row[10]
        face["glassestype"] = row[11]
        face["haircolortype"] = row[12]
        face["has_smile"] = row[13]
        face["hidden"] = row[14]
        face["intrash"] = row[15]
        face["left_eye_closed"] = row[16]
        face["right_eye_closed"] = row[17]
        face["lipmakeuptype"] = row[18]
        face["manual"] = row[19]
        face["smiletype"] = row[21]
        face["sourceheight"] = row[22]
        face["sourcewidth"] = row[23]
        face["facetype"] = None  # Photos 4 only
        face["centerx"] = row[25]
        face["centery"] = row[26]
        face["lefteyex"] = row[27]
        face["lefteyey"] = row[28]
        face["mouthx"] = row[29]
        face["mouthy"] = row[30]
        face["quality"] = row[32]
        face["righteyex"] = row[33]
        face["righteyey"] = row[34]
        face["roll"] = row[35]
        face["size"] = row[36]
        face["yaw"] = row[37]
        face["pitch"] = 0.0  # not defined in Photos 5

        photosdb._db_faceinfo_pk[pk] = face

        try:
            photosdb._db_faceinfo_uuid[asset_uuid].append(pk)
        except KeyError:
            photosdb._db_faceinfo_uuid[asset_uuid] = [pk]

        try:
            photosdb._db_faceinfo_person[person_pk].append(pk)
        except KeyError:
            photosdb._db_faceinfo_person[person_pk] = [pk]

    conn.close()
