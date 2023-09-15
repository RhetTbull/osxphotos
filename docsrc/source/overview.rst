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

.. code-block:: TXT

  Usage: osxphotos [OPTIONS] COMMAND [ARGS]...

    osxphotos: the multi-tool for your Photos library

  Options:
    -v, --version  Show the version and exit.
    -h, --help     Show this message and exit.

  Commands:
    about          Print information about osxphotos including license.
    add-locations  Add missing location data to photos in Photos.app using...
    albums         Print out albums found in the Photos library.
    batch-edit     Batch edit photo metadata such as title, description,...
    diff           Compare two Photos databases and print out differences
    docs           Open osxphotos documentation in your browser.
    dump           Print list of all photos & associated info from the Photos...
    exiftool       Run exiftool on previously exported files to update metadata.
    export         Export photos from the Photos database.
    exportdb       Utilities for working with the osxphotos export database
    help           Print help; for help on commands: help <command>.
    import         Import photos and videos into Photos.
    info           Print out descriptive info of the Photos library database.
    inspect        Interactively inspect photos selected in Photos.
    install        Install Python packages into the same environment as...
    keywords       Print out keywords found in the Photos library.
    labels         Print out image classification labels found in the Photos...
    list           Print list of Photos libraries found on the system.
    orphans        Find orphaned photos in a Photos library
    persons        Print out persons (faces) found in the Photos library.
    places         Print out places found in the Photos library.
    push-exif      Write photo metadata to original files in the Photos library
    query          Query the Photos database using 1 or more search options;...
    repl           Run interactive osxphotos REPL shell (useful for...
    run            Run a python file using same environment as osxphotos.
    show           Show photo, album, or folder in Photos from UUID_OR_NAME
    snap           Create snapshot of Photos database to use with diff command
    sync           Sync metadata and albums between Photos libraries.
    template       Interactively render templates for selected photo.
    theme          Manage osxphotos color themes.
    timewarp       Adjust date/time/timezone of photos in Apple Photos.
    tutorial       Display osxphotos tutorial.
    uninstall      Uninstall Python packages from the osxphotos environment
    uuid           Print out unique IDs (UUID) of photos selected in Photos
    version        Check for new version of osxphotos.

