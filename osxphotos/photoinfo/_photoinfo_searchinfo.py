""" Methods and class for PhotoInfo exposing SearchInfo data such as labels 
    Adds the following properties to PhotoInfo (valid only for Photos 5):
        search_info: returns a SearchInfo object
        labels: returns list of labels
        labels_normalized: returns list of normalized labels
"""

from .._constants import _PHOTOS_4_VERSION, SEARCH_CATEGORY_LABEL


@property
def search_info(self):
    """ returns SearchInfo object for photo 
        only valid on Photos 5, on older libraries, returns None
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return None

    # memoize SearchInfo object
    try:
        return self._search_info
    except AttributeError:
        self._search_info = SearchInfo(self)
        return self._search_info


@property
def labels(self):
    """ returns list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list 
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return []

    return self.search_info.labels


@property
def labels_normalized(self):
    """ returns normalized list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list 
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return []

    return self.search_info.labels_normalized


class SearchInfo:
    """ Info about search terms such as machine learning labels that Photos knows about a photo """

    def __init__(self, photo):
        """ photo: PhotoInfo object """

        if photo._db._db_version <= _PHOTOS_4_VERSION:
            raise NotImplementedError(
                f"search info not implemented for this database version"
            )

        self._photo = photo
        self.uuid = photo.uuid
        try:
            # get search info for this UUID
            # there might not be any search info data (e.g. if Photo was missing or photoanalysisd not run yet)
            self._db_searchinfo = photo._db._db_searchinfo_uuid[self.uuid]
        except KeyError:
            self._db_searchinfo = None

    @property
    def labels(self):
        """ return list of labels associated with Photo """
        if self._db_searchinfo:
            labels = [
                rec["content_string"]
                for rec in self._db_searchinfo
                if rec["category"] == SEARCH_CATEGORY_LABEL
            ]
        else:
            labels = []
        return labels

    @property
    def labels_normalized(self):
        """ return list of normalized labels associated with Photo """
        if self._db_searchinfo:
            labels = [
                rec["normalized_string"]
                for rec in self._db_searchinfo
                if rec["category"] == SEARCH_CATEGORY_LABEL
            ]
        else:
            labels = []
        return labels
