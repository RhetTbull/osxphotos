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

Works on macOS and linux. Some features are compatible only with macOS.

This package will read Photos databases for any supported version on any supported macOS version.  
E.g. you can read a database created with Photos 5.0 on MacOS 10.15 on a machine running macOS 10.12 and vice versa.

Requires python >= ``3.9``. 

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

  [[[cog
    from osxphotos.cli import cli_main
    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--help"])
    help = result.output.replace("Usage: cli-main", "Usage: osxphotos")
    cog.out(
        "{}\n".format(help)
    )
  ]]]
  [[[end]]]