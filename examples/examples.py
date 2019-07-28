import osxphotos


def main():
    photosdb = osxphotos.PhotosDB()
    print(f"db file = {photosdb.get_photos_library_path()}")
    print(f"db version = {photosdb.get_db_version()}")

    print(photosdb.keywords())
    print(photosdb.persons())
    print(photosdb.albums())

    print(photosdb.keywords_as_dict())
    print(photosdb.persons_as_dict())
    print(photosdb.albums_as_dict())

    # find all photos with Keyword = Kids and containing person Katie
    photos = photosdb.photos(keywords=["Kids"], persons=["Katie"])
    print(f"found {len(photos)} photos")

    # find all photos that include Katie but do not contain the keyword wedding
    photos = [
        p
        for p in photosdb.photos(persons=["Katie"])
        if p not in photosdb.photos(keywords=["wedding"])
    ]

    # get all photos in the database
    photos = photosdb.photos()
    for p in photos:
        print(
            p.uuid(),
            p.filename(),
            p.date(),
            p.description(),
            p.name(),
            p.keywords(),
            p.albums(),
            p.persons(),
            p.path(),
            p.ismissing(),
            p.hasadjustments(),
        )


if __name__ == "__main__":
    main()
