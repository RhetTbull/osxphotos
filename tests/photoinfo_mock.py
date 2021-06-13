"""Selectively mock a PhotoInfo object"""

from osxphotos import PhotoInfo


class PhotoInfoMock(PhotoInfo):
    def __init__(self, photo, **kwargs):
        self._photo = photo
        self._db = photo._db
        self._info = photo._info
        self._uuid = photo.uuid

        for kw in kwargs:
            if hasattr(photo, kw):
                setattr(self, f"_mock_{kw}", kwargs[kw])
            else:
                raise ValueError(f"Not a PhotoInfo attribute: {kw}")

    @property
    def hdr(self):
        return (
            self._mock_hdr
            if getattr(self, "_mock_hdr", None) is not None
            else self._photo.hdr
        )

    @property
    def favorite(self):
        return (
            self._mock_favorite
            if getattr(self, "_mock_favorite", None) is not None
            else self._photo.favorite
        )

    @property
    def hasadjustments(self):
        return (
            self._mock_hasadjustments
            if getattr(self, "_mock_hasadjustments", None) is not None
            else self._photo.hasadjustments
        )

    @property
    def keywords(self):
        return (
            self._mock_keywords
            if getattr(self, "_mock_keywords", None) is not None
            else self._photo.keywords
        )

    @property
    def title(self):
        return (
            self._mock_title
            if getattr(self, "_mock_title", None) is not None
            else self._photo.title
        )
