""" PhotoInfo methods to expose comments and likes for shared photos """ 

@property
def comments(self):
    """ Returns list of Comment objects for any comments on the photo (sorted by date) """
    try:
        return self._db._db_comments_uuid[self.uuid]["comments"]
    except:
        return []

@property
def likes(self):
    """ Returns list of Like objects for any likes on the photo (sorted by date) """
    try:
        return self._db._db_comments_uuid[self.uuid]["likes"]
    except:
        return []