"""Information about share participants for shared photos"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .photosdb import PhotosDB


def get_share_participants(db: PhotosDB, uuid: str) -> list[ShareParticipant]:
    """Return list of ShareParticipant objects for the given database"""
    sql = """   SELECT
                ZSHAREPARTICIPANT.Z_PK,
                ZSHAREPARTICIPANT.ZACCEPTANCESTATUS,
                ZSHAREPARTICIPANT.ZISCURRENTUSER,
                ZSHAREPARTICIPANT.ZEXITSTATE,
                ZSHAREPARTICIPANT.ZPERMISSION,
                ZSHAREPARTICIPANT.ZPERSON,
                ZSHAREPARTICIPANT.Z54_SHARE,
                ZSHAREPARTICIPANT.ZSHARE,
                ZSHAREPARTICIPANT.ZEMAILADDRESS,
                ZSHAREPARTICIPANT.ZPARTICIPANTID,
                ZSHAREPARTICIPANT.ZPHONENUMBER,
                ZSHAREPARTICIPANT.ZUSERIDENTIFIER,
                ZSHAREPARTICIPANT.ZUUID,
                ZSHAREPARTICIPANT.ZNAMECOMPONENTS
                FROM ZSHAREPARTICIPANT
                JOIN ZASSETCONTRIBUTOR ON ZSHAREPARTICIPANT.Z_PK = ZASSETCONTRIBUTOR.ZPARTICIPANT
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.Z_PK = ZASSETCONTRIBUTOR.Z3LIBRARYSCOPEASSETCONTRIBUTORS
                JOIN ZASSET ON ZASSET.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSET
                WHERE ZASSET.ZUUID = '{}';""".format(
        uuid
    )

    rows = db.execute(sql)
    return [ShareParticipant(*row) for row in rows]


@dataclass
class ShareParticipant:
    """Information about a share participant"""

    _pk: int
    _acceptance_status: int
    is_current_user: bool
    _exit_state: int
    _permission: int
    _person: int
    _z54_share: int
    _share: int
    email_address: str
    participant_id: str
    phone_number: str
    user_identifier: str
    uuid: str
    _name_components: bytes

    def asdict(self):
        """Return share participant as a dict"""
        return dataclasses.asdict(self)
