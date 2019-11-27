import pytest

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-10.15.1.photoslibrary/database/photos.db"
KEYWORDS = [
    "Kids",
    "wedding",
    "flowers",
    "England",
    "London",
    "London 2018",
    "St. James's Park",
    "UK",
    "United Kingdom",
]
# Photos 5 includes blank person for detected face
PERSONS = ["Katie", "Suzy", "Maria", ""]
ALBUMS = ["Pumpkin Farm"]
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 2,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1, "": 1}
ALBUM_DICT = {"Pumpkin Farm": 3}


def test_init():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.get_db_version() in osxphotos._TESTED_DB_VERSIONS


def test_os_version():
    import osxphotos

    (_, major, _) = osxphotos._get_os_version()
    assert major in osxphotos._TESTED_OS_VERSIONS


def test_persons():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "Katie" in photosdb.persons()
    assert collections.Counter(PERSONS) == collections.Counter(photosdb.persons())


def test_keywords():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "wedding" in photosdb.keywords()
    assert collections.Counter(KEYWORDS) == collections.Counter(photosdb.keywords())


def test_albums():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "Pumpkin Farm" in photosdb.albums()
    assert collections.Counter(ALBUMS) == collections.Counter(photosdb.albums())


def test_keywords_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    keywords = photosdb.keywords_as_dict()
    assert keywords["wedding"] == 2
    assert keywords == KEYWORDS_DICT


def test_persons_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    persons = photosdb.persons_as_dict()
    assert persons["Maria"] == 1
    assert persons == PERSONS_DICT


def test_albums_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums_as_dict()
    assert albums["Pumpkin Farm"] == 3
    assert albums == ALBUM_DICT


def test_attributes():
    import datetime
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["D79B8D77-BFFC-460B-9312-034F2877D35B"])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords() == ["Kids"]
    assert p.original_filename() == "Pumkins2.jpg"
    assert p.filename() == "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    assert p.date() == datetime.datetime(
        2018, 9, 28, 16, 7, 7, 0, datetime.timezone(datetime.timedelta(seconds=-14400))
    )
    assert p.description() == "Girl holding pumpkin"
    assert p.name() == "I found one!"
    assert p.albums() == ["Pumpkin Farm"]
    assert p.persons() == ["Katie"]
    assert p.path().endswith(
        "tests/Test-10.15.1.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    )
    assert p.ismissing() == False


def test_missing():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"])
    assert len(photos) == 1
    p = photos[0]
    assert p.path() == None
    assert p.ismissing() == True


def test_favorite():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite() == True


def test_not_favorite():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite() == False 


def test_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden() == True


def test_not_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden() == False


def test_count():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos()
    assert len(photos) == 7


def test_keyword_2():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(keywords=["wedding"])
    assert len(photos) == 2


def test_keyword_not_in_album():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid() == "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"


# def main():
#     photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
#     print(photosdb.keywords())
#     print(photosdb.persons())
#     print(photosdb.albums())

#     print(photosdb.keywords_as_dict())
#     print(photosdb.persons_as_dict())
#     print(photosdb.albums_as_dict())

# #      # find all photos with Keyword = Foo and containing John Smith
#     #  photos = photosdb.photos(keywords=["Foo"],persons=["John Smith"])
# #
#     #  # find all photos that include Alice Smith but do not contain the keyword Bar
#     #  photos = [p for p in photosdb.photos(persons=["Alice Smith"])
# #                  if p not in photosdb.photos(keywords=["Bar"]) ]
#     photos = photosdb.photos()
#     for p in photos:
#         print(
#             p.uuid(),
#             p.filename(),
#             p.date(),
#             p.description(),
#             p.name(),
#             p.keywords(),
#             p.albums(),
#             p.persons(),
#             p.path(),
#         )

# if __name__ == "__main__":
#     main()
