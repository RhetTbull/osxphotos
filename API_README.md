# OSXPhotos Python API

In addition to a command line interface, OSXPhotos provides a access to a Python API that allows you to easily access a Photos library, often with just a few lines of code.

## Table of Contents

* [Example uses of the Python package](#example-uses-of-the-python-package)
* [Package Interface](#package-interface)
  * [PhotosDB](#photosdb)
  * [PhotoInfo](#photoinfo)
  * [ExifInfo](#exifinfo)
  * [AlbumInfo](#albuminfo)
  * [ImportInfo](#importinfo)
  * [ProjectInfo](#projectinfo)
  * [MomentInfo](#momentinfo)
  * [FolderInfo](#folderinfo)
  * [PlaceInfo](#placeinfo)
  * [ScoreInfo](#scoreinfo)
  * [SearchInfo](#searchinfo)
  * [PersonInfo](#personinfo)
  * [FaceInfo](#faceinfo)
  * [CommentInfo](#commentinfo)
  * [LikeInfo](#likeinfo)
  * [AdjustmentsInfo](#adjustmentsinfo)
  * [Raw Photos](#raw-photos)
  * [Template System](#template-system)
  * [ExifTool](#exiftoolExifTool)
  * [PhotoExporter](#photoexporter)
  * [Text Detection](#textdetection)
  * [Utility Functions](#utility-functions)
* [Additional Examples](#additional-examples)

## Example uses of the Python package

```python
""" Simple usage of the package """
import os.path

import osxphotos

def main():
    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    photosdb = osxphotos.PhotosDB(db)
    print(photosdb.keywords)
    print(photosdb.persons)
    print(photosdb.album_names)

    print(photosdb.keywords_as_dict)
    print(photosdb.persons_as_dict)
    print(photosdb.albums_as_dict)

    # find all photos with Keyword = Foo and containing John Smith
    photos = photosdb.photos(keywords=["Foo"],persons=["John Smith"])

    # find all photos that include Alice Smith but do not contain the keyword Bar
    photos = [p for p in photosdb.photos(persons=["Alice Smith"]) 
                if p not in photosdb.photos(keywords=["Bar"]) ]
    for p in photos:
        print(
            p.uuid,
            p.filename,
            p.original_filename,
            p.date,
            p.description,
            p.title,
            p.keywords,
            p.albums,
            p.persons,
            p.path,
        )

if __name__ == "__main__":
    main()
```

```python
""" Export all photos to specified directory using album names as folders
    If file has been edited, also export the edited version, 
    otherwise, export the original version 
    This will result in duplicate photos if photo is in more than album """

import os.path
import pathlib
import sys

import click
from pathvalidate import is_valid_filepath, sanitize_filepath

import osxphotos


@click.command()
@click.argument("export_path", type=click.Path(exists=True))
@click.option(
    "--default-album",
    help="Default folder for photos with no album. Defaults to 'unfiled'",
    default="unfiled",
)
@click.option(
    "--library-path",
    help="Path to Photos library, default to last used library",
    default=None,
)
def export(export_path, default_album, library_path):
    export_path = os.path.expanduser(export_path)
    library_path = os.path.expanduser(library_path) if library_path else None

    if library_path is not None:
        photosdb = osxphotos.PhotosDB(library_path)
    else:
        photosdb = osxphotos.PhotosDB()

    photos = photosdb.photos()

    for p in photos:
        if not p.ismissing:
            albums = p.albums
            if not albums:
                albums = [default_album]
            for album in albums:
                click.echo(f"exporting {p.filename} in album {album}")

                # make sure no invalid characters in destination path (could be in album name)
                album_name = sanitize_filepath(album, platform="auto")

                # create destination folder, if necessary, based on album name
                dest_dir = os.path.join(export_path, album_name)

                # verify path is a valid path
                if not is_valid_filepath(dest_dir, platform="auto"):
                    sys.exit(f"Invalid filepath {dest_dir}")

                # create destination dir if needed
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)

                # export the photo
                if p.hasadjustments:
                    # export edited version
                    exported = p.export(dest_dir, edited=True)
                    edited_name = pathlib.Path(p.path_edited).name
                    click.echo(f"Exported {edited_name} to {exported}")
                # export unedited version
                exported = p.export(dest_dir)
                click.echo(f"Exported {p.filename} to {exported}")
        else:
            click.echo(f"Skipping missing photo: {p.filename}")


if __name__ == "__main__":
    export()  # pylint: disable=no-value-for-parameter
```

## Package Interface

### PhotosDB

#### Read a Photos library database

```python
osxphotos.PhotosDB()
osxphotos.PhotosDB(path)
osxphotos.PhotosDB(dbfile=path)
```

Reads the Photos library database and returns a PhotosDB object.  

Pass the path to a Photos library or to a specific database file (e.g. "/Users/smith/Pictures/Photos Library.photoslibrary" or "/Users/smith/Pictures/Photos Library.photoslibrary/database/photos.db").  Normally, it's recommended you pass the path the .photoslibrary folder, not the actual database path.  **Note**: In Photos, users may specify a different library to open by holding down the *option* key while opening Photos.app. See also [get_last_library_path](#get_last_library_path) and [get_system_library_path](#get_system_library_path)

If an invalid path is passed, PhotosDB will raise `FileNotFoundError` exception.

**Note**: If neither path or dbfile is passed, PhotosDB will use get_last_library_path to open the last opened Photos library.  This usually works but is not 100% reliable.  It can also lead to loading a different library than expected if the user has held down *option* key when opening Photos to switch libraries.  You may therefore want to explicitely pass the path to `PhotosDB()`.

#### Open the default (last opened) Photos library

The default library is the library that would open if the user opened Photos.app.

```python
import osxphotos
photosdb = osxphotos.PhotosDB(osxphotos.utils.get_last_library_path())
```

#### Open System Photos library

In Photos 5 (Catalina / MacOS 10.15), you can use `get_system_library_path()` to get the path to the System photo library if you want to ensure PhotosDB opens the system library.  This does not work on older versions of MacOS. E.g.

```python
import osxphotos

path = osxphotos.get_system_library_path()
photosdb = osxphotos.PhotosDB(path)
```

also,

```python
import osxphotos

path = osxphotos.get_system_library_path()
photosdb = osxphotos.PhotosDB(dbfile=path)
```

#### Open a specific Photos library

```python
import osxphotos

photosdb = osxphotos.PhotosDB(dbfile="/Users/smith/Pictures/Test.photoslibrary/database/photos.db")
```

or

```python
import osxphotos

photosdb = osxphotos.PhotosDB("/Users/smith/Pictures/Test.photoslibrary")
```

Pass the fully qualified path to the Photos library or the actual database file inside the library. The database is called photos.db and resides in the database folder in your Photos library.  If you pass only the path to the library, PhotosDB will add the database path automatically.  The option to pass the actual database path is provided so database files can be queried even if separated from the actual .photoslibrary file.

Returns a PhotosDB object.

**Note**: If you have a large library (e.g. many thousdands of photos), creating the PhotosDB object can take a long time (10s of seconds).  See [Implementation Notes](#implementation-notes) for additional details.

#### `keywords`

```python
# assumes photosdb is a PhotosDB object (see above)
keywords = photosdb.keywords
```

Returns a list of the keywords found in the Photos library

#### <a name="photosdbalbuminfo">`album_info`</a>

```python
# assumes photosdb is a PhotosDB object (see above)
albums = photosdb.album_info
```

Returns a list of [AlbumInfo](#AlbumInfo) objects representing albums in the database or empty list if there are no albums.  See also [albums](#albums) and [burst_album_info](#burst_album_info).

#### `albums`

```python
# assumes photosdb is a PhotosDB object (see above)
album_names = photosdb.albums
```

Returns a list of the album names found in the Photos library. See also [burst_albums](#burst_albums).

**Note**: In Photos 5.0 (MacOS 10.15/Catalina), It is possible to have more than one album with the same name in Photos.  Albums with duplicate names are treated as a single album and the photos in each are combined.  For example, if you have two albums named "Wedding" and each has 2 photos, osxphotos will treat this as a single album named "Wedding" with 4 photos in it.

See also [album_info](#album_info.)

#### `albums_shared`

Returns list of shared album names found in photos database (e.g. albums shared via iCloud photo sharing)

**Note**: *Only valid for Photos 5 / MacOS 10.15*; on Photos <= 4, prints warning and returns empty list.

#### `import_info`

Returns a list of [ImportInfo](#importinfo) objects representing the import sessions for the database.

#### `project_info`

Returns a list of [ProjectInfo](#projectinfo) objects representing the projects/creations (cards, calendars, etc.) in the database.

#### `moment_info`

Returns the  [MomentInfo](#momentinfo) object for the photo or `None` if the photo does not have an associated moment.

#### `folder_info`

```python
# assumes photosdb is a PhotosDB object (see above)
folders = photosdb.folder_info
```

Returns a list of [FolderInfo](#FolderInfo) objects representing top level folders in the database or empty list if there are no folders.  See also [folders](#folders).

**Note**: Currently folder_info is only implemented for Photos 5 (Catalina); will return empty list and output warning if called on earlier database versions.

#### `folders`

```python
# assumes photosdb is a PhotosDB object (see above)
folders = photosdb.folders
```

Returns a list names of top level folder names in the database.

**Note**: Currently folders is only implemented for Photos 5 (Catalina); will return empty list and output warning if called on earlier database versions.

#### `persons`

```python
# assumes photosdb is a PhotosDB object (see above)
persons = photosdb.persons
```

Returns a list of the person names (faces) found in the Photos library.  **Note**: It is of course possible to have more than one person with the same name, e.g. "Maria Smith", in the database.  `persons` assumes these are the same person and will list only one person named "Maria Smith".  If you need more information about persons in the database, see [person_info](#dbpersoninfo).

#### <a name="dbpersoninfo">`person_info`</a>

```python
# assumes photosdb is a PhotosDB object (see above)
person_info = photosdb.person_info
```

Returns a list of [PersonInfo](#personinfo) objects representing persons who appear in photos in the database.

#### `keywords_as_dict`

```python
# assumes photosdb is a PhotosDB object (see above)
keyword_dict = photosdb.keywords_as_dict
```

Returns a dictionary of keywords found in the Photos library where key is the keyword and value is the count of how many times that keyword appears in the library (ie. how many photos are tagged with the keyword).  Resulting dictionary is in reverse sorted order (e.g. keyword with the highest count is first).

#### `persons_as_dict`

```python
# assumes photosdb is a PhotosDB object (see above)
persons_dict = photosdb.persons_as_dict
```

Returns a dictionary of persons (faces) found in the Photos library where key is the person name and value is the count of how many times that person appears in the library (ie. how many photos are tagged with the person).  Resulting dictionary is in reverse sorted order (e.g. person who appears in the most photos is listed first). **Note**: It is of course possible to have more than one person with the same name, e.g. "Maria Smith", in the database.  `persons_as_dict` assumes these are the same person and will list only one person named "Maria Smith".  If you need more information about persons in the database, see [person_info](#dbpersoninfo).

#### `albums_as_dict`

```python
# assumes photosdb is a PhotosDB object (see above)
albums_dict = photosdb.albums_as_dict
```

Returns a dictionary of albums found in the Photos library where key is the album name and value is the count of how many photos are in the album.  Resulting dictionary is in reverse sorted order (e.g. album with the most photos is listed first).  

**Note**: In Photos 5.0 (MacOS 10.15/Catalina), It is possible to have more than one album with the same name in Photos.  Albums with duplicate names are treated as a single album and the photos in each are combined.  For example, if you have two albums named "Wedding" and each has 2 photos, osxphotos will treat this as a single album named "Wedding" with 4 photos in it.

#### `albums_shared_as_dict`

```python
# assumes photosdb is a PhotosDB object (see above)
albums_shared_dict = photosdb.albums_shared_as_dict
```

Returns a dictionary of shared albums (e.g. shared via iCloud photo sharing) found in the Photos library where key is the album name and value is the count of how many photos are in the album.  Resulting dictionary is in reverse sorted order (e.g. album with the most photos is listed first).

**Note**: *Photos 5 / MacOS 10.15 only*.  On earlier versions of Photos, prints warning and returns empty dictionary.

#### `labels`

Returns image categorization labels associated with photos in the library as list of str.

**Note**: Only valid on Photos 5; on earlier versions, returns empty list. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels_normalized](#labels_normalized).  

#### `labels_normalized`

Returns image categorization labels associated with photos in the library as list of str. Labels are normalized (e.g. converted to lower case).  Use of normalized strings makes it easier to search if you don't how Apple capitalizes a label.

**Note**: Only valid on Photos 5; on earlier versions, returns empty list. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels](#labels).  

#### `labels_as_dict`

Returns dictionary image categorization labels associated with photos in the library where key is label and value is number of photos in the library with the label.

**Note**: Only valid on Photos 5; on earlier versions, logs warning and returns empty dict. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels_normalized_as_dict](#labels_normalized_as_dict).  

#### `labels_normalized_as_dict`

Returns dictionary of image categorization labels associated with photos in the library where key is normalized label and value is number of photos in the library with that label. Labels are normalized (e.g. converted to lower case).  Use of normalized strings makes it easier to search if you don't how Apple capitalizes a label.

**Note**: Only valid on Photos 5; on earlier versions, logs warning and returns empty dict. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels_as_dict](#labels_as_dict).  

#### `library_path`

```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.library_path
```

Returns the path to the Photos library as a string

#### `db_path`

```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.db_path
```

Returns the path to the Photos database PhotosDB was initialized with

#### `db_version`

```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.db_version
```

Returns the version number for Photos library database.  You likely won't need this but it's provided in case needed for debugging. PhotosDB will print a warning to `sys.stderr` if you open a database version that has not been tested.

#### `get_db_connection()`

Returns tuple of (connection, cursor) for the working copy of the Photos database.  This is useful for debugging or prototyping new features.

```python
photosdb = osxphotos.PhotosDB()
conn, cursor = photosdb.get_db_connection()

results = conn.execute(
        "SELECT ZUUID FROM ZGENERICASSET WHERE ZFAVORITE = 1;"
).fetchall()

for row in results:
    # do something
    pass

conn.close()
```

#### <A name="photos">`photos(keywords=None, uuid=None, persons=None, albums=None, images=True, movies=True, from_date=None, to_date=None, intrash=False)`</a>

```python
# assumes photosdb is a PhotosDB object (see above)
photos = photosdb.photos([keywords=['keyword',]], [uuid=['uuid',]], [persons=['person',]], [albums=['album',]],[from_date=datetime.datetime],[to_date=datetime.datetime])
```

Returns a list of [PhotoInfo](#PhotoInfo) objects.  Each PhotoInfo object represents a photo in the Photos Libary.

If called with no parameters, returns a list of every photo in the Photos library.

May be called with one or more of the following parameters:

```python
photos = photosdb.photos(
    keywords = [],
    uuid = [],
    persons = [],
    albums = [],
    images = bool,
    movies = bool,
    from_date = datetime.datetime,
    to_date = datetime.datetime,
    intrash = bool,
)
```

* ```keywords```: list of one or more keywords.  Returns only photos containing the keyword(s).  If more than one keyword is provided finds photos matching any of the keywords (e.g. treated as "or")
* ```uuid```: list of one or more uuids.  Returns only photos whos UUID matches.  **Note**: The UUID is the universally unique identifier that the Photos database uses to identify each photo.  You shouldn't normally need to use this but it is a way to access a specific photo if you know the UUID.  If more than more uuid is provided, returns photos that match any of the uuids (e.g. treated as "or")
* ```persons```: list of one or more persons. Returns only photos containing the person(s).  If more than one person provided, returns photos that match any of the persons (e.g. treated as "or")
* ```albums```: list of one or more album names.  Returns only photos contained in the album(s). If more than one album name is provided, returns photos contained in any of the albums (.e.g. treated as "or")
* ```images```: bool; if True, returns photos/images; default is True
* ```movies```: bool; if True, returns movies/videos; default is True
* ```from_date```: datetime.datetime; if provided, finds photos where creation date >= from_date; default is None
* ```to_date```: datetime.datetime; if provided, finds photos where creation date <= to_date; default is None
* ```intrash```: if True, finds only photos in the "Recently Deleted" or trash folder, if False does not find any photos in the trash; default is False

See also [get_photo()](#getphoto) which is much faster for retrieving a single photo.

If more than one of (keywords, uuid, persons, albums,from_date, to_date) is provided, they are treated as "and" criteria. E.g.

Finds all photos with (keyword = "wedding" or "birthday") and (persons = "Juan Rodriguez")

```python
photos=photosdb.photos(keywords=["wedding","birthday"],persons=["Juan Rodriguez"])
```

Find all photos tagged with keyword "wedding":

```python
# assumes photosdb is a PhotosDB object (see above)
photos = photosdb.photos(keywords=["wedding"])
 ```

Find all photos of Maria Smith

```python
# assumes photosdb is a PhotosDB object (see above)
photos=photosdb.photos(persons=["Maria Smith"])
```

Find all photos in album "Summer Vacation" or album "Ski Trip"

```python
# assumes photosdb is a PhotosDB object (see above)
photos=photosdb.photos(albums=["Summer Vacation", "Ski Trip"])
```

Find the single photo with uuid = "osMNIO5sQFGZTbj9WrydRB"

```python
# assumes photosdb is a PhotosDB object (see above)
photos=photosdb.photos(uuid=["osMNIO5sQFGZTbj9WrydRB"])
```

If you need to do more complicated searches, you can do this programmaticaly.  For example, find photos with keyword = "Kids" but not in album "Vacation 2019"

```python
# assumes photosdb is a PhotosDB object (see above)
photos1 = photosdb.photos(albums=["Vacation 2019"])
photos2 = photosdb.photos(keywords=["Kids"])
photos3 = [p for p in photos2 if p not in photos1]
```

To get only movies:

```python
movies = photosdb.photos(images=False, movies=True)
```

**Note** PhotosDB.photos() may return a different number of photos than Photos.app reports in the GUI. This is because photos() returns [hidden](#hidden) photos, [shared](#shared) photos, and for [burst](#burst) photos, all selected burst images even if non-selected burst images have not been deleted. Photos only reports 1 single photo for each set of burst images until you "finalize" the burst by selecting key photos and deleting the others using the "Make a selection" option.

For example, in my library, Photos says I have 19,386 photos and 474 movies.  However, PhotosDB.photos() reports 25,002 photos.  The difference is due to 5,609 shared photos and 7 hidden photos.  (*Note* Shared photos only valid for Photos 5).  Similarly, filtering for just movies returns 625 results.  The difference between 625 and 474 reported by Photos is due to 151 shared movies.

```pycon
>>> import osxphotos
>>> photosdb = osxphotos.PhotosDB("/Users/smith/Pictures/Photos Library.photoslibrary")
>>> photos = photosdb.photos()
>>> len(photos)
25002
>>> shared = [p for p in photos if p.shared]
>>> len(shared)
5609
>>> not_shared = [p for p in photos if not p.shared]
>>> len(not_shared)
19393
>>> hidden = [p for p in photos if p.hidden]
>>> len(hidden)
7
>>> movies = photosdb.photos(movies=True, images=False)
>>> len(movies)
625
>>> shared_movies = [m for m in movies if m.shared]
>>> len(shared_movies)
151
>>>
```

#### <a name="getphoto">`get_photo(uuid)`</A>

Returns a single PhotoInfo instance for photo with UUID matching `uuid` or None if no photo is found matching `uuid`.  If you know the UUID of a photo, `get_photo()` is much faster than `photos`.  See also [photos()](#photos).

#### `execute(sql)`

Execute sql statement against the Photos database and return a sqlite cursor with the results.

### PhotoInfo

PhotosDB.photos() returns a list of PhotoInfo objects.  Each PhotoInfo object represents a single photo in the Photos library.

#### `uuid`

Returns the universally unique identifier (uuid) of the photo.  This is how Photos keeps track of individual photos within the database.

#### `filename`

Returns the current filename of the photo on disk.  See also [original_filename](#original_filename)

#### `original_filename`

Returns the original filename of the photo when it was imported to Photos.  **Note**: Photos 5.0+ renames the photo when it adds the file to the library using UUID.  See also [filename](#filename)

#### `date`

Returns the create date of the photo as a datetime.datetime object

#### `date_added`

Returns the date the photo was added to the Photos library as a timezone aware datetime.datetime object, or None if the data added cannot be determined

#### `date_modified`

Returns the modification date of the photo as a datetime.datetime object or None if photo has no modification date

#### `description`

Returns the description of the photo

#### `title`

Returns the title of the photo

#### `keywords`

Returns a list of keywords (e.g. tags) applied to the photo

#### `albums`

Returns a list of albums the photo is contained in. See also [album_info](#album_info).

#### `album_info`

Returns a list of [AlbumInfo](#AlbumInfo) objects representing the albums the photo is contained in or empty list of the photo is not in any albums.  See also [albums](#albums).

#### `import_info`

Returns an [ImportInfo](#importinfo) object representing the import session associated with the photo or `None` if there is no associated import session.

#### `project_info`

Returns a list of [ProjectInfo](#projectinfo) objects representing projects/creations (cards, calendars, etc.) the photo is contained in or empty list if there are no projects associated with the photo.

#### `persons`

Returns a list of the names of the persons in the photo

#### <a name="photopersoninfo">`person_info`</a>

Returns a list of [PersonInfo](#personinfo) objects representing persons in the photo.  Each PersonInfo object is associated with one or more FaceInfo objects.

#### <a name="photofaceinfo">`face_info`</a>

Returns a list of [FaceInfo](#faceinfo) objects representing faces in the photo.  Each face is associated with the a PersonInfo object.

#### `path`

Returns the absolute path to the photo on disk as a string.  **Note**: this returns the path to the *original* unedited file (see [hasadjustments](#hasadjustments)).  If the file is missing on disk, path=`None` (see [ismissing](#ismissing)).

#### `path_edited`

Returns the absolute path to the edited photo on disk as a string.  If the photo has not been edited, returns `None`.  See also [path](#path) and [hasadjustments](#hasadjustments).  

**Note**: will also return None if the edited photo is missing on disk.

#### `path_derivatives`

Returns list of paths to any derivative preview images associated with the photo. The list of returned paths is sorted in descending order by size (the largest, presumably highest quality) preview image will be the first element in the returned list. These will be named something like this on Photos 5+:

* `F19E06B8-A712-4B5C-907A-C007D37BDA16_1_101_o.jpeg`
* `F19E06B8-A712-4B5C-907A-C007D37BDA16_1_102_o.jpeg`
* `F19E06B8-A712-4B5C-907A-C007D37BDA16_1_105_c.jpeg`

On Photos <=4, they'll be named something like:

* `UNADJUSTEDNONRAW_mini_6.jpg`
* `UNADJUSTEDNONRAW_thumb_6.jpg`
* `Y6OofYkbR96spbS6XgwOQw_mini_1.jpg`

I've not yet decoded the suffixes to know which preview is used for which purpose but in general, if you look for the largest file, you'll get the highest resolution preview. Note that video files and Live images may have both a `.mov` video preview as well as a `.jpeg` still-image preview (the JPEG file is the one Photos displays as the "cover" for the video.)

Returns empty list if no preview images are found.

#### `path_raw`

Returns the absolute path to the associated raw photo on disk as a string, if photo is part of a RAW+JPEG pair, otherwise returns None.  See [notes on Raw Photos](#raw-photos).

#### `has_raw`

Returns True if photo has an associated raw image, otherwise False. (e.g. Photo is a RAW+JPEG pair). See also [is_raw](#israw) and [notes on Raw Photos](#raw-photos).

#### `israw`

Returns True if photo is a raw image. E.g. it was imported as a single raw image, not part of a RAW+JPEG pair.  See also [has_raw](#has_raw) and .

#### `raw_original`

Returns True if associated raw image and the raw image is selected in Photos via "Use RAW as Original", otherwise returns False.  See [notes on Raw Photos](#raw-photos).

#### `height`

Returns height of the photo in pixels.  If image has been edited, returns height of the edited image, otherwise returns height of the original image.  See also [original_height](#original_height).

#### `width`

Returns width of the photo in pixels.  If image has been edited, returns width of the edited image, otherwise returns width of the original image.  See also [original_width](#original_width).

#### `orientation`

Returns EXIF orientation value of the photo as integer.  If image has been edited, returns orientation of the edited image, otherwise returns orientation of the original image. See also [original_orientation](#original_orientation).  If orientation cannot be determined, returns 0 (this happens if osxphotos cannot decode the adjustment info for an edited image).

#### `original_height`

Returns height of the original photo in pixels. See also [height](#height).

#### `original_width`

Returns width of the original photo in pixels. See also [width](#width).

#### `original_orientation`

Returns EXIF orientation value of the original photo as integer. See also [orientation](#orientation).

#### `original_filesize`

Returns size of the original photo in bytes as integer.

#### `ismissing`

Returns `True` if the original image file is missing on disk, otherwise `False`.  This can occur if the file has been uploaded to iCloud but not yet downloaded to the local library or if the file was deleted or imported from a disk that has been unmounted and user hasn't enabled "Copy items to the Photos library" in Photos preferences. **Note**: this status is computed based on data in the Photos library and `ismissing` does not verify if the photo is actually missing. See also [path](#path).

#### `hasadjustments`

Returns `True` if the picture has been edited, otherwise `False`

#### `adjustments`

On Photos 5+, returns an [AdjustmentsInfo](#adjustmentsinfo) object representing the adjustments (edits) to the photo or None if there are no adjustments.  On earlier versions of Photos, always returns None.

#### `external_edit`

Returns `True` if the picture was edited in an external editor (outside Photos.app), otherwise `False`

#### `favorite`

Returns `True` if the picture has been marked as a favorite, otherwise `False`

#### `hidden`

Returns `True` if the picture has been marked as hidden, otherwise `False`

#### `visible`

Returns `True` if the picture is visible in library, otherwise `False`.  e.g. non-selected burst photos are not hidden but also not visible

#### `intrash`

Returns `True` if the picture is in the trash ('Recently Deleted' folder), otherwise `False`

#### `date_trashed`

Returns the date the photo was placed in the trash as a datetime.datetime object or None if photo is not in the trash

#### `location`

Returns latitude and longitude as a tuple of floats (latitude, longitude).  If location is not set, latitude and longitude are returned as `None`

#### `place`

Returns a [PlaceInfo](#PlaceInfo) object with reverse geolocation data or None if there is the photo has no reverse geolocation information.

#### `shared`

Returns True if photo is in a shared album, otherwise False.

**Note**: *Only valid on Photos 5 / MacOS 10.15+; on Photos <= 4, returns None.

#### `owner`

Returns full name of the photo owner (person who shared the photo) for shared photos or None if photo is not shared. Also returns None if you are the person who shared the photo.

**Note**: *Only valid on Photos 5 / MacOS 10.15+; on Photos <= 4, returns None.

#### `comments`

Returns list of [CommentInfo](#commentinfo) objects for comments on shared photos or empty list if no comments.

**Note**: *Only valid on Photos 5 / MacOS 10.15+; on Photos <= 4, returns empty list.

#### `likes`

Returns list of [LikeInfo](#likeinfo) objects for likes on shared photos or empty list if no likes.

**Note**: *Only valid on Photos 5 / MacOS 10.15+; on Photos <= 4, returns empty list.

#### `isreference`

Returns `True` if the original image file is a referenced file (imported without copying to the Photos library) otherwise returns `False`.

#### `isphoto`

Returns True if type is photo/still image, otherwise False

#### `ismovie`

Returns True if type is movie/video, otherwise False

#### `iscloudasset`

Returns True if photo is a cloud asset, that is, it is in a library synched to iCloud.  See also [incloud](#incloud)

#### `incloud`

Returns True if photo is a [cloud asset](#iscloudasset) and is synched to iCloud otherwise False if photo is a cloud asset and not yet synched to iCloud. Returns None if photo is not a cloud asset.

**Note**: Applies to master (original) photo only.  It's possible for the master to be in iCloud but a local edited version is not yet synched to iCloud. `incloud` provides status of only the master photo.  osxphotos does not yet provide a means to determine if the edited version is in iCloud.  If you need this feature, please open an [issue](https://github.com/RhetTbull/osxphotos/issues).

#### `uti`

Returns Uniform Type Identifier (UTI) for the current version of the image, for example: 'public.jpeg' or 'com.apple. quicktime-movie'.  If the image has been edited, `uti` will return the UTI for the edited image, otherwise it will return the UTI for the original image.

#### `uti_original`

Returns Uniform Type Identifier (UTI) for the original unedited image, for example: 'public.jpeg' or 'com.apple.quicktime-movie'.

#### `uti_edited`

Returns Uniform Type Identifier (UTI) for the edited image, for example: 'public.jpeg'.  Returns None if the photo does not have adjustments.

#### `uti_raw`

Returns Uniform Type Identifier (UTI) for the associated raw image, if there is one; for example, 'com.canon.cr2-raw-image'.  If the image is raw but not part of a RAW+JPEG pair, `uti_raw` returns None.  In this case, use `uti`, or `uti_original`.  See also [has_raw](#has_raw) and [notes on Raw Photos](#raw-photos).

#### `burst`

Returns True if photos is a burst image (e.g. part of a set of burst images), otherwise False.
See [burst_photos](#burst_photos)

#### `burst_selected`

Returns True if photo is a burst photo and has been selected from the burst set by the user, otherwise False.

#### `burst_key`

Returns True if photo is a burst photo and is the key image for the burst set (the image that Photos shows on top of the burst stack), otherwise False.

#### `burst_default_pick`

Returns True if photo is a burst image and is the photo that Photos selected as the default image for the burst set, otherwise False.

#### `burst_photos`

If photo is a burst image (see [burst](#burst)), returns a list of PhotoInfo objects for all other photos in the same burst set. If not a burst image, returns empty list.

Example below gets list of all photos that are bursts, selects one of of them and prints out the names of the other images in the burst set.  PhotosDB.photos() will only return the photos in the burst set that the user [selected](https://support.apple.com/guide/photos/view-photo-bursts-phtde06a275d/mac) using "Make a Selection..." in Photos or the key image Photos selected if the user has not yet made a selection.  This is similar to how Photos displays and counts burst photos.  Using `burst_photos` you can access the other images in the burst set to export them, etc.

```pycon
>>> import osxphotos
>>> photosdb = osxphotos.PhotosDB("/Users/smith/Pictures/Photos Library.photoslibrary")
>>> bursts = [p for p in photosdb.photos() if p.burst]
>>> burst_photo = bursts[5]
>>> len(burst_photo.burst_photos)
4
>>> burst_photo.original_filename
'IMG_9851.JPG'
>>> for photo in burst_photo.burst_photos:
...     print(photo.original_filename)
...
IMG_9853.JPG
IMG_9852.JPG
IMG_9854.JPG
IMG_9855.JPG
```

#### `burst_albums`

If photo is burst photo, returns list of albums it is contained in as well as any albums the key photo is contained in, otherwise returns `PhotoInfo.albums`.  

If a burst photo which has unselected burst images (e.g. the burst images are in the library but haven't been selected by the user using the "Make a selection" feature) is placed in a an album, Photos treats only the selected "key" photo as in the album.  The unselected burst images, while associated with the photo in the album, are not technically in the album.  If you are handling one of these unselected burst photos and want to know which album it would be in based on which albums it's selected key images are in, use `burst_albums`. See also [burst_album_info](#burst_album_info) and [albums](#albums).

#### `burst_album_info`

If photo is non-selected burst photo, teturns a list of [AlbumInfo](#AlbumInfo) objects representing the albums any other photos in the same burst set are contained in.  Otherwise, returns `PhotoInfo.album_info`. See also [burst_albums](#burst_albums) and [album_info](#album_info).

#### `live_photo`

Returns True if photo is an Apple live photo (ie. it has an associated "live" video component), otherwise returns False.  See [path_live_photo](#path_live_photo).

#### `path_live_photo`

Returns the path to the live video component of a [live photo](#live_photo). If photo is not a live photo, returns None.

**Note**: will also return None if the live video component is missing on disk. It's possible that the original photo may be on disk ([ismissing](#ismissing)==False) but the video component is missing, likely because it has not been downloaded from iCloud.

#### `path_edited_live_photo`

Returns the path to the edited live video component of an edited [live photo](#live_photo). If photo is not a live photo or not edited, returns None.

#### `portrait`

Returns True if photo was taken in iPhone portrait mode, otherwise False.

#### `hdr`

Returns True if photo was taken in High Dynamic Range (HDR) mode, otherwise False.

#### `selfie`

Returns True if photo is a selfie (taken with front-facing camera), otherwise False.  

**Note**: Only implemented for Photos version 3.0+.  On Photos version < 3.0, returns None.

#### `time_lapse`

Returns True if photo is a time lapse video, otherwise False.

#### `panorama`

Returns True if photo is a panorama, otherwise False.

**Note**: The result of `PhotoInfo.panorama` will differ from the "Panoramas" Media Types smart album in that it will also identify panorama photos from older phones that Photos does not recognize as panoramas.

#### `slow_mo`

Returns True if photo is a slow motion video, otherwise False

#### `labels`

Returns image categorization labels associated with the photo as list of str.

**Note**: Only valid on Photos 5; on earlier versions, returns empty list. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels_normalized](#labels_normalized).  

#### `labels_normalized`

Returns image categorization labels associated with the photo as list of str. Labels are normalized (e.g. converted to lower case).  Use of normalized strings makes it easier to search if you don't how Apple capitalizes a label. For example:

```python
import osxphotos

photosdb = osxphotos.PhotosDB()
for photo in photosdb.photos():
    if "statue" in photo.labels_normalized:
        print(f"I found a statue! {photo.original_filename}")
```

**Note**: Only valid on Photos 5+; on earlier versions, returns empty list. In Photos 5+, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels](#labels).  

#### <a name="photosearchinfo">`search_info`</a>

Returns [SearchInfo](#searchinfo) object that represents search metadata for the photo.  

**Note**: Only valid on Photos 5+; on ealier versions, returns None.

#### <a name="photosearchinfo-normalized">`search_info_normalized`</a>

Returns [SearchInfo](#searchinfo) object that represents normalized search metadata for the photo.  This returns a SearchInfo object just as `search_info` but all the properties of the object return normalized text (converted to lowercase).

**Note**: Only valid on Photos 5+; on ealier versions, returns None.

#### `exif_info`

Returns an [ExifInfo](#exifinfo) object with EXIF details from the Photos database.  See [ExifInfo](#exifinfo) for additional details.

**Note**: Only valid on Photos 5+; on earlier versions, returns `None`.  The EXIF details returned are a subset of the actual EXIF data in a typical image.  At import Photos stores this subset in the database and it's this stored data that `exif_info` returns.

See also `exiftool`.

#### `exiftool`

Returns an [ExifToolCaching](#exiftoolExifTool) object for the photo which provides an interface to [exiftool](https://exiftool.org/) allowing you to read the actual EXIF data in the image file inside the Photos library.  If [exif_info](#exif-info) doesn't give you all the data you need, you can use `exiftool` to read the entire EXIF contents of the image.

If the file is missing from the library (e.g. not downloaded from iCloud), returns None.

exiftool must be installed in the path for this to work.  If exiftool cannot be found in the path, calling `exiftool` will log a warning and return `None`.  You can check the exiftool path using `osxphotos.exiftool.get_exiftool_path` which will raise FileNotFoundError if exiftool cannot be found.

```pycon
>>> import osxphotos
>>> osxphotos.exiftool.get_exiftool_path()
'/usr/local/bin/exiftool'
>>>
```

`ExifToolCaching` provides the following methods:

* `asdict(tag_groups=True)`: returns all EXIF metadata found in the file as a dictionary in following form (Note: this shows just a subset of available metadata).  See [exiftool](https://exiftool.org/) documentation to understand which metadata keys are available. If `tag_groups` is True (default) dict keys are in form "GROUP:TAG", e.g. "IPTC:Keywords". If `tag_groups` is False, dict keys do not have group names, e.g. "Keywords".

```python
{'Composite:Aperture': 2.2,
 'Composite:GPSPosition': '-34.9188916666667 138.596861111111',
 'Composite:ImageSize': '2754 2754',
 'EXIF:CreateDate': '2017:06:20 17:18:56',
 'EXIF:LensMake': 'Apple',
 'EXIF:LensModel': 'iPhone 6s back camera 4.15mm f/2.2',
 'EXIF:Make': 'Apple',
 'XMP:Title': 'Elder Park',
}
```

* `json()`: returns same information as `asdict()` but as a serialized JSON string.

The `ExifToolCaching` class caches values read from the photo via `exiftool` and is read-only.  This speeds access to the underlying EXIF data but any changes made to the EXIF data in the image will not be reflected in subsequent calls to `exiftool`.  In practice, the images in the Photos Library should not be modified after import so this is unlikely to cause any issues.

**Caution**: I caution against writing new EXIF data to photos in the Photos library because this will overwrite the original copy of the photo and could adversely affect how Photos behaves.  `exiftool.asdict()` is useful for getting access to all the photos information but if you want to write new EXIF data, I recommend you export the photo first then write the data.  [PhotoInfo.export()](#export) does this if called with `exiftool=True`.

#### `score`

Returns a [ScoreInfo](#scoreinfo) data class object which provides access to the computed aesthetic scores for each photo.

**Note**: Valid only for Photos 5; returns None for earlier Photos versions.

#### `duplicates`

Returns list of PhotoInfo objects for *possible* duplicates or empty list if no matching duplicates.  Photos are considered possible duplicates if the photo's original file size, date created, height, and width match another those of another photo.  This does not do a byte-for-byte comparison or compute a hash which makes it fast and allows for identification of possible duplicates even if originals are not downloaded from iCloud.  The signature-based approach should be robust enough to match duplicates created either through the "duplicate photo" menu item or imported twice into the library but you should not rely on this 100% for identification of all duplicates.

#### `hexdigest`

Returns a unique digest of the photo's properties and metadata; useful for detecting changes in any property/metadata of the photo.

#### `json()`

Returns a JSON representation of all photo info.

#### `asdict()`

Returns a dictionary representation of all photo info.

#### `export()`

`export(dest, filename=None, edited=False, live_photo=False, export_as_hardlink=False, overwrite=False, increment=True, sidecar_json=False, sidecar_exiftool=False, sidecar_xmp=False, download_missing=False, use_photos_export=False, use_photokit=True, timeout=120, exiftool=False, use_albums_as_keywords=False, use_persons_as_keywords=False)`

Export photo from the Photos library to another destination on disk.  

* dest: must be valid destination path as str (or exception raised).
* filename (optional): name of picture as str; if not provided, will use current filename.  **NOTE**: if provided, user must ensure file extension (suffix) is correct. For example, if photo is .CR2 file, edited image may be .jpeg.  If you provide an extension different than what the actual file is, export will print a warning but will happily export the photo using the incorrect file extension.  e.g. to get the extension of the edited photo, look at [PhotoInfo.path_edited](#path_edited).
* edited: bool; if True (default=False), will export the edited version of the photo (or raise exception if no edited version)
* export_as_hardlink: bool; if True (default=False), will hardlink files instead of copying them
* overwrite: bool; if True (default=False), will overwrite files if they alreay exist
* live_photo: bool; if True (default=False), will also export the associted .mov for live photos; exported live photo will be named filename.mov
* increment: bool; if True (default=True), will increment file name until a non-existent name is found
* sidecar_json: (bool, default = False); if True will also write a json sidecar with metadata in format readable by exiftool; sidecar filename will be dest/filename.json where filename is the stem of the photo name
* sidecar_json: (bool, default = False); if True will also write a json sidecar with metadata in format readable by exiftool; sidecar filename will be dest/filename.json where filename is the stem of the photo name; resulting json file will include tag group names (e.g. `exiftool -G -j`)
* sidecar_exiftool: (bool, default = False); if True will also write a json sidecar with metadata in format readable by exiftool; sidecar filename will be dest/filename.json where filename is the stem of the photo name; resulting json file will not include tag group names (e.g. `exiftool -j`)
* sidecar_xmp: (bool, default = False); if True will also write a XMP sidecar with metadata; sidecar filename will be dest/filename.xmp where filename is the stem of the photo name
* use_photos_export: (bool, default=False); if True will attempt to export photo via AppleScript or PhotoKit interaction with Photos
* download_missing: (bool, default=False); if True will attempt to export photo via AppleScript or PhotoKit interaction with Photos if missing
* use_photokit: (bool, default=True); if True will attempt to export photo via photokit instead of AppleScript when used with use_photos_export or download_missing
* timeout: (int, default=120) timeout in seconds used with use_photos_export
* exiftool: (bool, default = False) if True, will use [exiftool](https://exiftool.org/) to write metadata directly to the exported photo; exiftool must be installed and in the system path
* use_albums_as_keywords: (bool, default = False); if True, will use album names as keywords when exporting metadata with exiftool or sidecar
* use_persons_as_keywords: (bool, default = False); if True, will use person names as keywords when exporting metadata with exiftool or sidecar

Returns: list of paths to exported files. More than one file could be exported, for example if live_photo=True, both the original image and the associated .mov file will be exported

The json sidecar file can be used by exiftool to apply the metadata from the json file to the image.  For example:

```python
import osxphotos

photosdb = osxphotos.PhotosDB("/Users/smith/Pictures/Photos Library.photoslibrary")
photos = photosdb.photos()
photos[0].export("/tmp","photo_name.jpg",sidecar_json=True)
```

Then

`exiftool -j=photo_name.json photo_name.jpg`

If overwrite=False and increment=False, export will fail if destination file already exists

#### <a name="rendertemplate">`render_template(template_str, options=None)`</a>

Render template string for photo.  none_str is used if template substitution results in None value and no default specified.

* `template_str`: str in metadata template language (MTL) format. See also [Template System](#template-system) table. See notes below regarding specific details of the syntax.
* `options`: an optional osxphotos.phototemplate.RenderOptions object specifying the options to pass to the rendering engine.

`RenderOptions` has the following properties:

* template: str template
* none_str: str to use default for None values, default is '_'
* path_sep: optional string to use as path separator, default is os.path.sep
* expand_inplace: expand multi-valued substitutions in-place as a single string instead of returning individual strings
* inplace_sep: optional string to use as separator between multi-valued keywords with expand_inplace; default is ','
* filename: if True, template output will be sanitized to produce valid file name
* dirname: if True, template output will be sanitized to produce valid directory name
* strip: if True, strips leading/trailing whitespace from rendered templates
* edited_version: set to True if you want {edited_version} to resolve to True (e.g. exporting edited version of photo)
* export_dir: set to the export directory if you want to evalute {export_dir} template
* filepath: set to value for filepath of the exported photo if you want to evaluate {filepath} template
* quote: quote path templates for execution in the shell

Returns a tuple of (rendered, unmatched) where rendered is a list of rendered strings with all substitutions made and unmatched is a list of any strings that resembled a template substitution but did not match a known substitution. E.g. if template contained "{foo}", unmatched would be ["foo"].  If there are unmatched strings, rendered will be [].  E.g. a template statement must fully match or will result in error and return all unmatched fields in unmatched.

e.g. `photo.render_template("{created.year}/{foo}")` would return `([],["foo"])`

Some substitutions, notably `album`, `keyword`, and `person` could return multiple values, hence a new string will be return for each possible substitution (hence why a list of rendered strings is returned).  For example, a photo in 2 albums: 'Vacation' and 'Family' would result in the following rendered values if template was "{created.year}/{album}" and created.year == 2020: `["2020/Vacation","2020/Family"]`

See [Template System](#template-system) for additional details.

#### <a name="detected_text_method">`detected_text(confidence_threshold=TEXT_DETECTION_CONFIDENCE_THRESHOLD)`</a>

Detects text in photo and returns lists of results as (detected text, confidence)

* `confidence_threshold`: float between 0.0 and 1.0. If text detection confidence is below this threshold, text will not be returned. Default is `osxphotos._constants.TEXT_DETECTION_CONFIDENCE_THRESHOLD`

If photo is edited, uses the edited photo, otherwise the original; falls back to the preview image if neither edited or original is available.

Returns: list of (detected text, confidence) tuples.

Note: This is *not* the same as Live Text in macOS Monterey.  When using `detected_text()`, osxphotos will use Apple's [Vision framework](https://developer.apple.com/documentation/vision/recognizing_text_in_images?language=objc) to perform text detection on the image.  On my circa 2013 MacBook Pro, this takes about 2 seconds per image.  `detected_text()` does memoize the results for a given `confidence_threshold` so repeated calls will not re-process the photo.  This works only on macOS Catalina (10.15) or later.

See also [Text Detection](#textdetection).

### ExifInfo

[PhotosInfo.exif_info](#exif-info) returns an `ExifInfo` object with some EXIF data about the photo (Photos 5 only).  `ExifInfo` contains the following properties:

```python
    flash_fired: bool
    iso: int
    metering_mode: int
    sample_rate: int
    track_format: int
    white_balance: int
    aperture: float
    bit_rate: float
    duration: float
    exposure_bias: float
    focal_length: float
    fps: float
    latitude: float
    longitude: float
    shutter_speed: float
    camera_make: str
    camera_model: str
    codec: str
    lens_model: str
```

For example:

```python
import osxphotos

nikon_photos = [
    p
    for p in osxphotos.PhotosDB().photos()
    if p.exif_info.camera_make and "nikon" in p.exif_info.camera_make.lower()
]
```

### AlbumInfo

PhotosDB.album_info and PhotoInfo.album_info return a list of AlbumInfo objects.  Each AlbumInfo object represents a single album in the Photos library.

#### `uuid`

Returns the universally unique identifier (uuid) of the album.  This is how Photos keeps track of individual objects within the database.

#### `title`

Returns the title or name of the album.

#### <a name="albumphotos">`photos`</a>

Returns a list of [PhotoInfo](#PhotoInfo) objects representing each photo contained in the album sorted in the same order as in Photos. (e.g. if photos were manually sorted in the Photos albums, photos returned by `photos` will be in same order as they appear in the Photos album)

#### `creation_date`

Returns the creation date as a timezone aware datetime.datetime object of the album.

#### `start_date`

Returns the date of earliest photo in the album as a timezone aware datetime.datetime object.

#### `end_date`

Returns the date of latest photo in the album as a timezone aware datetime.datetime object.

#### `folder_list`

Returns a hierarchical list of [FolderInfo](#FolderInfo) objects representing the folders the album is contained in.  For example, if album "AlbumInFolder" is in SubFolder2 of Folder1 as illustrated below, would return a list of `FolderInfo` objects representing ["Folder1", "SubFolder2"]

```txt
Photos Library
├── Folder1
    ├── SubFolder1
    ├── SubFolder2
        └── AlbumInFolder
```

#### `folder_names`

Returns a hierarchical list of names of the folders the album is contained in.  For example, if album is in SubFolder2 of Folder1 as illustrated below, would return ["Folder1", "SubFolder2"].  

```txt
Photos Library
├── Folder1
    ├── SubFolder1
    ├── SubFolder2
        └── AlbumInFolder
```

#### `parent`

Returns a [FolderInfo](#FolderInfo) object representing the albums parent folder or `None` if album is not a in a folder.

#### `owner`

Returns full name of the album owner (person who shared the album) for shared albums or None if album is not shared.

**Note**: *Only valid on Photos 5 / MacOS 10.15+; on Photos <= 4, returns None.

### ImportInfo

PhotosDB.import_info returns a list of ImportInfo objects.  Each ImportInfo object represents an import session in the library.  PhotoInfo.import_info returns a single ImportInfo object representing the import session for the photo (or `None` if no associated import session).

**Note**: Photos 5+ only.  Not implemented for Photos version <= 4.

#### `uuid`

Returns the universally unique identifier (uuid) of the import session.  This is how Photos keeps track of individual objects within the database.

#### <a name="importphotos">`photos`</a>

Returns a list of [PhotoInfo](#PhotoInfo) objects representing each photo contained in the import session.

#### `creation_date`

Returns the creation date as a timezone aware datetime.datetime object of the import session.

#### `start_date`

Returns the start date as a timezone aware datetime.datetime object for when the import session bega.

#### `end_date`

Returns the end date as a timezone aware datetime.datetime object for when the import session completed.

### ProjectInfo

PhotosDB.projcet_info returns a list of ProjectInfo objects.  Each ProjectInfo object represents a project in the library.  PhotoInfo.project_info returns a list of ProjectInfo objects for each project the photo is contained in.

Projects (found under "My Projects" in Photos) are projects or creations such as cards, calendars, and slideshows created in Photos.  osxphotos provides only very basic information about projects and projects created with third party plugins may not accessible to osxphotos.

#### `uuid`

Returns the universally unique identifier (uuid) of the project.  This is how Photos keeps track of individual objects within the database.

#### `title`

Returns the title or name of the project.

#### <a name="projectphotos">`photos`</a>

Returns a list of [PhotoInfo](#PhotoInfo) objects representing each photo contained in the project.

#### `creation_date`

Returns the creation date as a timezone aware datetime.datetime object of the project.

### MomentInfo

PhotoInfo.moment_info return the MomentInfo object for the photo.  The MomentInfo object contains information about the photo's moment as assigned by Photos.  The MomentInfo object contains the following properties:

#### `pk`

Returns the primary key of the moment in the Photos database.

#### `location`

Returns the location of the moment as a tuple of (latitude, longitude).

#### `title`

Returns the title of the moment.

#### `subtitle`

Returns the subtitle of the moment.

#### `start_date`

Returns the start date of the moment as a timezone aware datetime.datetime object.

#### `end_date`

Returns the end date of the moment as a timezone aware datetime.datetime object.

#### `date`

Returns the date of the moment as a timezone aware datetime.datetime object.

#### `modification_date`

Returns the modification date of the moment as a timezone aware datetime.datetime object.

#### `photos`

Returns a list of [PhotoInfo] objects representing the photos in the moment.

#### `asdict()`

Returns a dictionary representation of the moment.

### FolderInfo

PhotosDB.folder_info returns a list of FolderInfo objects representing the top level folders in the library.  Each FolderInfo object represents a single folder in the Photos library.

#### `uuid`

Returns the universally unique identifier (uuid) of the folder.  This is how Photos keeps track of individual objects within the database.

#### `title`

Returns the title or name of the folder.

#### `album_info`

Returns a list of [AlbumInfo](#AlbumInfo) objects representing each album contained in the folder.

#### `album_info_shared`

Returns a list of [AlbumInfo](#AlbumInfo) objects for each shared album in the photos database.

**Note**: Only valid for Photos 5+; on Photos <= 4, prints warning and returns empty list.

#### `subfolders`

Returns a list of [FolderInfo](#FolderInfo) objects representing the sub-folders of the folder.  

#### `parent`

Returns a [FolderInfo](#FolderInfo) object representing the folder's parent folder or `None` if album is not a in a folder.

#### `sort_order`

Returns album sort order (as `AlbumSortOrder` enum).  On Photos <=4, always returns `AlbumSortOrder.MANUAL`.

`AlbumSortOrder` has following values:

* `UNKNOWN`
* `MANUAL`
* `NEWEST_FIRST`
* `OLDEST_FIRST`
* `TITLE`

#### `photo_index(photo)`

Returns index of photo in album (based on album sort order).

**Note**: FolderInfo and AlbumInfo objects effectively work as a linked list.  The children of a folder are contained in `subfolders` and `album_info` and the parent object of both `AlbumInfo` and `FolderInfo` is represented by `parent`.  For example:

```pycon
>>> import osxphotos
>>> photosdb = osxphotos.PhotosDB()
>>> photosdb.folder_info
[<osxphotos.albuminfo.FolderInfo object at 0x10fcc0160>]
>>> photosdb.folder_info[0].title
'Folder1'
>>> photosdb.folder_info[0].subfolders[1].title
'SubFolder2'
>>> photosdb.folder_info[0].subfolders[1].album_info[0].title
'AlbumInFolder'
>>> photosdb.folder_info[0].subfolders[1].album_info[0].parent.title
'SubFolder2'
>>> photosdb.folder_info[0].subfolders[1].album_info[0].parent.album_info[0].title
'AlbumInFolder'
```

### PlaceInfo

[PhotoInfo.place](#place) returns a PlaceInfo object if the photo contains valid reverse geolocation information.  PlaceInfo has the following properties.  

**Note** For Photos versions <= 4, only `name`, `names`, and `country_code` properties are defined.  All others return `None`.  This is because older versions of Photos do not store the more detailed reverse geolocation information.

#### `ishome`

Returns `True` if photo place is user's home address, otherwise `False`.

#### `name`

Returns the name of the local place as str.  This is what Photos displays in the Info window.  **Note** Photos 5 uses a different algorithm to determine the name than earlier versions which means the same Photo may have a different place name in Photos 4 and Photos 5. `PhotoInfo.name` will return the name Photos would have shown depending on the version of the library being processed.  In Photos 5, the place name is generally more detailed than in earlier versions of Photos.

For example, I have photo in my library that under Photos 4, has place name of "‎⁨Mayfair Shopping Centre⁩, ⁨Victoria⁩, ⁨Canada⁩" and under Photos 5 the same photo has place name of "Mayfair⁩, ⁨Vancouver Island⁩, ⁨Victoria⁩, ⁨British Columbia⁩, ⁨Canada⁩".

Returns `None` if photo does not contain a name.

#### `names`

Returns a `PlaceNames` namedtuple with the following fields.  Each field is a list with zero or more values, sorted by area in ascending order.  E.g. `names.area_of_interest` could be ['Gulf Islands National Seashore', 'Santa Rosa Island'], ["Knott's Berry Farm"], or [] if `area_of_interest` not defined.  The value shown in Photos is the first value in the list. With the exception of `body_of_water` each of these field corresponds to an attribute of a [CLPlacemark](https://developer.apple.com/documentation/corelocation/clplacemark) object.  **Note** The `PlaceNames` namedtuple contains reserved fields not listed below (see implementation for details), thus it should be referenced only by name (e.g. `names.city`) and not by index.

* `country`; the name of the country associated with the placemark.
* `state_province`; administrativeArea, The state or province associated with the placemark.
* `sub_administrative_area`; additional administrative area information for the placemark.
* `city`; locality; the city associated with the placemark.
* `additional_city_info`; subLocality, Additional city-level information for the placemark.
* `ocean`; the name of the ocean associated with the placemark.
* `area_of_interest`; areasOfInterest, The relevant areas of interest associated with the placemark.
* `inland_water`; the name of the inland water body associated with the placemark.
* `region`; the geographic region associated with the placemark.
* `sub_throughfare`; additional street-level information for the placemark.
* `postal_code`; the postal code associated with the placemark.
* `street_address`; throughfare, The street address associated with the placemark.
* `body_of_water`; in Photos 4, any body of water; in Photos 5 contains the union of ocean and inland_water

**Note**: In Photos <= 4.0, only the following fields are defined; all others are set to empty list:

* `country`
* `state_province`
* `sub_administrative_area`
* `city`
* `additional_city_info`
* `area_of_interest`
* `body_of_water`

#### `country_code`

Returns the country_code of place, for example "GB".  Returns `None` if PhotoInfo contains no country code.

#### `address_str`

Returns the full postal address as a string if defined, otherwise `None`.

For example: "2038 18th St NW, Washington, DC  20009, United States"

#### `address`

Returns a `PostalAddress` namedtuple with details of the postal address containing the following fields:

* `city`
* `country`
* `postal_code`
* `state`
* `street`
* `sub_administrative_area`
* `sub_locality`
* `iso_country_code`

For example:

```pycon
>>> photo.place.address
PostalAddress(street='3700 Wailea Alanui Dr', sub_locality=None, city='Kihei', sub_administrative_area='Maui', state='HI', postal_code='96753', country='United States', iso_country_code='US')
>>> photo.place.address.postal_code
'96753'
```

### ScoreInfo

[PhotoInfo.score](#score) returns a ScoreInfo object that exposes the computed aesthetic scores for each photo (**Photos 5+ only**).  I have not yet reverse engineered the meaning of each score.  The `overall` score seems to the most useful and appears to be a composite of the other scores.  The following score properties are currently available:

```python
overall: float
curation: float
promotion: float
highlight_visibility: float
behavioral: float
failure: float
harmonious_color: float
immersiveness: float
interaction: float
interesting_subject: float
intrusive_object_presence: float
lively_color: float
low_light: float
noise: float
pleasant_camera_tilt: float
pleasant_composition: float
pleasant_lighting: float
pleasant_pattern: float
pleasant_perspective: float
pleasant_post_processing: float
pleasant_reflection: float
pleasant_symmetry: float
sharply_focused_subject: float
tastefully_blurred: float
well_chosen_subject: float
well_framed_subject: float
well_timed_shot: float
```

Example: find your "best" photo of food

```python
>>> import osxphotos
>>> photos = osxphotos.PhotosDB().photos()
>>> best_food_photo = sorted([p for p in photos if "food" in p.labels_normalized], key=lambda p: p.score.overall, reverse=True)[0]
```

### SearchInfo

[PhotoInfo.search_info](#photosearchinfo) and [PhotoInfo.search_info_normalized](#photosearchinfo-normalized) return a SearchInfo object that exposes various metadata that Photos uses when searching for photos such as labels, associated holiday, etc. (**Photos 5+ only**).

The following properties are available:

#### `labels`

Returns list of labels applied to photo by Photos image categorization algorithms.

#### `place_names`

Returns list of place names associated with the photo.

#### `streets`

Returns list of street names associated with the photo. (e.g. reverse geolocation of where the photo was taken)

#### `neighborhoods`

Returns list of neighborhood names associated with the photo.

#### `locality_names`

Returns list of locality names associated with the photo.

#### `city`

Returns str of city/town/municipality associated with the photo.

#### `state`

Returns str of state name associated with the photo.

#### `state_abbreviation`

Returns str of state abbreviation associated with the photo.

#### `country`

Returns str of country name associated with the photo.

#### `month`

Returns str of month name associated witht the photo (e.g. month in which the photo was taken)

#### `year`

Returns year associated with the photo.

#### `bodies_of_water`

Returns list of bodies of water associated with the photo.

#### `holidays`

Returns list of holiday names associated with the photo.

#### `activities`

Returns list of activities associated with the photo.

#### `season`

Returns str of season name associated with the photo.

#### `venues`

Returns list of venue names associated with the photo.

#### `venue_types`

Returns list of venue types associated with the photoo.

#### `media_types`

Returns list of media types associated with the photo.

#### `all`

Returns all search_info properties as a single list of strings.

#### `asdict()`

Returns all associated search_info metadata as a dict.

### PersonInfo

[PhotosDB.person_info](#dbpersoninfo) and [PhotoInfo.person_info](#photopersoninfo) return a list of PersonInfo objects represents persons in the database and in a photo, respectively.  The PersonInfo class has the following properties and methods.

#### `name`

Returns the full name of the person represented in the photo. For example, "Maria Smith".

#### `display_name`

Returns the display name of the person represented in the photo. For example, "Maria".

#### `uuid`

Returns the UUID of the person as stored in the Photos library database.

#### `keyphoto`

Returns a PhotoInfo instance for the photo designated as the key photo for the person. This is the Photos uses to display the person's face thumbnail in Photos' "People" view.

#### `facecount`

Returns a count of how many times this person appears in images in the database.

#### <a name="personphotos">`photos`</a>

Returns a list of PhotoInfo objects representing all photos the person appears in.

#### <a name="personfaceinfo">`face_info`</a>

Returns a list of [FaceInfo](#faceinfo) objects associated with this person sorted by quality score. Highest quality face is result[0] and lowest quality face is result[n].

#### `json()`

Returns a json string representation of the PersonInfo instance.

#### `asdict()`

Returns a dictionary representation of the PersonInfo instance.

### FaceInfo

[PhotoInfo.face_info](#photofaceinfo) return a list of FaceInfo objects representing detected faces in a photo.  The FaceInfo class has the following properties and methods.

#### `uuid`

UUID of the face.

#### `name`

Full name of the person represented by the face or None if person hasn't been given a name in Photos.  This is a shortcut for `FaceInfo.person_info.name`.

#### `asset_uuid`

UUID of the photo this face is associated with.

#### `person_info`

[PersonInfo](#personinfo) object associated with this face.

#### `photo`

[PhotoInfo](#photoinfo) object representing the photo that contains this face.

#### `mwg_rs_area`

Returns named tuple with following coordinates as used in Metdata Working Group (mwg) face regions in XMP files.

* `x` = `stArea:x`
* `y` = `stArea:y`
* `h` = `stArea:h`
* `w` = `stArea:w`

#### `mpri_reg_rect`

Returnes named tuple with following coordinates as used in Microsoft Photo Region Rectangle (mpri) in XMP files.

* `x` = x coordinate of top left corner of rectangle
* `y` = y coordinate of top left corner of rectangle
* `h` = height of rectangle
* `w` = width of rectangle

#### `face_rect()`

Returns list of x, y coordinates as tuples `[(x0, y0), (x1, y1)]` representing the corners of rectangular region that contains the face.  Coordinates are in same format and [reference frame](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#coordinate-system) as used by [Pillow](https://pypi.org/project/Pillow/) imaging library.  **Note**: face_rect() and all other properties/methods that return coordinates refer to the *current version* of the image. E.g. if the image has been edited ([`PhotoInfo.hasadjustments`](#hasadjustments)), these refer to [`PhotoInfo.path_edited`](#pathedited).  If the image has no adjustments, these coordinates refer to the original photo ([`PhotoInfo.path`](#path)).

#### `center`

Coordinates as (x, y) tuple for the center of the detected face.

#### `size_pixels`

Diameter of detected face region in pixels.

#### `roll_pitch_yaw()`

Roll, pitch, and yaw of face region in radians.  Returns a tuple of (roll, pitch, yaw)

#### roll

Roll of face region in radians.

#### pitch

Pitch of face region in radians.

**Note**: Only valid on Photos version <= 4, otherwise returns 0

#### yaw

Yaw of face region in radians.

**Note**: Only valid on Photos version <= 4, otherwise returns 0

#### `Additional properties`

The following additional properties are also available but are not yet fully documented.

* `center_x`: x coordinate of center of face in Photos' internal reference frame
* `center_y`: y coordinate of center of face in Photos' internal reference frame
* `size`: size of face region in Photos' internal reference frame
* `quality`: quality measure of detected face
* `source_width`: width in pixels of photo
* `source_height`: height in pixels of photo
* `has_smile`:
* `manual`:
* `face_type`:
* `age_type`:
* `eye_makeup_type`:
* `eye_state`:
* `facial_hair_type`:
* `gender_type`:
* `glasses_type`:
* `hair_color_type`:
* `lip_makeup_type`:
* `smile_type`:

#### `asdict()`

Returns a dictionary representation of the FaceInfo instance.

#### `json()`

Returns a JSON representation of the FaceInfo instance.

### CommentInfo

[PhotoInfo.comments](#comments) returns a list of CommentInfo objects for comments on shared photos. (Photos 5/MacOS 10.15+ only).  The list of CommentInfo objects will be sorted in ascending order by date comment was made.  CommentInfo contains the following fields:

* `datetime`: `datetime.datetime`, date/time comment was made
* `user`: `str`, name of user who made the comment
* `ismine`: `bool`, True if comment was made by person who owns the Photos library being operated on
* `text`: `str`, text of the actual comment

### LikeInfo

[PhotoInfo.likes](#likes) returns a list of LikeInfo objects for "likes" on shared photos. (Photos 5/MacOS 10.15+ only).  The list of LikeInfo objects will be sorted in ascending order by date like was made.  LikeInfo contains the following fields:

* `datetime`: `datetime.datetime`, date/time like was made
* `user`: `str`, name of user who made the like
* `ismine`: `bool`, True if like was made by person who owns the Photos library being operated on

### AdjustmentsInfo

[PhotoInfo.adjustments](#adjustments) returns an AdjustmentsInfo object, if the photo has adjustments, or `None` if the photo does not have adjusments.   AdjustmentsInfo has the following properties and methods:

* `plist`: The adjustments plist file maintained by Photos as a dict.
* `data`: The raw, undecoded adjustments info as binary blob.
* `editor`: The editor bundle ID of the app which made the edits, e.g. `com.apple.photos`.
* `format_id`: The format identifier set by the app which made the edits, e.g. `com.apple.photos`.
* `base_version`: Version info set by the app which made the edits.
* `format_version`: Version info set by the app which made the edits.
* `timestamp`: Time stamp of the adjustment as a timezone-aware datetime.datetime object; None if no timestamp is set.
* `adjustments`: a list of dicts containing information about the decoded adjustments to the photo or None if adjustments could not be decoded. AdjustmentsInfo can decode adjustments made by Photos but cannot decode adjustments made by external plugins or apps.
* `adj_metadata`: a dict containing additional data about the photo decoded from the adjustment data.
* `adj_orientation`: the EXIF orientation of the edited photo decoded from the adjustment metadata.
* `adj_format_version`: version for adjustments format decoded from the adjustment data.
* `adj_version_info`: version info for the application which made the adjustments to the photo decoded from the adjustments data.
* `asdict()`: dict representation of the AdjustmentsInfo object; contains all properties with exception of `plist`.

### Raw Photos

Handling raw photos in `osxphotos` requires a bit of extra work.  Raw photos in Photos can be imported in two different ways: 1) a single raw photo with no associated JPEG image is imported 2) a raw+JPEG pair is imported -- two separate images with same file stem (e.g. `IMG_0001.CR2` and `IMG_001.JPG`) are imported.  

The latter are treated by Photos as a single image.  By default, Photos will treat these as a JPEG image.  They are denoted in the Photos interface with a "J" icon superimposed on the image.  In Photos, the user can select "Use RAW as original" in which case the "J" icon changes to an "R" icon and all subsequent edits will use the raw image as the original. To further complicate this, different versions of Photos handle these differently in their internal logic.  

`osxphotos` attempts to simplify the handling of these raw+JPEG pairs by providing a set of attributes for accessing both the JPEG and the raw version.  For example, [PhotoInfo.has_raw](#has_raw) will be True if the photo has an associated raw image but False otherwise and [PhotoInfo.path_raw](#path_raw) provides the path to the associated raw image.  Reference the following table for the various attributes useful for dealing with raw images.  Given the different ways Photos deals with raw images I've struggled with how to represent these in a logical and consistent manner.  If you have suggestions for a better interface, please open an [issue](https://github.com/RhetTbull/osxphotos/issues)!

#### Raw-Related Attributes

|`PhotoInfo` attribute|`IMG_0001.CR2` imported without raw+JPEG pair|`IMG_0001.CR2` + `IMG_0001.JPG` raw+JPEG pair, JPEG is original|`IMG_0001.CR2` + `IMG_0001.JPG` raw+jpeg pair, raw is original|
|----------|----------|----------|----------|
|[israw](#israw)| True | False | False |
|[has_raw](#has_raw)| False | True | True |
|[uti](#uti) | `com.canon.cr2-raw-image` | `public.jpeg` | `public.jpeg` |
|[uti_raw](#uti_raw) | None | `com.canon.cr2-raw-image` | `com.canon.cr2-raw-image` |
|[raw_original](#raw_original) | False | False | True |
|[path](#path) | `/path/to/IMG_0001.CR2` | `/path/to/IMG_0001.JPG` | `/path/to/IMG_0001.JPG` |
|[path_raw](#path_raw) | None | `/path/to/IMG_0001.CR2` | `/path/to/IMG_0001.CR2` |

#### Example

To get the path of every raw photo, whether it's a single raw photo or a raw+JPEG pair, one could do something like this:

```pycon
>>> import osxphotos
>>> photosdb = osxphotos.PhotosDB()
>>> photos = photosdb.photos()
>>> all_raw = [p for p in photos if p.israw or p.has_raw]
>>> for raw in all_raw:
...     path = raw.path if raw.israw else raw.path_raw
...     print(path)
```

### Template System

<!--[[[cog
from osxphotos.phototemplate import get_template_help
cog.out(get_template_help())
]]]-->
<!-- Generated by cog: see phototemplate.cog.md -->

The templating system converts one or template statements, written in osxphotos metadata templating language, to one or more rendered values using information from the photo being processed.

In its simplest form, a template statement has the form: `"{template_field}"`, for example `"{title}"` which would resolve to the title of the photo.

Template statements may contain one or more modifiers.  The full syntax is:

`"pretext{delim+template_field:subfield(field_arg)|filter[find,replace] conditional?bool_value,default}posttext"`

Template statements are white-space sensitive meaning that white space (spaces, tabs) changes the meaning of the template statement.

`pretext` and `posttext` are free form text.  For example, if a photo has title "My Photo Title" the template statement `"The title of the photo is {title}"`, resolves to `"The title of the photo is My Photo Title"`.  The `pretext` in this example is `"The title if the photo is "` and the template_field is `{title}`.

`delim`: optional delimiter string to use when expanding multi-valued template values in-place

`+`: If present before template `name`, expands the template in place.  If `delim` not provided, values are joined with no delimiter.

e.g. if Photo keywords are `["foo","bar"]`:

- `"{keyword}"` renders to `"foo", "bar"`
- `"{,+keyword}"` renders to: `"foo,bar"`
- `"{; +keyword}"` renders to: `"foo; bar"`
- `"{+keyword}"` renders to `"foobar"`

`template_field`: The template field to resolve.  See [Template Substitutions](#template-substitutions) for full list of template fields.

`:subfield`: Some templates have sub-fields, For example, `{exiftool:IPTC:Make}`; the template_field is `exiftool` and the sub-field is `IPTC:Make`.

`(field_arg)`: optional arguments to pass to the field; for example, with `{folder_album}` this is used to pass the path separator used for joining folders and albums when rendering the field (default is "/" for `{folder_album}`).

`|filter`: You may optionally append one or more filter commands to the end of the template field using the vertical pipe ('|') symbol.  Filters may be combined, separated by '|' as in: `{keyword|capitalize|parens}`.

Valid filters are:

- `lower`: Convert value to lower case, e.g. 'Value' => 'value'.
- `upper`: Convert value to upper case, e.g. 'Value' => 'VALUE'.
- `strip`: Strip whitespace from beginning/end of value, e.g. ' Value ' => 'Value'.
- `titlecase`: Convert value to title case, e.g. 'my value' => 'My Value'.
- `capitalize`: Capitalize first word of value and convert other words to lower case, e.g. 'MY VALUE' => 'My value'.
- `braces`: Enclose value in curly braces, e.g. 'value => '{value}'.
- `parens`: Enclose value in parentheses, e.g. 'value' => '(value')
- `brackets`: Enclose value in brackets, e.g. 'value' => '[value]'
- `shell_quote`: Quotes the value for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.
- `function`: Run custom python function to filter value; use in format 'function:/path/to/file.py::function_name'. See example at https://github.com/RhetTbull/osxphotos/blob/master/examples/template_filter.py
- `split(x)`: Split value into a list of values using x as delimiter, e.g. 'value1;value2' => ['value1', 'value2'] if used with split(;).
- `autosplit`: Automatically split delimited string into separate values; will split strings delimited by comma, semicolon, or space, e.g. 'value1,value2' => ['value1', 'value2'].
- `chop(x)`: Remove x characters off the end of value, e.g. chop(1): 'Value' => 'Valu'; when applied to a list, chops characters from each list value, e.g. chop(1): ['travel', 'beach']=> ['trave', 'beac'].
- `chomp(x)`: Remove x characters from the beginning of value, e.g. chomp(1): ['Value'] => ['alue']; when applied to a list, removes characters from each list value, e.g. chomp(1): ['travel', 'beach']=> ['ravel', 'each'].
- `sort`: Sort list of values, e.g. ['c', 'b', 'a'] => ['a', 'b', 'c'].
- `rsort`: Sort list of values in reverse order, e.g. ['a', 'b', 'c'] => ['c', 'b', 'a'].
- `reverse`: Reverse order of values, e.g. ['a', 'b', 'c'] => ['c', 'b', 'a'].
- `uniq`: Remove duplicate values, e.g. ['a', 'b', 'c', 'b', 'a'] => ['a', 'b', 'c'].
- `join(x)`: Join list of values with delimiter x, e.g. join(,): ['a', 'b', 'c'] => 'a,b,c'; the DELIM option functions similar to join(x) but with DELIM, the join happens before being passed to any filters.May optionally be used without an argument, that is 'join()' which joins values together with no delimiter. e.g. join(): ['a', 'b', 'c'] => 'abc'.
- `append(x)`: Append x to list of values, e.g. append(d): ['a', 'b', 'c'] => ['a', 'b', 'c', 'd'].
- `prepend(x)`: Prepend x to list of values, e.g. prepend(d): ['a', 'b', 'c'] => ['d', 'a', 'b', 'c'].
- `remove(x)`: Remove x from list of values, e.g. remove(b): ['a', 'b', 'c'] => ['a', 'c'].
- `slice(start:stop:step)`: Slice list using same semantics as Python's list slicing, e.g. slice(1:3): ['a', 'b', 'c', 'd'] => ['b', 'c']; slice(1:4:2): ['a', 'b', 'c', 'd'] => ['b', 'd']; slice(1:): ['a', 'b', 'c', 'd'] => ['b', 'c', 'd']; slice(:-1): ['a', 'b', 'c', 'd'] => ['a', 'b', 'c']; slice(::-1): ['a', 'b', 'c', 'd'] => ['d', 'c', 'b', 'a']. See also sslice().
- `sslice(start:stop:step)`: [s(tring) slice] Slice values in a list using same semantics as Python's string slicing, e.g. sslice(1:3):'abcd => 'bc'; sslice(1:4:2): 'abcd' => 'bd', etc. See also slice().
- `filter(x)`: Filter list of values using predicate x; for example, `{folder_album|filter(contains Events)}` returns only folders/albums containing the word 'Events' in their path.
- `int`: Convert values in list to integer, e.g. 1.0 => 1. If value cannot be converted to integer, remove value from list. ['1.1', 'x'] => ['1']. See also float.
- `float`: Convert values in list to floating point number, e.g. 1 => 1.0. If value cannot be converted to float, remove value from list. ['1', 'x'] => ['1.0']. See also int.

e.g. if Photo keywords are `["FOO","bar"]`:

- `"{keyword|lower}"` renders to `"foo", "bar"`
- `"{keyword|upper}"` renders to: `"FOO", "BAR"`
- `"{keyword|capitalize}"` renders to: `"Foo", "Bar"`
- `"{keyword|lower|parens}"` renders to: `"(foo)", "(bar)"`

e.g. if Photo description is "my description":

- `"{descr|titlecase}"` renders to: `"My Description"`

e.g. If Photo is in `Album1` in `Folder1`:

- `"{folder_album}"` renders to `["Folder1/Album1"]`
- `"{folder_album(>)}"` renders to `["Folder1>Album1"]`
- `"{folder_album()}"` renders to `["Folder1Album1"]`

`[find,replace]`: optional text replacement to perform on rendered template value.  For example, to replace "/" in an album name, you could use the template `"{album[/,-]}"`.  Multiple replacements can be made by appending "|" and adding another find|replace pair.  e.g. to replace both "/" and ":" in album name: `"{album[/,-|:,-]}"`.  find/replace pairs are not limited to single characters.  The "|" character cannot be used in a find/replace pair.

`conditional`: optional conditional expression that is evaluated as boolean (True/False) for use with the `?bool_value` modifier.  Conditional expressions take the form '`not operator value`' where `not` is an optional modifier that negates the `operator`.  Note: the space before the conditional expression is required if you use a conditional expression.  Valid comparison operators are:

- `contains`: template field contains value, similar to python's `in`
- `matches`: template field contains exactly value, unlike `contains`: does not match partial matches
- `startswith`: template field starts with value
- `endswith`: template field ends with value
- `<=`: template field is less than or equal to value
- `>=`: template field is greater than or equal to value
- `<`: template field is less than value
- `>`: template field is greater than value
- `==`: template field equals value
- `!=`: template field does not equal value

The `value` part of the conditional expression is treated as a bare (unquoted) word/phrase.  Multiple values may be separated by '|' (the pipe symbol).  `value` is itself a template statement so you can use one or more template fields in `value` which will be resolved before the comparison occurs.

For example:

- `{keyword matches Beach}` resolves to True if 'Beach' is a keyword. It would not match keyword 'BeachDay'.
- `{keyword contains Beach}` resolves to True if any keyword contains the word 'Beach' so it would match both 'Beach' and 'BeachDay'.
- `{photo.score.overall > 0.7}` resolves to True if the photo's overall aesthetic score is greater than 0.7.
- `{keyword|lower contains beach}` uses the lower case filter to do case-insensitive matching to match any keyword that contains the word 'beach'.
- `{keyword|lower not contains beach}` uses the `not` modifier to negate the comparison so this resolves to True if there is no keyword that matches 'beach'.

Examples: to export photos that contain certain keywords with the `osxphotos export` command's `--directory` option:

`--directory "{keyword|lower matches travel|vacation?Travel-Photos,Not-Travel-Photos}"`

This exports any photo that has keywords 'travel' or 'vacation' into a directory 'Travel-Photos' and all other photos into directory 'Not-Travel-Photos'.

This can be used to rename files as well, for example:
`--filename "{favorite?Favorite-{original_name},{original_name}}"`

This renames any photo that is a favorite as 'Favorite-ImageName.jpg' (where 'ImageName.jpg' is the original name of the photo) and all other photos with the unmodified original name.

`?bool_value`: Template fields may be evaluated as boolean (True/False) by appending "?" after the field name (and following "(field_arg)" or "[find/replace]".  If a field is True (e.g. photo is HDR and field is `"{hdr}"`) or has any value, the value following the "?" will be used to render the template instead of the actual field value.  If the template field evaluates to False (e.g. in above example, photo is not HDR) or has no value (e.g. photo has no title and field is `"{title}"`) then the default value following a "," will be used.  

e.g. if photo is an HDR image,

- `"{hdr?ISHDR,NOTHDR}"` renders to `"ISHDR"`

and if it is not an HDR image,

- `"{hdr?ISHDR,NOTHDR}"` renders to `"NOTHDR"`

`,default`: optional default value to use if the template name has no value.  This modifier is also used for the value if False for boolean-type fields (see above) as well as to hold a sub-template for values like `{created.strftime}`.  If no default value provided, "_" is used.

e.g., if photo has no title set,

- `"{title}"` renders to "_"
- `"{title,I have no title}"` renders to `"I have no title"`

Template fields such as `created.strftime` use the default value to pass the template to use for `strftime`.  

e.g., if photo date is 4 February 2020, 19:07:38,

- `"{created.strftime,%Y-%m-%d-%H%M%S}"` renders to `"2020-02-04-190738"`

Some template fields such as `"{media_type}"` use the default value to allow customization of the output. For example, `"{media_type}"` resolves to the special media type of the photo such as `panorama` or `selfie`.  You may use the default value to override these in form: `"{media_type,video=vidéo;time_lapse=vidéo_accélérée}"`. In this example, if photo was a time_lapse photo, `media_type` would resolve to `vidéo_accélérée` instead of `time_lapse`.

Either or both bool_value or default (False value) may be empty which would result in empty string `""` when rendered.

If you want to include "{" or "}" in the output, use "{openbrace}" or "{closebrace}" template substitution.

e.g. `"{created.year}/{openbrace}{title}{closebrace}"` would result in `"2020/{Photo Title}"`.

**Variables**

You can define variables for later use in the template string using the format `{var:NAME,VALUE}`.  Variables may then be referenced using the format `%NAME`. For example: `{var:foo,bar}` defines the variable `%foo` to have value `bar`. This can be useful if you want to re-use a complex template value in multiple places within your template string or for allowing the use of characters that would otherwise be prohibited in a template string. For example, the "pipe" (`|`) character is not allowed in a find/replace pair but you can get around this limitation like so: `{var:pipe,{pipe}}{title[-,%pipe]}` which replaces the `-` character with `|` (the value of `%pipe`).  

Variables can also be referenced as fields in the template string, for example: `{var:year,created.year}{original_name}-{%year}`. In some cases, use of variables can make your template string more readable.  Variables can be used as template fields, as values for filters, as values for conditional operations, or as default values.  When used as a conditional value or default value, variables should be treated like any other field and enclosed in braces as conditional and default values are evaluated as template strings. For example: `{var:name,Katie}{person contains {%name}?{%name},Not-{%name}}`.

If you need to use a `%` (percent sign character), you can escape the percent sign by using `%%`.  You can also use the `{percent}` template field where a template field is required. For example:

`{title[:,%%]}` replaces the `:` with `%` and `{title contains Foo?{title}{percent},{title}}` adds `%` to the  title if it contains `Foo`.
<!--[[[end]]] -->

The following template field substitutions are availabe for use the templating system.

<!--[[[cog
from osxphotos.phototemplate import get_template_field_table
cog.out(get_template_field_table())
]]]-->
| Field | Description |
|--------------|-------------|
|{name}|Current filename of the photo|
|{original_name}|Photo's original filename when imported to Photos|
|{title}|Title of the photo|
|{descr}|Description of the photo|
|{media_type}|Special media type resolved in this precedence: selfie, time_lapse, panorama, slow_mo, screenshot, portrait, live_photo, burst, photo, video. Defaults to 'photo' or 'video' if no special type. Customize one or more media types using format: '{media_type,video=vidéo;time_lapse=vidéo_accélérée}'|
|{photo_or_video}|'photo' or 'video' depending on what type the image is. To customize, use default value as in '{photo_or_video,photo=fotos;video=videos}'|
|{hdr}|Photo is HDR?; True/False value, use in format '{hdr?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{edited}|True if photo has been edited (has adjustments), otherwise False; use in format '{edited?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{edited_version}|True if template is being rendered for the edited version of a photo, otherwise False. |
|{favorite}|Photo has been marked as favorite?; True/False value, use in format '{favorite?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{created}|Photo's creation date in ISO format, e.g. '2020-03-22'|
|{created.date}|Photo's creation date in ISO format, e.g. '2020-03-22'|
|{created.year}|4-digit year of photo creation time|
|{created.yy}|2-digit year of photo creation time|
|{created.mm}|2-digit month of the photo creation time (zero padded)|
|{created.month}|Month name in user's locale of the photo creation time|
|{created.mon}|Month abbreviation in the user's locale of the photo creation time|
|{created.dd}|2-digit day of the month (zero padded) of photo creation time|
|{created.dow}|Day of week in user's locale of the photo creation time|
|{created.doy}|3-digit day of year (e.g Julian day) of photo creation time, starting from 1 (zero padded)|
|{created.hour}|2-digit hour of the photo creation time|
|{created.min}|2-digit minute of the photo creation time|
|{created.sec}|2-digit second of the photo creation time|
|{created.strftime}|Apply strftime template to file creation date/time. Should be used in form {created.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {created.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. See https://strftime.org/ for help on strftime templates.|
|{modified}|Photo's modification date in ISO format, e.g. '2020-03-22'; uses creation date if photo is not modified|
|{modified.date}|Photo's modification date in ISO format, e.g. '2020-03-22'; uses creation date if photo is not modified|
|{modified.year}|4-digit year of photo modification time; uses creation date if photo is not modified|
|{modified.yy}|2-digit year of photo modification time; uses creation date if photo is not modified|
|{modified.mm}|2-digit month of the photo modification time (zero padded); uses creation date if photo is not modified|
|{modified.month}|Month name in user's locale of the photo modification time; uses creation date if photo is not modified|
|{modified.mon}|Month abbreviation in the user's locale of the photo modification time; uses creation date if photo is not modified|
|{modified.dd}|2-digit day of the month (zero padded) of the photo modification time; uses creation date if photo is not modified|
|{modified.dow}|Day of week in user's locale of the photo modification time; uses creation date if photo is not modified|
|{modified.doy}|3-digit day of year (e.g Julian day) of photo modification time, starting from 1 (zero padded); uses creation date if photo is not modified|
|{modified.hour}|2-digit hour of the photo modification time; uses creation date if photo is not modified|
|{modified.min}|2-digit minute of the photo modification time; uses creation date if photo is not modified|
|{modified.sec}|2-digit second of the photo modification time; uses creation date if photo is not modified|
|{modified.strftime}|Apply strftime template to file modification date/time. Should be used in form {modified.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {modified.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. Uses creation date if photo is not modified. See https://strftime.org/ for help on strftime templates.|
|{today}|Current date in iso format, e.g. '2020-03-22'|
|{today.date}|Current date in iso format, e.g. '2020-03-22'|
|{today.year}|4-digit year of current date|
|{today.yy}|2-digit year of current date|
|{today.mm}|2-digit month of the current date (zero padded)|
|{today.month}|Month name in user's locale of the current date|
|{today.mon}|Month abbreviation in the user's locale of the current date|
|{today.dd}|2-digit day of the month (zero padded) of current date|
|{today.dow}|Day of week in user's locale of the current date|
|{today.doy}|3-digit day of year (e.g Julian day) of current date, starting from 1 (zero padded)|
|{today.hour}|2-digit hour of the current date|
|{today.min}|2-digit minute of the current date|
|{today.sec}|2-digit second of the current date|
|{today.strftime}|Apply strftime template to current date/time. Should be used in form {today.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {today.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. See https://strftime.org/ for help on strftime templates.|
|{place.name}|Place name from the photo's reverse geolocation data, as displayed in Photos|
|{place.country_code}|The ISO country code from the photo's reverse geolocation data|
|{place.name.country}|Country name from the photo's reverse geolocation data|
|{place.name.state_province}|State or province name from the photo's reverse geolocation data|
|{place.name.city}|City or locality name from the photo's reverse geolocation data|
|{place.name.area_of_interest}|Area of interest name (e.g. landmark or public place) from the photo's reverse geolocation data|
|{place.address}|Postal address from the photo's reverse geolocation data, e.g. '2007 18th St NW, Washington, DC 20009, United States'|
|{place.address.street}|Street part of the postal address, e.g. '2007 18th St NW'|
|{place.address.city}|City part of the postal address, e.g. 'Washington'|
|{place.address.state_province}|State/province part of the postal address, e.g. 'DC'|
|{place.address.postal_code}|Postal code part of the postal address, e.g. '20009'|
|{place.address.country}|Country name of the postal address, e.g. 'United States'|
|{place.address.country_code}|ISO country code of the postal address, e.g. 'US'|
|{searchinfo.season}|Season of the year associated with a photo, e.g. 'Summer'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{exif.camera_make}|Camera make from original photo's EXIF information as imported by Photos, e.g. 'Apple'|
|{exif.camera_model}|Camera model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s'|
|{exif.lens_model}|Lens model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s back camera 4.15mm f/2.2'|
|{moment}|The moment title of the photo|
|{uuid}|Photo's internal universally unique identifier (UUID) for the photo, a 36-character string unique to the photo, e.g. '128FB4C6-0B16-4E7D-9108-FB2E90DA1546'|
|{shortuuid}|A shorter representation of photo's internal universally unique identifier (UUID) for the photo, a 22-character string unique to the photo, e.g. 'JYsxugP9UjetmCbBCHXcmu'|
|{id}|A unique number for the photo based on its primary key in the Photos database. A sequential integer, e.g. 1, 2, 3...etc.  Each asset associated with a photo (e.g. an image and Live Photo preview) will share the same id. May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{id:05d}' which results in 00001, 00002, 00003...etc. |
|{album_seq}|An integer, starting at 0, indicating the photo's index (sequence) in the containing album. Only valid when used in a '--filename' template and only when '{album}' or '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{album_seq}_{original_name}"'. To start counting at a value other than 0, append append '(starting_value)' to the field name.  For example, to start counting at 1 instead of 0: '{album_seq(1)}'. May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{album_seq:05d}' which results in 00000, 00001, 00002...etc. To format while also using a starting value: '{album_seq:05d(1)}' which results in 0001, 00002...etc.This may result in incorrect sequences if you have duplicate albums with the same name; see also '{folder_album_seq}'.|
|{folder_album_seq}|An integer, starting at 0, indicating the photo's index (sequence) in the containing album and folder path. Only valid when used in a '--filename' template and only when '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{folder_album_seq}_{original_name}"'. To start counting at a value other than 0, append '(starting_value)' to the field name. For example, to start counting at 1 instead of 0: '{folder_album_seq(1)}' May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{folder_album_seq:05d}' which results in 00000, 00001, 00002...etc. To format while also using a starting value: '{folder_album_seq:05d(1)}' which results in 0001, 00002...etc.This may result in incorrect sequences if you have duplicate albums with the same name in the same folder; see also '{album_seq}'. |
|{comma}|A comma: ','|
|{semicolon}|A semicolon: ';'|
|{questionmark}|A question mark: '?'|
|{pipe}|A vertical pipe: '\|'|
|{openbrace}|An open brace: '{'|
|{closebrace}|A close brace: '}'|
|{openparens}|An open parentheses: '('|
|{closeparens}|A close parentheses: ')'|
|{openbracket}|An open bracket: '['|
|{closebracket}|A close bracket: ']'|
|{newline}|A newline: '\n'|
|{lf}|A line feed: '\n', alias for {newline}|
|{cr}|A carriage return: '\r'|
|{crlf}|A carriage return + line feed: '\r\n'|
|{tab}|:A tab: '\t'|
|{osxphotos_version}|The osxphotos version, e.g. '0.54.4'|
|{osxphotos_cmd_line}|The full command line used to run osxphotos|
|{album}|Album(s) photo is contained in|
|{folder_album}|Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder|
|{project}|Project(s) photo is contained in (such as greeting cards, calendars, slideshows)|
|{album_project}|Album(s) and project(s) photo is contained in; treats projects as regular albums|
|{folder_album_project}|Folder path + album (includes projects as albums) photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder|
|{keyword}|Keyword(s) assigned to photo|
|{person}|Person(s) / face(s) in a photo|
|{label}|Image categorization label associated with a photo (Photos 5+ only). Labels are added automatically by Photos using machine learning algorithms to categorize images. These are not the same as {keyword} which refers to the user-defined keywords/tags applied in Photos.|
|{label_normalized}|All lower case version of 'label' (Photos 5+ only)|
|{comment}|Comment(s) on shared Photos; format is 'Person name: comment text' (Photos 5+ only)|
|{exiftool}|Format: '{exiftool:GROUP:TAGNAME}'; use exiftool (https://exiftool.org) to extract metadata, in form GROUP:TAGNAME, from image.  E.g. '{exiftool:EXIF:Make}' to get camera make, or {exiftool:IPTC:Keywords} to extract keywords. See https://exiftool.org/TagNames/ for list of valid tag names.  You must specify group (e.g. EXIF, IPTC, etc) as used in `exiftool -G`. exiftool must be installed in the path to use this template.|
|{searchinfo.holiday}|Holiday names associated with a photo, e.g. 'Christmas Day'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.activity}|Activities associated with a photo, e.g. 'Sporting Event'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.venue}|Venues associated with a photo, e.g. name of restaurant; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.venue_type}|Venue types associated with a photo, e.g. 'Restaurant'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{photo}|Provides direct access to the PhotoInfo object for the photo. Must be used in format '{photo.property}' where 'property' represents a PhotoInfo property. For example: '{photo.favorite}' is the same as '{favorite}' and '{photo.place.name}' is the same as '{place.name}'. '{photo}' provides access to properties that are not available as separate template fields but it assumes some knowledge of the underlying PhotoInfo class.  See https://rhettbull.github.io/osxphotos/ for additional documentation on the PhotoInfo class.|
|{detected_text}|List of text strings found in the image after performing text detection. Using '{detected_text}' will cause osxphotos to perform text detection on your photos using the built-in macOS text detection algorithms which will slow down your export. The results for each photo will be cached in the export database so that future exports with '--update' do not need to reprocess each photo. You may pass a confidence threshold value between 0.0 and 1.0 after a colon as in '{detected_text:0.5}'; The default confidence threshold is 0.75. '{detected_text}' works only on macOS Catalina (10.15) or later. Note: this feature is not the same thing as Live Text in macOS Monterey, which osxphotos does not yet support.|
|{shell_quote}|Use in form '{shell_quote,TEMPLATE}'; quotes the rendered TEMPLATE value(s) for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.|
|{strip}|Use in form '{strip,TEMPLATE}'; strips whitespace from begining and end of rendered TEMPLATE value(s).|
|{format}|Use in form, '{format:TYPE:FORMAT,TEMPLATE}'; converts TEMPLATE value to TYPE then formats the value using Python string formatting codes specified by FORMAT; TYPE is one of: 'int', 'float', or 'str'. For example, '{format:float:.1f,{exiftool:EXIF:FocalLength}}' will format focal length to 1 decimal place (e.g. '100.0'). |
|{function}|Execute a python function from an external file and use return value as template substitution. Use in format: {function:file.py::function_name} where 'file.py' is the name of the python file and 'function_name' is the name of the function to call. The function will be passed the PhotoInfo object for the photo. See https://github.com/RhetTbull/osxphotos/blob/master/examples/template_function.py for an example of how to implement a template function.|
<!--[[[end]]] -->

### <a name="exiftoolExifTool">ExifTool</a>

osxphotos includes its own `exiftool` library that can be accessed via `osxphotos.exiftool`:

```python
>>> from osxphotos.exiftool import ExifTool
>>> exiftool = ExifTool("/Users/rhet/Downloads/test.jpeg")
>>> exifdict = exiftool.asdict()
>>> exifdict["EXIF:Make"]
'Canon'
>>> exiftool.setvalue("IPTC:Keywords","Keyword1")
True
>>> exiftool.asdict()["IPTC:Keywords"]
'Keyword1'
>>> exiftool.addvalues("IPTC:Keywords","Keyword2","Keyword3")
True
>>> exiftool.asdict()["IPTC:Keywords"]
['Keyword1', 'Keyword2', 'Keyword3']
```

`ExifTool(filepath, exiftool=None, large_file_support=True)`

* `filepath`: str, path to photo
* `exiftool`: str, optional path to `exiftool`; if not provided, will look for `exiftool` in the system path
* `large_file_support`: bool, if True, enables large file support in exiftool (`-api largefilesupport=1`)

#### ExifTool methods

* `asdict(tag_groups=True)`: returns all EXIF metadata found in the file as a dictionary in following form (Note: this shows just a subset of available metadata).  See [exiftool](https://exiftool.org/) documentation to understand which metadata keys are available. If `tag_groups` is True (default) dict keys are in form "GROUP:TAG", e.g. "IPTC:Keywords". If `tag_groups` is False, dict keys do not have group names, e.g. "Keywords".

```python
{'Composite:Aperture': 2.2,
 'Composite:GPSPosition': '-34.9188916666667 138.596861111111',
 'Composite:ImageSize': '2754 2754',
 'EXIF:CreateDate': '2017:06:20 17:18:56',
 'EXIF:LensMake': 'Apple',
 'EXIF:LensModel': 'iPhone 6s back camera 4.15mm f/2.2',
 'EXIF:Make': 'Apple',
 'XMP:Title': 'Elder Park',
}
```

* `json()`: returns same information as `asdict()` but as a serialized JSON string.

* `setvalue(tag, value)`: write to the EXIF data in the photo file. To delete a tag, use setvalue with value = `None`. For example:

```python
photo.exiftool.setvalue("XMP:Title", "Title of photo")
```

* `addvalues(tag, *values)`: Add one or more value(s) to tag.  For a tag that accepts multiple values, like "IPTC:Keywords", this will add the values as additional list values.  However, for tags which are not usually lists, such as "EXIF:ISO" this will literally add the new value to the old value which is probably not the desired effect.  Be sure you understand the behavior of the individual tag before using this. For example:

```python
photo.exiftool.addvalues("IPTC:Keywords", "vacation", "beach")
```

osxphotos.exiftool also provides an `ExifToolCaching` class which caches all metadata after the first call to `exiftool`. This can significantly speed up repeated access to the metadata but should only be used if you do not intend to modify the file's metadata.

[`PhotoInfo.exiftool`](#exiftool) returns an `ExifToolCaching` instance for the original image in the Photos library.

#### Implementation Note

`ExifTool()` runs `exiftool` as a subprocess using the `-stay_open True` flag to keep the process running in the background.  The subprocess will be cleaned up when your main script terminates.  `ExifTool()` uses a singleton pattern to ensure that only one instance of `exiftool` is created.  Multiple instances of `ExifTool()` will all use the same `exiftool` subprocess.

### <a name="photoexporter">PhotoExporter</a>

[PhotoInfo.export()](#photoinfo) provides a simple method to export a photo.  This method actually calls `PhotoExporter.export()` to do the export.  `PhotoExporter` provides many more options to configure the export and report results and this is what the osxphotos command line export tools uses.

#### `export(dest, filename=None, options: Optional[ExportOptions]=None) -> ExportResults`

Export a photo.

Args:

* dest: must be valid destination path or exception raised
* filename: (optional): name of exported picture; if not provided, will use current filename
* options (ExportOptions): optional ExportOptions instance

Returns: ExportResults instance

*Note*: to use dry run mode, you must set options.dry_run=True and also pass in memory version of export_db, and no-op fileutil (e.g. `ExportDBInMemory` and `FileUtilNoOp`) in options.export_db and options.fileutil respectively.

#### `ExportOptions`

Options class for exporting photos with `export`

Attributes:

* convert_to_jpeg (bool): if True, converts non-jpeg images to jpeg
* description_template (str): optional template string that will be rendered for use as photo description
* download_missing: (bool, default=False): if True will attempt to export photo via applescript interaction with Photos if missing (see also use_photokit, use_photos_export)
* dry_run: (bool, default=False): set to True to run in "dry run" mode
* edited: (bool, default=False): if True will export the edited version of the photo otherwise exports the original version
* exiftool_flags (list of str): optional list of flags to pass to exiftool when using exiftool option, e.g ["-m", "-F"]
* exiftool: (bool, default = False): if True, will use exiftool to write metadata to export file
* export_as_hardlink: (bool, default=False): if True, will hardlink files instead of copying them
* export_db: (ExportDB): instance of a class that conforms to ExportDB with methods for getting/setting data related to exported files to compare update state
* fileutil: (FileUtilABC): class that conforms to FileUtilABC with various file utilities
* ignore_date_modified (bool): for use with sidecar and exiftool; if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
* ignore_signature (bool, default=False): ignore file signature when used with update (look only at filename)
* increment (bool, default=True): if True, will increment file name until a non-existant name is found if overwrite=False and increment=False, export will fail if destination file already exists
* jpeg_ext (str): if set, will use this value for extension on jpegs converted to jpeg with convert_to_jpeg; if not set, uses jpeg; do not include the leading "."
* jpeg_quality (float in range 0.0 <= jpeg_quality <= 1.0): a value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
* keyword_template (list of str): list of template strings that will be rendered as used as keywords
* live_photo (bool, default=False): if True, will also export the associated .mov for live photos
* location (bool): if True, include location in exported metadata
* merge_exif_keywords (bool): if True, merged keywords found in file's exif data (requires exiftool)
* merge_exif_persons (bool): if True, merged persons found in file's exif data (requires exiftool)
* overwrite (bool, default=False): if True will overwrite files if they already exist
* persons (bool): if True, include persons in exported metadata
* preview_suffix (str): optional string to append to end of filename for preview images
* preview (bool): if True, also exports preview image
* raw_photo (bool, default=False): if True, will also export the associated RAW photo
* render_options (RenderOptions): optional osxphotos.phototemplate.RenderOptions instance to specify options for rendering templates
* replace_keywords (bool): if True, keyword_template replaces any keywords, otherwise it's additive
* sidecar_drop_ext (bool, default=False): if True, drops the photo's extension from sidecar filename (e.g. 'IMG_1234.json' instead of 'IMG_1234.JPG.json')
* sidecar: bit field (int): set to one or more of SIDECAR_XMP, SIDECAR_JSON, SIDECAR_EXIFTOOL
  * SIDECAR_JSON: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json; includes exiftool tag group names (e.g. `exiftool -G -j`)
  * SIDECAR_EXIFTOOL: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json; does not include exiftool tag group names (e.g. `exiftool -j`)
  * SIDECAR_XMP: if set will write an XMP sidecar with IPTC data sidecar filename will be dest/filename.xmp
* strip (bool): if True, strip whitespace from rendered templates
* timeout (int, default=120): timeout in seconds used with use_photos_export
* touch_file (bool, default=False): if True, sets file's modification time upon photo date
* update (bool, default=False): if True export will run in update mode, that is, it will not export the photo if the current version already exists in the destination
* use_albums_as_keywords (bool, default = False): if True, will include album names in keywords when exporting metadata with exiftool or sidecar
* use_persons_as_keywords (bool, default = False): if True, will include person names in keywords when exporting metadata with exiftool or sidecar
* use_photos_export (bool, default=False): if True will attempt to export photo via applescript interaction with Photos even if not missing (see also use_photokit, download_missing)
* use_photokit (bool, default=False): if True, will use photokit to export photos when use_photos_export is True
* verbose (Callable): optional callable function to use for printing verbose text during processing; if None (default), does not print output.
* tmpfile (str): optional path to use for temporary files

#### `ExportResults`

`PhotoExporter().export()` returns an instance of this class.

`ExportResults` has the following properties:

* datetime: date/time of export in ISO 8601 format
* exported: list of all exported files (A single call to export could export more than one file, e.g. original file, preview, live video, raw, etc.)
* new: list of new files exported when used with update=True
* updated: list of updated files when used with update=True
* skipped: list of skipped files when used with update=True
* exif_updated: list of updated files when used with update=True and exiftool
* touched: list of files touched during export (e.g. file date/time updated with touch_file=True)
* to_touch: Reserved for internal use of export
* converted_to_jpeg: list of files converted to jpeg when convert_to_jpeg=True
* metadata_changed: list of filenames that had metadata changes since last export
* sidecar_json_written: list of JSON sidecars written
* sidecar_json_skipped: list of JSON sidecars skipped when update=True
* sidecar_exiftool_written: list of exiftool sidecars written
* sidecar_exiftool_skipped: list of exiftool sidecars skipped when update=True
* sidecar_xmp_written: list of XMP sidecars written
* sidecar_xmp_skipped: list of XMP sidecars skipped when update=True
* missing: list of missing files
* error: list of tuples containing (filename, error) if error generated during export
* exiftool_warning: list of warnings generated by exiftool during export
* exiftool_error: list of errors generated by exiftool during export
* xattr_written: list of files with extended attributes written during export
* xattr_skipped: list of files where extended attributes were skipped when update=True
* deleted_files: reserved for use by osxphotos CLI
* deleted_directories: reserved for use by osxphotos CLI
* exported_album: reserved for use by osxphotos CLI
* skipped_album: reserved for use by osxphotos CLI
* missing_album: reserved for use by osxphotos CLI

### <a name="textdetection">Text Detection</a>

The [PhotoInfo.detected_text()](#detected_text_method) and the `{detected_text}` template will perform text detection on the photos in your library. Text detection is a slow process so to avoid unnecessary re-processing of photos, osxphotos will cache the results of the text detection process as an extended attribute on the photo image file.  Extended attributes do not modify the actual file.  The extended attribute is named `osxphotos.metadata:detected_text` and can be viewed using the built-in [xattr](https://ss64.com/osx/xattr.html) command or my [osxmetadata](https://github.com/RhetTbull/osxmetadata) tool.  If you want to remove the cached attribute, you can do so with `xattr` as follows:

`find ~/Pictures/Photos\ Library.photoslibrary | xargs -I{} xattr -c osxphotos.metadata:detected_text '{}'`

### Utility Functions

The following functions are located in osxphotos.utils

#### `get_system_library_path()`

**MacOS 10.15 Only** Returns path to System Photo Library as string.  On MacOS version < 10.15, returns None.

#### `get_last_library_path()`

Returns path to last opened Photo Library as string.  

#### `list_photo_libraries()`

Returns list of Photos libraries found on the system.  **Note**: On MacOS 10.15, this appears to list all libraries. On older systems, it may not find some libraries if they are not located in ~/Pictures.  Provided for convenience but do not rely on this to find all libraries on the system.

## Additional Examples

```python
import osxphotos

def main():

    photosdb = osxphotos.PhotosDB("/Users/smith/Pictures/Photos Library.photoslibrary")
    print(f"db file = {photosdb.db_path}")
    print(f"db version = {photosdb.db_version}")

    print(photosdb.keywords)
    print(photosdb.persons)
    print(photosdb.album_names)

    print(photosdb.keywords_as_dict)
    print(photosdb.persons_as_dict)
    print(photosdb.albums_as_dict)

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
            p.uuid,
            p.filename,
            p.date,
            p.description,
            p.title,
            p.keywords,
            p.albums,
            p.persons,
            p.path,
            p.ismissing,
            p.hasadjustments,
        )


if __name__ == "__main__":
    main()
```
