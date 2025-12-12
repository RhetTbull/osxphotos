.. role:: raw-html-m2r(raw)
   :format: html


osxphotos
=========

What is osxphotos?
------------------

OSXPhotos provides both the ability to interact with and query Apple's Photos.app library on macOS directly from your python code
as well as a very flexible command line interface (CLI) app for exporting photos.
You can query the Photos library database -- for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc.
You can also easily export both the original and edited photos.

Supported operating systems
---------------------------

Only works on macOS (aka Mac OS X). Tested on macOS Sierra (10.12.6) through macOS Sequoia (15.7.2).
Most features work on macOS 26.1 but OSXPhotos does yet fully support 26.x. Notably OSXPhotos cannot read
shared albums on macOS 26.x.

This package will read Photos databases for any supported version on any supported macOS version.
E.g. you can read a database created with Photos 5.0 on MacOS 10.15 on a machine running macOS 10.12 and vice versa.

Requires python >= ``3.10``.

Installation
------------

The recommended way to install ``osxphotos`` is via the `uv <https://github.com/astral-sh/uv>`_ python package manager tool.

Installation using ``uv``
-------------------------

* Open ``Terminal`` (search for ``Terminal`` in Spotlight or look in ``Applications/Utilities``)
* Install ``uv`` by running the following command in Terminal:

.. code-block:: bash

    curl -LsSf https://astral.sh/uv/install.sh | sh

If you previously installed ``uv``, upgrade to the latest version:

.. code-block:: bash

    uv self update

* Type the following into Terminal:

.. code-block:: bash

    uv tool install --python 3.12 osxphotos

* Now you should be able to run ``osxphotos`` by typing: ``osxphotos``

Once you've installed osxphotos with ``uv``, to upgrade to the latest version:

.. code-block:: bash

    uv tool upgrade osxphotos

If you want to try ``osxphotos`` without installing it, you can run ``uv tool run --python 3.12 osxphotos`` or ``uvx --python 3.12 osxphotos``.

Note: If installing on an older version of macOS and you encounter issues installing with uv, try installing python 3.12 from `python.org <https://www.python.org/downloads/>`_ then running uv to install osxphotos.

Installation using pip
----------------------

You can install ``osxphotos`` directly from `pypi <https://pypi.org/project/osxphotos/>`_:

.. code-block:: bash

    python3 -m pip install osxphotos

Once you've installed osxphotos with pip, to upgrade to the latest version:

.. code-block:: bash

    python3 -m pip install --upgrade osxphotos

Installation via MacPorts
-------------------------

If you use the `MacPorts <https://www.macports.org>`_ package manager on a Mac:

.. code-block:: bash

    sudo port install osxphotos

Installation on Linux
---------------------

At least one of the Linux-specific python packages normally installed on Linux may cause an error during installation with ``pip`` or ``pipx``. If you encounter an error similar to: ``pip._vendor.packaging.version.InvalidVersion: Invalid version: '6.5.0-1022-generic``, you should still be able to install osxphotos by creating and activating a virtual environment:

.. code-block:: bash

    python3 -m venv .venv-osxphotos
    source .venv-osxphotos/bin/activate
    python3 -m pip install osxphotos

To use osxphotos you will need to ensure the venv is activated using ``source .venv-osxphotos/bin/activate``.

You may name the virtual environment anything you want; ``.venv-osxphotos`` is used in this example to make it clear the virtual environment is used by osxphotos and to avoid conflict with other virtual environments which, by convention, are often named ``.venv`` or ``venv``.


Command Line Usage
------------------

This package will install a command line utility called ``osxphotos`` that allows you to query the Photos database and export photos.
Alternatively, you can also run the command line utility like this: ``python3 -m osxphotos``

.. code-block::

   Usage: osxphotos [OPTIONS] COMMAND [ARGS]...

     OSXPhotos: the multi-tool for your Photos library.

     To get help on a specific command, use "osxphotos COMMAND --help" or
     "osxphotos help COMMAND"; for example, "osxphotos help export".

     To search help for a specific topic within a command, run "osxphotos help
     COMMAND TOPIC"; for example, "osxphotos help export keyword" to get help
     related to keywords when using the export command.

     To see the full documentation in your browser, run "osxphotos docs".

     Some advanced commands are hidden by default. To see all commands, run
     "OSXPHOTOS_SHOW_HIDDEN=1 osxphotos help". Some commands also have hidden
     options. These can be seen by running "OSXPHOTOS_SHOW_HIDDEN=1 osxphotos
     help COMMAND".

   Options:
     -v, --version  Show the version and exit.
     -h, --help     Show this message and exit.

   Commands:
     about          Print information about osxphotos including license.
     add-locations  Add missing location data to photos in Photos.app using...
     albums         Print out albums found in the Photos library.
     batch-edit     Batch edit photo metadata such as title, description,...
     compare        Compare two Photos libraries to find differences
     docs           Open osxphotos documentation in your browser.
     dump           Print list of all photos & associated info from the...
     exiftool       Run exiftool on previously exported files to update...
     export         Export photos from the Photos database.
     exportdb       Utilities for working with the osxphotos export database
     help           Print help; for help on commands: help <command>.
     import         Import photos and videos into Photos.
     info           Print out descriptive info of the Photos library database.
     inspect        Interactively inspect photos selected in Photos.
     install        Install Python packages into the same environment as...
     keywords       Print out keywords found in the Photos library.
     labels         Print out image classification labels found in the...
     list           Print list of Photos libraries found on the system.
     orphans        Find orphaned photos in a Photos library
     persons        Print out persons (faces) found in the Photos library.
     places         Print out places found in the Photos library.
     push-exif      Write photo metadata to original files in the Photos...
     query          Query the Photos database using 1 or more search...
     repl           Run interactive osxphotos REPL shell (useful for...
     run            Run a python file using same environment as osxphotos.
     show           Show photo, album, or folder in Photos from UUID_OR_NAME
     sync           Sync metadata and albums between Photos libraries.
     template       Interactively render templates for selected photo.
     theme          Manage osxphotos color themes.
     timewarp       Adjust date/time/timezone of photos in Apple Photos.
     tutorial       Display osxphotos tutorial.
     uninstall      Uninstall Python packages from the osxphotos environment
     uuid           Print out unique IDs (UUID) of photos selected in Photos
     version        Check for new version of osxphotos.

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
