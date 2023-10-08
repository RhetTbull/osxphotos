"""Dataclasses for comments and likes on shared photos"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass


@dataclass
class CommentInfo:
    """Class for shared photo comments"""

    datetime: datetime.datetime
    user: str
    ismine: bool
    text: str

    def asdict(self):
        return dataclasses.asdict(self)


@dataclass
class LikeInfo:
    """Class for shared photo likes"""

    datetime: datetime.datetime
    user: str
    ismine: bool

    def asdict(self):
        return dataclasses.asdict(self)
