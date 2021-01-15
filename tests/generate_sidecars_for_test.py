""" Generate sidecars used for tests """

# Generates sidecars used for test cases
# tests generate sidecars and compare to the ones generated here to assert nothing changed
# Run this any time you change code that would result in a change to sidecar files

import pathlib

import osxphotos

PHOTOS_DB_15_7 = "./tests/Test-10.15.7.photoslibrary/database/photos.db"
PHOTOS_DB_14_6 = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

UUID_DICT_15_7 = {
    "not_favorite": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "has_adjustments": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "location": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_location": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "export": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
    "xmp": "F12384F6-CD17-4151-ACBA-AE0E3688539E",  # Pumkins1.jpg
}

UUID_DICT_14_6 = {
    "has_adjustments": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "no_adjustments": "15uNd7%8RguTEgNPKHfTWw",
    "location": "3Jn73XpSQQCluzRBMWRsMA",
    "xmp": "8SOE9s0XQVGsuq4ONohTng",
}

SIDECAR_DIR = "tests/sidecars"


def generate_sidecars(dbname, uuid_dict):
    """ generate XMP and JSON sidecars for testing """
    photosdb = osxphotos.PhotosDB(dbname)

    for _, uuid in uuid_dict.items():
        photo = photosdb.get_photo(uuid)

        # plain xmp
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}.xmp")
        xmp = photo._xmp_sidecar()
        with open(sidecar, "w") as file:
            file.write(xmp)

        # with extension
        ext = osxphotos.utils.get_preferred_uti_extension(photo.uti)
        ext = "jpg" if ext == "jpeg" else ext
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_ext.xmp")
        xmp = photo._xmp_sidecar(extension=ext)
        with open(sidecar, "w") as file:
            file.write(xmp)

        # persons_as_keywords
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_persons_as_keywords.xmp")
        xmp = photo._xmp_sidecar(use_persons_as_keywords=True, extension=ext)
        with open(sidecar, "w") as file:
            file.write(xmp)

        # albums_as_keywords
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_albums_as_keywords.xmp")
        xmp = photo._xmp_sidecar(use_albums_as_keywords=True, extension=ext)
        with open(sidecar, "w") as file:
            file.write(xmp)

        # keyword_template
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_keyword_template.xmp")
        xmp = photo._xmp_sidecar(
            keyword_template=["{created.year}", "{folder_album}"], extension=ext
        )
        with open(sidecar, "w") as file:
            file.write(xmp)

        # generate JSON files
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}.json")
        json_ = photo._exiftool_json_sidecar()
        with open(sidecar, "w") as file:
            file.write(json_)

        # no tag groups
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_no_tag_groups.json")
        json_ = photo._exiftool_json_sidecar(tag_groups=False)
        with open(sidecar, "w") as file:
            file.write(json_)

        # ignore_date_modified
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_ignore_date_modified.json")
        json_ = photo._exiftool_json_sidecar(ignore_date_modified=True)
        with open(sidecar, "w") as file:
            file.write(json_)

        # keyword_template
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_keyword_template.json")
        json_ = photo._exiftool_json_sidecar(keyword_template=["{folder_album}"])
        with open(sidecar, "w") as file:
            file.write(json_)

        # persons_as_keywords
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_persons_as_keywords.json")
        json_ = photo._exiftool_json_sidecar(use_persons_as_keywords=True)
        with open(sidecar, "w") as file:
            file.write(json_)

        # albums_as_keywords
        sidecar = str(pathlib.Path(SIDECAR_DIR) / f"{uuid}_albums_as_keywords.json")
        json_ = photo._exiftool_json_sidecar(use_albums_as_keywords=True)
        with open(sidecar, "w") as file:
            file.write(json_)


if __name__ == "__main__":
    generate_sidecars(PHOTOS_DB_15_7, UUID_DICT_15_7)
    generate_sidecars(PHOTOS_DB_14_6, UUID_DICT_14_6)
