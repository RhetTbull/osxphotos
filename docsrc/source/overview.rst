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

Installation using pip
---------------------

You can install ``osxphotos`` directly from `pypi <https://pypi.org/project/osxphotos/>`_:

.. code-block:: bash

    python3 -m pip install osxphotos

Once you've installed osxphotos with pip, to upgrade to the latest version:

.. code-block:: bash

    python3 -m pip install --upgrade osxphotos

Installation via MacPorts
------------------------

If you use the `MacPorts <https://www.macports.org>`_ package manager on a Mac:

.. code-block:: bash

    sudo port install osxphotos

Installation on Linux
--------------------

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

.. code-block:: TXT

