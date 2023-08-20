"""Information about share participants for shared photos"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bpylist2 import archiver
from bpylist2.archive_types import DataclassArchiver

from .unicode import normalize_unicode

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
    name_components: PersonNameComponents = dataclasses.field(init=False)

    def __post_init__(self):
        self.name_components = PersonNameComponents.init_from_bplist(
            self._name_components
        )

    def asdict(self):
        """Return share participant as a dict"""
        dict_data = dataclasses.asdict(self)
        dict_data["name_components"] = self.name_components.asdict()


# @dataclasses.dataclass
# class _NSPersonNameComponentsDataXNSObject(DataclassArchiver):
#     """Dummy class"""

#     data: bytes


@dataclasses.dataclass
class NSPersonNameComponents(DataclassArchiver):
    """Python implementation of NSPersonNameComponents.

    Note: see https://developer.apple.com/documentation/foundation/nspersonnamecomponents?language=objc
    """

    NSnameComponentsPrivate: NSnameComponentsPrivate


@dataclasses.dataclass
class NSnameComponentsPrivate(DataclassArchiver):
    """Python implementation of NSnameComponentsPrivate."""

    _NSPersonNameComponentsData: _NSPersonNameComponentsData


@dataclasses.dataclass
class _NSPersonNameComponentsData(DataclassArchiver):
    """Python implementation of _NSPersonNameComponentsData."""

    NSgivenName: str
    NSmiddleName: str
    NSfamilyName: str
    NSnamePrefix: str
    NSnameSuffix: str
    NSnickname: str
    NSphoneticRepresentation: str


archiver.update_class_map(
    {
        "NSPersonNameComponents": NSPersonNameComponents,
        "NSnameComponentsPrivate": NSnameComponentsPrivate,
        "_NSPersonNameComponentsData": _NSPersonNameComponentsData,
        # "_NSPersonNameComponentsDataXNSObject": _NSPersonNameComponentsDataXNSObject,
    }
)


class PersonNameComponents:
    """Python representation of an NSPersonNameComponents object."""

    def __init__(
        self,
        given_name: str,
        middle_name: str,
        family_name: str,
        name_prefix: str,
        name_suffix: str,
        nickname: str,
        phonetic_representation: str,
    ) -> None:
        """Initialize PersonNameComponents."""
        self._given_name = given_name
        self._middle_name = middle_name
        self._family_name = family_name
        self._name_prefix = name_prefix
        self._name_suffix = name_suffix
        self._nickname = nickname
        self._phonetic_representation = phonetic_representation

    @staticmethod
    def init_from_bplist(bplist_data: bytes) -> PersonNameComponents:
        """Initialize from bplist data."""
        ns_person_name_components = archiver.unarchive(bplist_data)

        _given_name = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSgivenName
        )
        _middle_name = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSmiddleName
        )
        _family_name = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSfamilyName
        )
        _name_prefix = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSnamePrefix
        )
        _name_suffix = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSnameSuffix
        )
        _nickname = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSnickname
        )
        _phonetic_representation = normalize_unicode(
            ns_person_name_components.NSnameComponentsPrivate.NSphoneticRepresentation
        )

        return PersonNameComponents(
            _given_name,
            _middle_name,
            _family_name,
            _name_prefix,
            _name_suffix,
            _nickname,
            _phonetic_representation,
        )

    @property
    def given_name(self) -> str:
        """Return given name."""
        return self._given_name

    @property
    def middle_name(self) -> str:
        """Return middle name."""
        return self._middle_name

    @property
    def family_name(self) -> str:
        """Return family name."""
        return self._family_name

    @property
    def name_prefix(self) -> str:
        """Return name prefix."""
        return self._name_prefix

    @property
    def name_suffix(self) -> str:
        """Return name suffix."""
        return self._name_suffix

    @property
    def nickname(self) -> str:
        """Return nickname."""
        return self._nickname

    @property
    def phonetic_representation(self) -> str:
        """Return phonetic representation."""
        return self._phonetic_representation

    def asdict(self) -> dict[str, str]:
        """Return PersonNameComponents as dict."""
        return {
            "given_name": self._given_name,
            "middle_name": self._middle_name,
            "family_name": self._family_name,
            "name_prefix": self._name_prefix,
            "name_suffix": self._name_suffix,
            "nickname": self._nickname,
            "phonetic_representation": self._phonetic_representation,
        }

    def json(self) -> str:
        """Return PersonNameComponents as JSON."""
        return json.dumps(self.asdict())

    def __repr__(self) -> str:
        """Return string representation of PersonNameComponents."""
        return f"PersonNameComponents({self._given_name}, {self._middle_name}, {self._family_name}, {self._name_prefix}, {self._name_suffix}, {self._nickname}, {self._phonetic_representation})"

    def __str__(self) -> str:
        """Return string representation of PersonNameComponents."""
        return f"PersonNameComponents({self._given_name}, {self._middle_name}, {self._family_name}, {self._name_prefix}, {self._name_suffix}, {self._nickname}, {self._phonetic_representation})"
