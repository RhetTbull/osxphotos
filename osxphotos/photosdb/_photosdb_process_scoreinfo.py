""" Methods for PhotosDB to add Photos 5 photo score info 
    ref: https://simonwillison.net/2020/May/21/dogsheep-photos/
"""

import logging

from .._constants import _DB_TABLE_NAMES, _PHOTOS_4_VERSION
from ..utils import _open_sql_file
from .photosdb_utils import get_db_version

"""
    This module should be imported in the class defintion of PhotosDB in photosdb.py
    Do not import this module directly
    This module adds the following method to PhotosDB:
        _process_scoreinfo: process photo score info 

    The following data structures are added to PhotosDB
        self._db_scoreinfo_uuid
    
    These methods only work on Photos 5 databases.  Will print warning on earlier library versions.
"""


def _process_scoreinfo(self):
    """ Process computed photo scores
        Note: Only works on Photos version == 5.0
    """

    # _db_scoreinfo_uuid is dict in form {uuid: {score values}}
    self._db_scoreinfo_uuid = {}

    if self._db_version <= _PHOTOS_4_VERSION:
        raise NotImplementedError(
            f"search info not implemented for this database version"
        )
    else:
        _process_scoreinfo_5(self)


def _process_scoreinfo_5(photosdb):
    """ Process computed photo scores for Photos 5 databases

    Args:
        photosdb: an OSXPhotosDB instance
    """

    db = photosdb._tmp_db

    asset_table = _DB_TABLE_NAMES[photosdb._photos_ver]["ASSET"]

    (conn, cursor) = _open_sql_file(db)

    result = cursor.execute(
        f"""
        SELECT 
        {asset_table}.ZUUID,
        {asset_table}.ZOVERALLAESTHETICSCORE,
        {asset_table}.ZCURATIONSCORE,
        {asset_table}.ZPROMOTIONSCORE,
        {asset_table}.ZHIGHLIGHTVISIBILITYSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZBEHAVIORALSCORE, 
        ZCOMPUTEDASSETATTRIBUTES.ZFAILURESCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZHARMONIOUSCOLORSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZIMMERSIVENESSSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZINTERACTIONSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZINTERESTINGSUBJECTSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZINTRUSIVEOBJECTPRESENCESCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZLIVELYCOLORSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZLOWLIGHT,
        ZCOMPUTEDASSETATTRIBUTES.ZNOISESCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTCAMERATILTSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTCOMPOSITIONSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTLIGHTINGSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPATTERNSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPERSPECTIVESCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPOSTPROCESSINGSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTREFLECTIONSSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTSYMMETRYSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZSHARPLYFOCUSEDSUBJECTSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZTASTEFULLYBLURREDSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZWELLCHOSENSUBJECTSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZWELLFRAMEDSUBJECTSCORE,
        ZCOMPUTEDASSETATTRIBUTES.ZWELLTIMEDSHOTSCORE
        FROM {asset_table}
        JOIN ZCOMPUTEDASSETATTRIBUTES ON ZCOMPUTEDASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
        """
    )

    # 0     ZGENERICASSET.ZUUID,
    # 1     ZGENERICASSET.ZOVERALLAESTHETICSCORE,
    # 2     ZGENERICASSET.ZCURATIONSCORE,
    # 3     ZGENERICASSET.ZPROMOTIONSCORE,
    # 4     ZGENERICASSET.ZHIGHLIGHTVISIBILITYSCORE,
    # 5     ZCOMPUTEDASSETATTRIBUTES.ZBEHAVIORALSCORE,
    # 6     ZCOMPUTEDASSETATTRIBUTES.ZFAILURESCORE,
    # 7     ZCOMPUTEDASSETATTRIBUTES.ZHARMONIOUSCOLORSCORE,
    # 8     ZCOMPUTEDASSETATTRIBUTES.ZIMMERSIVENESSSCORE,
    # 9     ZCOMPUTEDASSETATTRIBUTES.ZINTERACTIONSCORE,
    # 10    ZCOMPUTEDASSETATTRIBUTES.ZINTERESTINGSUBJECTSCORE,
    # 11    ZCOMPUTEDASSETATTRIBUTES.ZINTRUSIVEOBJECTPRESENCESCORE,
    # 12    ZCOMPUTEDASSETATTRIBUTES.ZLIVELYCOLORSCORE,
    # 13    ZCOMPUTEDASSETATTRIBUTES.ZLOWLIGHT,
    # 14    ZCOMPUTEDASSETATTRIBUTES.ZNOISESCORE,
    # 15    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTCAMERATILTSCORE,
    # 16    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTCOMPOSITIONSCORE,
    # 17    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTLIGHTINGSCORE,
    # 18    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPATTERNSCORE,
    # 19    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPERSPECTIVESCORE,
    # 20    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTPOSTPROCESSINGSCORE,
    # 21    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTREFLECTIONSSCORE,
    # 22    ZCOMPUTEDASSETATTRIBUTES.ZPLEASANTSYMMETRYSCORE,
    # 23    ZCOMPUTEDASSETATTRIBUTES.ZSHARPLYFOCUSEDSUBJECTSCORE,
    # 24    ZCOMPUTEDASSETATTRIBUTES.ZTASTEFULLYBLURREDSCORE,
    # 25    ZCOMPUTEDASSETATTRIBUTES.ZWELLCHOSENSUBJECTSCORE,
    # 26    ZCOMPUTEDASSETATTRIBUTES.ZWELLFRAMEDSUBJECTSCORE,
    # 27    ZCOMPUTEDASSETATTRIBUTES.ZWELLTIMEDSHOTSCORE

    for row in result:
        uuid = row[0]
        scores = {"uuid": uuid}
        scores["overall_aesthetic"] = row[1]
        scores["curation"] = row[2]
        scores["promotion"] = row[3]
        scores["highlight_visibility"] = row[4]
        scores["behavioral"] = row[5]
        scores["failure"] = row[6]
        scores["harmonious_color"] = row[7]
        scores["immersiveness"] = row[8]
        scores["interaction"] = row[9]
        scores["interesting_subject"] = row[10]
        scores["intrusive_object_presence"] = row[11]
        scores["lively_color"] = row[12]
        scores["low_light"] = row[13]
        scores["noise"] = row[14]
        scores["pleasant_camera_tilt"] = row[15]
        scores["pleasant_composition"] = row[16]
        scores["pleasant_lighting"] = row[17]
        scores["pleasant_pattern"] = row[18]
        scores["pleasant_perspective"] = row[19]
        scores["pleasant_post_processing"] = row[20]
        scores["pleasant_reflection"] = row[21]
        scores["pleasant_symmetry"] = row[22]
        scores["sharply_focused_subject"] = row[23]
        scores["tastefully_blurred"] = row[24]
        scores["well_chosen_subject"] = row[25]
        scores["well_framed_subject"] = row[26]
        scores["well_timed_shot"] = row[27]
        photosdb._db_scoreinfo_uuid[uuid] = scores

    conn.close()