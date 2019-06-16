[OSXPhotos](https://github.com/RhetTbull/osxphotos)
========

What is osxphotos?
-----------------

OSXPhotos provides the ability to manipulate the Apple's Photos app database on Mac OS X.  

Supported operating systems
---------------------------

Only works on Mac OS X.  Only tested on Mac OS 10.13 and Photos 3.0.  It's quote possible the Photos database schema changed in later versions of Mac OS X and/or the Photos app.

Installation instructions
-------------------------

osxmetadata uses setuptools, thus simply run:

	python setup.py install

Command Line Usage
------------------

This project started as a command line utility, `photosmeta`, available at [photosmeta](https://github.com/RhetTbull/photosmeta) This module converts the photosmeta functionality into a module.  Eventually, I plan to rewrite photosmeta using this module and include it as a command line script in this module.

Example uses of the module
--------------------------

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

Usage Notes
-----------

This module is very kludgy.  It works by creating a copy of the sqlite3 database that Photos uses to store data about the Photos library. The class PhotosDB then queries this database to extract information about the photos such as persons (faces identified in the photos), albums, keywords, etc.  

If Apple changes the database format this will break.  

The sqlite3 database used by Photos uses write ahead logging that is updated asynchronously in the background by a Photos helper service.  Sometimes the update takes a long time meaning the latest changes made in Photos (e.g. add a keyword) will not show up in the database for sometime.  I know of no way around this.

Dependencies
------------
[PyObjC](https://pythonhosted.org/pyobjc/)

Acknowledgements
----------------
This code was inspired by photo-export by Patrick Fältström see: (https://github.com/patrikhson/photo-export) Copyright (c) 2015 Patrik Fältström paf@frobbit.se

To interact with the Photos app, I use [py-applescript]( https://github.com/rdhyee/py-applescript) by "Raymond Yee / rdhyee".  Rather than import this module, I included the entire module
(which is published as public domain code) in a private module to prevent ambiguity with
other applescript modules on PyPi.  py-applescript uses a native bridge via PyObjC and
is very fast compared to the other osascript based modules.
