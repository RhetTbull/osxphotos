.. role:: raw-html-m2r(raw)
   :format: html


OSXPhotos
=========

What is osxphotos?
------------------

OSXPhotos provides both the ability to interact with and query Apple's Photos.app library on macOS directly from your python code 
as well as a very flexible command line interface (CLI) app for exporting photos. 
You can query the Photos library database -- for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc. 
You can also easily export both the original and edited photos. 

Supported operating systems
---------------------------

Only works on macOS (aka Mac OS X). Tested on macOS Sierra (10.12.6) through macOS Big Sur (11.3).

If you have access to macOS 12 / Monterey beta and would like to help ensure osxphotos is compatible, please contact me via GitHub.

This package will read Photos databases for any supported version on any supported macOS version.  
E.g. you can read a database created with Photos 5.0 on MacOS 10.15 on a machine running macOS 10.12 and vice versa.

Requires python >= ``3.7``. 

Installation
------------

If you are new to python and just want to use the command line application, I recommend you to install using pipx. See other advanced options below. 

Installation using pipx
^^^^^^^^^^^^^^^^^^^^^^^

If you aren't familiar with installing python applications, I recommend you install ``osxphotos`` with `pipx <https://github.com/pipxproject/pipx>`_. If you use ``pipx``\ , you will not need to create a virtual environment as ``pipx`` takes care of this. The easiest way to do this on a Mac is to use `homebrew <https://brew.sh/>`_\ :


* Open ``Terminal`` (search for ``Terminal`` in Spotlight or look in ``Applications/Utilities``\ )
* Install ``homebrew`` according to instructions at `https://brew.sh/ <https://brew.sh/>`_
* Type the following into Terminal: ``brew install pipx``
* Then type this: ``pipx install osxphotos``
* Now you should be able to run ``osxphotos`` by typing: ``osxphotos``

Installation using pip
^^^^^^^^^^^^^^^^^^^^^^

You can also install directly from `pypi <https://pypi.org/project/osxphotos/>`_\ :

.. code-block::

   pip install osxphotos


Installation from git repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OSXPhotos uses setuptools, thus simply run:

.. code-block::

   git clone https://github.com/RhetTbull/osxphotos.git
   cd osxphotos
   python3 setup.py install


I recommend you create a `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_ before installing osxphotos.

**WARNING** The git repo for this project is very large (> 1GB) because it contains multiple Photos libraries used for testing 
on different versions of macOS.  If you just want to use the osxphotos package in your own code, 
I recommend you install the latest version from `PyPI <https://pypi.org/project/osxphotos/>`_ which does not include all the test 
libraries. If you just want to use the command line utility, you can download a pre-built executable of the latest 
`release <https://github.com/RhetTbull/osxphotos/releases>`_ or you can install via ``pip`` which also installs the command line app.  
If you aren't comfortable with running python on your Mac, start with the pre-built executable or ``pipx`` as described above.

Command Line Usage
------------------

This package will install a command line utility called ``osxphotos`` that allows you to query the Photos database and export photos.  
Alternatively, you can also run the command line utility like this: ``python3 -m osxphotos``

.. code-block::

   > osxphotos
   Usage: osxphotos [OPTIONS] COMMAND [ARGS]...

   Options:
     --db <Photos database path>  Specify Photos database path. Path to Photos
                                  library/database can be specified using either
                                  --db or directly as PHOTOS_LIBRARY positional
                                  argument. If neither --db or PHOTOS_LIBRARY
                                  provided, will attempt to find the library to
                                  use in the following order: 1. last opened
                                  library, 2. system library, 3.
                                  ~/Pictures/Photos Library.photoslibrary
     --json                       Print output in JSON format.
     -v, --version                Show the version and exit.
     -h, --help                   Show this message and exit.

   Commands:
     about     Print information about osxphotos including license.
     albums    Print out albums found in the Photos library.
     dump      Print list of all photos & associated info from the Photos...
     export    Export photos from the Photos database.
     help      Print help; for help on commands: help <command>.
     info      Print out descriptive info of the Photos library database.
     keywords  Print out keywords found in the Photos library.
     labels    Print out image classification labels found in the Photos...
     list      Print list of Photos libraries found on the system.
     persons   Print out persons (faces) found in the Photos library.
     places    Print out places found in the Photos library.
     query     Query the Photos database using 1 or more search options; if...
     repl      Run interactive osxphotos shell
     tutorial  Display osxphotos tutorial.

To get help on a specific command, use ``osxphotos help <command_name>``

Command line examples
^^^^^^^^^^^^^^^^^^^^^

export all photos to ~/Desktop/export group in folders by date created
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos export --export-by-date ~/Pictures/Photos\ Library.photoslibrary ~/Desktop/export``

**Note**\ : Photos library/database path can also be specified using ``--db`` option:

``osxphotos export --export-by-date --db ~/Pictures/Photos\ Library.photoslibrary ~/Desktop/export``

find all photos with keyword "Kids" and output results to json file named results.json:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos query --keyword Kids --json ~/Pictures/Photos\ Library.photoslibrary >results.json``

export photos to file structure based on 4-digit year and full name of month of photo's creation date:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos export ~/Desktop/export --directory "{created.year}/{created.month}"``

(by default, it will attempt to use the system library)

export photos to file structure based on 4-digit year of photo's creation date and add keywords for media type and labels (labels are only awailable on Photos 5 and higher):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos export ~/Desktop/export --directory "{created.year}" --keyword-template "{label}" --keyword-template "{media_type}"`` 

export default library using 'country name/year' as output directory (but use "NoCountry/year" if country not specified), add persons, album names, and year as keywords, write exif metadata to files when exporting, update only changed files, print verbose ouput
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos export ~/Desktop/export --directory "{place.name.country,NoCountry}/{created.year}"  --person-keyword --album-keyword --keyword-template "{created.year}" --exiftool --update --verbose``

find all videos larger than 200MB and add them to Photos album "Big Videos" creating the album if necessary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``osxphotos query --only-movies --min-size 200MB --add-to-album "Big Videos"``

Example uses of the package
---------------------------

.. code-block:: python

   """ Simple usage of the package """
   import osxphotos

   def main():
       photosdb = osxphotos.PhotosDB()
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

.. code-block:: python

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

Package Interface
-----------------

Reference full documentation on `GitHub <https://github.com/RhetTbull/osxphotos/blob/master/README.md>`_
