# OSXPhotos

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is osxphotos?

OSXPhotos provides the ability to interact with and query Apple's Photos.app library database on MacOS. Using this module you can query the Photos database for information about the photos stored in a Photos library on your Mac--for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc.

**NOTE**: OSXPhotos currently only supports image files -- e.g. it does not handle movies.

## Supported operating systems

Only works on MacOS (aka Mac OS X). Tested on MacOS 10.12.6 / Photos 2.0, 10.13.6 / Photos 3.0 and MacOS 10.14.5, 10.14.6 / Photos 4.0. Requires python >= 3.6

**NOTE**: Alpha support for Mac OS 10.15.0 / Photos 5.0.  Photos 5.0 uses a new database format which required rewrite of much of the code for this module.  If you find bugs, please open an [issue](https://github.com/RhetTbull/osxphotos/issues/).

This module will read Photos databases for any supported version on any supported OS version.  E.g. you can read a database created with Photos 4.0 on MacOS 10.14 on a machine running MacOS 10.12


## Installation instructions

osxmetadata uses setuptools, thus simply run:

	python setup.py install

## Command Line Usage

This module will install a command line utility called `osxphotos` that allows you to query the Photos database.

If you only care about the command line tool, I recommend installing with [pipx](https://github.com/pipxproject/pipx)

After installing pipx:
`pipx install osxphotos`

```
Usage: osxphotos [OPTIONS] COMMAND [ARGS]...

Options:
  --db <Photos database path>  Specify database file
  --json                       Print output in JSON format
  -v, --version                Show the version and exit.
  -h, --help                   Show this message and exit.

Commands:
  albums    print out albums found in the Photos library
  dump      print list of all photos & associated info from the Photos...
  help      print help; for help on commands: help <command>
  info      print out descriptive info of the Photos library database
  keywords  print out keywords found in the Photos library
  persons   print out persons (faces) found in the Photos library
  query     query the Photos database using 1 or more search options; if...
```

To get help on a specific command, use `osxphotos help <command_name>`

Example: `osxphotos help query`

```
Usage: osxphotos help [OPTIONS]

  query the Photos database using 1 or more search options;  if more than
  one option is provided, they are treated as "AND"  (e.g. search for photos
  matching all options)

Options:
  --keyword TEXT      search for keyword(s)
  --person TEXT       search for person(s)
  --album TEXT        search for album(s)
  --uuid TEXT         search for UUID(s)
  --name TEXT         search for TEXT in name of photo
  --no-name           search for photos with no name
  --description TEXT  search for TEXT in description of photo
  --no-description    search for photos with no description
  -i, --ignore-case   case insensitive search for name or description. Does
                      not apply to keyword, person, or album
  --favorite          search for photos marked favorite
  --not-favorite      search for photos not marked favorite
  --hidden            search for photos marked hidden
  --not-hidden        search for photos not marked hidden
  --missing           search for photos missing from disk
  --not-missing       search for photos present on disk (e.g. not missing)
  --json              Print output in JSON format
  -h, --help          Show this message and exit.
```

Example: find all photos with keyword "Kids" and output results to json file named results.json:

`osxphotos query --keyword Kids --json >results.json`

## Example uses of the module 

```python
import osxphotos

def main():
    photosdb = osxphotos.PhotosDB()
    print(photosdb.keywords())
    print(photosdb.persons())
    print(photosdb.albums())

    print(photosdb.keywords_as_dict())
    print(photosdb.persons_as_dict())
    print(photosdb.albums_as_dict())

    # find all photos with Keyword = Foo and containing John Smith
    photos = photosdb.photos(keywords=["Foo"],persons=["John Smith"])

    # find all photos that include Alice Smith but do not contain the keyword Bar
    photos = [p for p in photosdb.photos(persons=["Alice Smith"]) 
                if p not in photosdb.photos(keywords=["Bar"]) ]
    for p in photos:
        print(
            p.uuid,
            p.filename(),
            p.original_filename(),
            p.date(),
            p.description(),
            p.name(),
            p.keywords(),
            p.albums(),
            p.persons(),
            p.path(),
        )

if __name__ == "__main__":
    main()
```

## Module Interface

### Utility Functions

#### ```get_system_library_path()```

**MacOS 10.15 Only** Returns path to System Photo Library as string.  On MacOS version < 10.15, raises Exception.

#### ```get_last_library_path()```

Returns path to last opened Photo Library as string.  

#### ```list_photo_libraries()```

Returns list of Photos libraries found in the user's Pictures folder.

### PhotosDB

#### Open the default Photos library

```python
osxphotos.PhotosDB([dbfile="path to database file"])
```

Opens the Photos library database and returns a PhotosDB object.  Optionally, pass the path to a specific database file.  If `dbfile` is not included, will open the default (last opened) Photos database.

**Note**: this will open the last library that was opened in Photos. This is not necessarily the System Photos Library.  If you have more than one Photos library, you can select which to open by holding down Option key while opening Photos.

```python
import osxphotos

photosdb = osxphotos.PhotosDB()
```

Returns a PhotosDB object. 

#### Open a specific Photos library
```python
import osxphotos

photosdb = osxphotos.PhotosDB(dbfile="/Users/smith/Pictures/Test.photoslibrary/database/photos.db")
```

Pass the fully qualified path to the specific Photos database you want to open. The database is called photos.db and resides in the database folder in your Photos library

#### ```keywords```
```python
# assumes photosdb is a PhotosDB object (see above)
keywords = photosdb.keywords()
```

Returns a list of the keywords found in the Photos library

#### ```albums```
```python
# assumes photosdb is a PhotosDB object (see above)
albums = photosdb.albums()
```

Returns a list of the albums found in the Photos library.  

**Note**: In Photos 5.0 (MacOS 10.15/Catalina), It is possible to have more than one album with the same name in Photos.  Albums with duplicate names are treated as a single album and the photos in each are combined.  For example, if you have two albums named "Wedding" and each has 2 photos, osxphotos will treat this as a single album named "Wedding" with 4 photos in it.

#### ```persons```
```python
# assumes photosdb is a PhotosDB object (see above)
persons = photosdb.persons()
```

Returns a list of the persons (faces) found in the Photos library

#### ```keywords_as_dict```
```python
# assumes photosdb is a PhotosDB object (see above)
keyword_dict = photosdb.keywords_as_dict()
```

Returns a dictionary of keywords found in the Photos library where key is the keyword and value is the count of how many times that keyword appears in the library (ie. how many photos are tagged with the keyword).  Resulting dictionary is in reverse sorted order (e.g. keyword with the highest count is first).

#### ```persons_as_dict```
```python
# assumes photosdb is a PhotosDB object (see above)
persons_dict = photosdb.persons_as_dict()
```

Returns a dictionary of persons (faces) found in the Photos library where key is the person name and value is the count of how many times that person appears in the library (ie. how many photos are tagged with the person).  Resulting dictionary is in reverse sorted order (e.g. person who appears in the most photos is listed first).

#### ```albums_as_dict```
```python
# assumes photosdb is a PhotosDB object (see above)
albums_dict = photosdb.albums_as_dict()
```

Returns a dictionary of albums found in the Photos library where key is the album name and value is the count of how many photos are in the album.  Resulting dictionary is in reverse sorted order (e.g. album with the most photos is listed first).  

**Note**: In Photos 5.0 (MacOS 10.15/Catalina), It is possible to have more than one album with the same name in Photos.  Albums with duplicate names are treated as a single album and the photos in each are combined.  For example, if you have two albums named "Wedding" and each has 2 photos, osxphotos will treat this as a single album named "Wedding" with 4 photos in it.

#### ```get_library_path```
```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.get_photos_library_path()
```

Returns the path to the Photos library as a string

#### ```get_db_path```
```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.get_db_path()
```

Returns the path to the Photos database PhotosDB was initialized with

#### ```get_db_version```
```python
# assumes photosdb is a PhotosDB object (see above)
photosdb.get_db_version()
```

Returns the version number for Photos library database.  You likely won't need this but it's provided in case needed for debugging. PhotosDB will print a warning to `sys.stderr` if you open a database version that has not been tested. 


#### ```photos```
```python
# assumes photosdb is a PhotosDB object (see above)
photos = photosdb.photos([keywords=['keyword',]], [uuid=['uuid',]], [persons=['person',]], [albums=['album',]])
```

Returns a list of PhotoInfo objects.  Each PhotoInfo object represents a photo in the Photos Libary.

If called with no parameters, returns a list of every photo in the Photos library. 

May be called with one or more of the following parameters:
```python
photos = photosdb.photos(
    keywords = [],
    uuid = [],
    persons = [],
    albums = []
)
```

- ```keywords```: list of one or more keywords.  Returns only photos containing the keyword(s).  If more than one keyword is provided finds photos matching any of the keywords (e.g. treated as "or")
- ```uuid```: list of one or more uuids.  Returns only photos whos UUID matches.  **Note**: The UUID is the universally unique identifier that the Photos database uses to identify each photo.  You shouldn't normally need to use this but it is a way to access a specific photo if you know the UUID.  If more than more uuid is provided, returns photos that match any of the uuids (e.g. treated as "or")
- ```persons```: list of one or more persons. Returns only photos containing the person(s).  If more than one person provided, returns photos that match any of the persons (e.g. treated as "or")
- ```albums```: list of one or more album names.  Returns only photos contained in the album(s). If more than one album name is provided, returns photos contained in any of the albums (.e.g. treated as "or")

If more than one of these parameters is provided, they are treated as "and" criteria. E.g.

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

### PhotoInfo 
PhotosDB.photos() returns a list of PhotoInfo objects.  Each PhotoInfo object represents a single photo in the Photos library.

#### `uuid()`
Returns the universally unique identifier (uuid) of the photo.  This is how Photos keeps track of individual photos within the database.

#### `filename()`
Returns the current filename of the photo on disk.  See also `original_filename()`

#### `original_filename()`
Returns the original filename of the photo when it was imported to Photos.  **Note**: Photos 5.0+ renames the photo when it adds the file to the library using UUID.  See also `filename()`

#### `date()`
Returns the date of the photo as a datetime.datetime object

#### `description()`
Returns the description of the photo

#### `name()`
Returns the name (or the title as Photos calls it) of the photo

#### `keywords()`
Returns a list of keywords (e.g. tags) applied to the photo

#### `albums()`
Returns a list of albums the photo is contained in

#### `persons()`
Returns a list of the names of the persons in the photo

#### `path()`
Returns the absolute path to the photo on disk as a string.  **Note**: this returns the path to the *original* unedited file (see `hasadjustments()`).  If the file is missing on disk, path=`None` (see `ismissing()`)

#### `path_edited()`
Returns the absolute path to the edited photo on disk as a string.  If the photo has not been edited, returns `None`.  See also `path()` and `hasadjustments()`.  

#### `ismissing()`
Returns `True` if the original image file is missing on disk, otherwise `False`.  This can occur if the file has been uploaded to iCloud but not yet downloaded to the local library or if the file was deleted or imported from a disk that has been unmounted. **Note**: this status is set by Photos and osxphotos does not verify that the file path returned by `path()` actually exists.  It merely reports what Photos has stored in the library database. 

#### `hasadjustments()`
Returns `True` if the picture has been edited, otherwise `False`

#### `external_edit()`
Returns `True` if the picture was edited in an external editor (outside Photos.app), otherwise `False`

#### `favorite()`
Returns `True` if the picture has been marked as a favorite, otherwise `False`

#### `hidden()`
Returns `True` if the picture has been marked as hidden, otherwise `False`

#### `location()`
Returns latitude and longitude as a tuple of floats (latitude, longitude).  If location is not set, latitude and longitude are returned as `None`

#### `to_json()`
Returns a JSON representation of all photo info 

Examples:

```python
# assumes photosdb is a PhotosDB object (see above)
photos=photosdb.photos()
for p in photos:
    print(
        p.uuid(),
        p.filename(),
        p.original_filename(),
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
```

## History

This project started as a command line utility, `photosmeta`, available at [photosmeta](https://github.com/RhetTbull/photosmeta) This module converts the photosmeta Photos library query functionality into a module.  


## Implementation Notes

This module works by creating a copy of the sqlite3 database that Photos uses to store data about the Photos library. The class PhotosDB then queries this database to extract information about the photos such as persons (faces identified in the photos), albums, keywords, etc.  

If Apple changes the database format this will likely break.

Apple does provide a framework ([PhotoKit](https://developer.apple.com/documentation/photokit?language=objc)) for querying the user's Photos library and I attempted to create the funcationality in this module using this framework but unfortunately PhotoKit does not provide access to much of the needed metadata (such as Faces/Persons).  While copying the sqlite file is a bit kludgy, it allows osxphotos to provide access to all available metadata.

## Dependencies
- [PyObjC](https://pythonhosted.org/pyobjc/)
- [PyYAML](https://pypi.org/project/PyYAML/)
- [Click](https://pypi.org/project/click/)

## Acknowledgements
This project was inspired by photo-export by Patrick Fältström see: (https://github.com/patrikhson/photo-export) Copyright (c) 2015 Patrik Fältström paf@frobbit.se

To interact with the Photos app, I use [py-applescript]( https://github.com/rdhyee/py-applescript) by "Raymond Yee / rdhyee".  Rather than import this module, I included the entire module
(which is published as public domain code) in a private module to prevent ambiguity with
other applescript modules on PyPi.  py-applescript uses a native bridge via PyObjC and
is very fast compared to the other osascript based modules.
