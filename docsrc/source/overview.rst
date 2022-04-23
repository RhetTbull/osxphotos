OSXPhotos
=========

What is OSXPhotos?
------------------

OSXPhotos provides both the ability to interact with and query Apple's Photos.app library on macOS directly from your python code 
as well as a very flexible command line interface (CLI) app for exporting photos. 
You can query the Photos library database -- for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc. 
You can also easily export both the original and edited photos. 

Supported operating systems
---------------------------

Only works on macOS (aka Mac OS X). Tested on macOS Sierra (10.12.6) through macOS Monterey (12.3).

This package will read Photos databases for any supported version on any supported macOS version.  
E.g. you can read a database created with Photos 5.0 on MacOS 10.15 on a machine running macOS 10.12 and vice versa.

Requires python >= ``3.8``. 

Installation
------------

The recommended way of installing ``osxphotos`` is with `pipx <https://github.com/pipxproject/pipx>`_.  The easiest way to do this on a Mac is to use `homebrew <https://brew.sh/>`_\ :


* Open ``Terminal`` (search for ``Terminal`` in Spotlight or look in ``Applications/Utilities``\ )
* Install ``homebrew`` according to instructions at `https://brew.sh/ <https://brew.sh/>`_
* Type the following into Terminal: ``brew install pipx``
* Then type this: ``pipx install osxphotos``
* Now you should be able to run ``osxphotos`` by typing: ``osxphotos``

Command Line Usage
------------------

This package will install a command line utility called ``osxphotos`` that allows you to query the Photos database and export photos.  

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
     --json                      Print output in JSON format.
     -v, --version                Show the version and exit.
     -h, --help                   Show this message and exit.

   Commands:
     about      Print information about osxphotos including license.
     albums     Print out albums found in the Photos library.
     diff       Compare two Photos databases and print out differences
     docs       Open osxphotos documentation in your browser.
     dump       Print list of all photos & associated info from the Photos...
     export     Export photos from the Photos database.
     help       Print help; for help on commands: help <command>.
     info       Print out descriptive info of the Photos library database.
     install    Install Python packages into the same environment as osxphotos
     keywords   Print out keywords found in the Photos library.
     labels     Print out image classification labels found in the Photos...
     list       Print list of Photos libraries found on the system.
     persons    Print out persons (faces) found in the Photos library.
     places     Print out places found in the Photos library.
     query      Query the Photos database using 1 or more search options; if...
     repl       Run interactive osxphotos REPL shell (useful for debugging,...
     run        Run a python file using same environment as osxphotos
     snap       Create snapshot of Photos database to use with diff command
     theme      Manage osxphotos color themes.
     tutorial   Display osxphotos tutorial.
     uninstall  Uninstall Python packages from the osxphotos environment
     uuid       Print out unique IDs (UUID) of photos selected in Photos
     version    Check for new version of osxphotos.

To get help on a specific command, use ``osxphotos help <command_name>``
