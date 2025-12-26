# OSXPhotos

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![tests](https://github.com/RhetTbull/osxphotos/workflows/Tests/badge.svg)](https://github.com/RhetTbull/osxphotos/workflows/Tests/badge.svg)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/osxphotos)
[![Downloads](https://static.pepy.tech/personalized-badge/osxphotos?period=month&units=international_system&left_color=black&right_color=brightgreen&left_text=downloads/month)](https://pepy.tech/project/osxphotos)
[![subreddit](https://img.shields.io/reddit/subreddit-subscribers/osxphotos?style=social)](https://www.reddit.com/r/osxphotos/)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-105-orange.svg?style=flat)](#contributors)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

OSXPhotos provides the ability to interact with and query Apple's Photos.app library on macOS and Linux. You can query the Photos library database — for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc. You can also easily export both the original and edited photos. OSXPhotos also works with iPhoto libraries though some features are available only for Photos.

<p align="center"><img src="docs/screencast/demo.gif?raw=true" width="713" height="430"/></p>

# Table of Contents

* [Supported operating systems](#supported-operating-systems)
* [Installation](#installation)
* [Documentation](#documentation)
* [Getting Help](#getting-help)
* [Command Line Usage](#command-line-usage)
  * [Command Line Examples](#command-line-examples)
  * [Tutorial](#tutorial)
  * [Command Line Reference: export](#command-line-reference-export)
  * [Files Created By OSXPhotos](#files-created-by-osxphotos)
* [Python API](#python-api)
* [Template System](#template-system)
* [Related Projects](#related-projects)
* [Contributing](#contributing)
* [Known Bugs and Limitations](#known-bugs-and-limitations)
* [Implementation Notes](#implementation-notes)
* [Acknowledgements](#acknowledgements)

## Supported operating systems

Tested on Ubuntu Linux and macOS. Many features are only available on macOS.

On Linux, macOS-specific features of the CLI will not be available (these will not be shown in the help output). The export and query CLI commands as well as the Python API will work on Linux which enables you to export photos from a Photos library on a Linux machine.

Tested on macOS Sierra (10.12.6) through macOS Sequoia (15.i7.2). Tested on both x86 and Apple silicon (M1).

**Most features work on macOS 26.1 but OSXPhotos does yet fully support 26.x. Notably OSXPhotos cannot read shared albums on macOS 26.x.**

| macOS Version     | macOS name | Photos.app version  |
| ----------------- |------------|:--------------------|
| 26.0              | Tahoe      | 11.0 (not yet tested) ❌|
| 26.0 (beta)       | Tahoe      | 11.0 (alpha support)|
| 15.0 - 15.6       | Sequoia    | 10.0 ✅             |
| 14.0 - 14.6       | Sonoma     | 9.0 ✅              |
| 13.0 - 13.6       | Ventura    | 8.0 ✅              |
| 12.0 - 12.7       | Monterey   | 7.0 ✅              |
| 10.16, 11.0-11.7  | Big Sur    | 6.0 ✅              |
| 10.15.1 - 10.15.7 | Catalina   | 5.0 ✅              |
| 10.14.5, 10.14.6  | Mojave     | 4.0 ✅              |
| 10.13.6           | High Sierra| 3.0 ✅              |
| 10.12.6           | Sierra     | 2.0 ✅              |

Limited support is also provided for exporting photos and metadata from iPhoto libraries. Only iPhoto 9.6.1 (the final release) has been tested.

This package will read Photos databases for any supported version on any supported macOS version.  E.g. you can read a database created with Photos 5.0 on MacOS 10.15 on a machine running macOS 10.12 and vice versa.

Requires python >= `3.10`, <= `3.14`.

For macOS 26.0 / Tahoe developer preview, alpha support is provided (very preliminary, not guaranteed to work). Not all features of osxphotos have been tested and some features may not work. If you encounter issues, please open an issue on GitHub.

## Installation

The recommended way to install `osxphotos` is via the [uv](https://github.com/astral-sh/uv) python package manager tool.

### Installation using `uv`

* Open `Terminal` (search for `Terminal` in Spotlight or look in `Applications/Utilities`)
* Install `uv` by running the following command in Terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If you previously installed `uv`, upgrade to the latest version:

```bash
uv self update
```

* Type the following into Terminal:

```bash
uv tool install --python 3.13 osxphotos
```

* Now you should be able to run `osxphotos` by typing: `osxphotos`

**Note**: If you encounter errors during installation on older versions of macOS, try using an older version of python, for example, on macOS 12.7, you must use python 3.11:

```bash
uv tool install osxphotos --python 3.11
```

Once you've installed osxphotos with `uv`, to upgrade to the latest version:

```bash
uv tool upgrade osxphotos
```

If you want to try `osxphotos` without installing it, you can run `uv tool run --python 3.13 osxphotos` or `uvx --python 3.13 osxphotos`. On older versions of macOS, you may need to use an older version of python: `uv tool run --python 3.11 osxphotos` or `uvx --python 3.11 osxphotos`.


### Installation using Brew

You can install `osxphotos` via Homebrew

```
# Add the tap
brew tap RhetTbull/osxphotos

# Install osxphotos
brew install osxphotos
```

### Installation using pip

You can install `osxphotos` directly from [pypi](https://pypi.org/project/osxphotos/):

    python3 -m pip install osxphotos

Once you've installed osxphotos with pip, to upgrade to the latest version:

    python3 -m pip install --upgrade osxphotos

### Installation via MacPorts

If you use the [MacPorts](https://www.macports.org) package manager on a Mac:

    sudo port install osxphotos

### Installation on Linux

At least one of the Linux-specific python packages normally installed on Linux may cause an error during installation with `pip` or `pipx`. If you encounter an error similar to: `pip._vendor.packaging.version.InvalidVersion: Invalid version: '6.5.0-1022-generic`, you should still be able to install osxphotos using the `uv` installation instructions above.

### Installation from git repository

If you want to work on osxphotos code or contribute to the project, you can install from the git repository:

    git clone https://github.com/RhetTbull/osxphotos.git
    cd osxphotos

> [!NOTE]
> The git repo for this project is very large (> 3GB) because it contains multiple Photos libraries used for testing on different versions of macOS.
>
> If you just want to use the osxphotos package in your own code, I recommend you install the latest version from [PyPI](https://pypi.org/project/osxphotos/) which does not include all the test libraries. If you just want to use the command line utility, you can download a pre-built executable of the latest [release](https://github.com/RhetTbull/osxphotos/releases) or you can install via `pip` which also installs the command line app.  If you aren't comfortable with running python on your Mac, start with the pre-built executable or with `uv` as described above.
>
> Alternatively, to clone the repository without the test data:
>
>     git clone --filter=blob:none --no-checkout --sparse https://github.com/RhetTbull/osxphotos.git
>     cd osxphotos
>     git sparse-checkout set --no-cone '/*' '!tests'
>     git checkout
>

Next, install the required dependencies, and `osxphotos` itself. I recommend you create a
[virtual environment](https://docs.python.org/3/tutorial/venv.html) before installing osxphotos.

    python3 -m pip install -r dev_requirements.txt
    python3 -m pip install -r requirements.txt
    python3 -m pip install -e .

Once you've installed osxphotos via the git repository, to upgrade to the latest version:

    cd osxphotos
    git pull
    python3 -m pip install -e .

See also the developer notes in [README_DEV.md](README_DEV.md).

### Installing pre-built executable

You can also download a stand-alone pre-built executable--that doesn't require installing python--from the [releases](https://github.com/RhetTbull/osxphotos/releases) page. Look for the file with a name similar to `osxphotos_MacOS_exe_darwin_x86_64_v0.63.5.zip`. In this case `v0.63.5` specifies version 0.63.5 and `x86_64` specifies Intel x86 platform; you should download the latest version available. For Apple Silicon, there is an equivalent `arm64` version of the executable. Unzip the file and put the included `osxphotos` binary in your system path.  Currently, the binary is not notarized so you'll have to authorize the app to run in the System Preferences | Security & Privacy settings. If you don't know how to do this, I recommend using `uv` as described above.

## Documentation

See the [documentation](https://rhettbull.github.io/osxphotos/) for more information on using osxphotos.

## Getting Help

OSXPhotos is well documented.  See the [tutorial](#tutorial) for a description of key features.  The tutorial can be accessed using the command `osxphotos tutorial` via the command line.  If you are interested in using OSXPhotos in your own code, see [API_README.md](https://github.com/RhetTbull/osxphotos/blob/master/API_README.md) for a description of the API as well as the [example](https://github.com/RhetTbull/osxphotos/tree/master/examples) programs. The full documentation is [available online](https://rhettbull.github.io/osxphotos/) and can also be accessed using the command `osxphotos docs` via the command line. Running `osxphotos help` will show help in the terminal. You can use `osxphotos help COMMAND` to get help on a command. For example, `osxphotos help export`. To search within the help of a specific command, use `osxphotos help COMMAND TOPIC`, for example, `osxphotos help export sidecar`.

If you have questions, would like to show off projects created with OSXPhotos, or if you just want to say hello, please use the [GitHub discussions forum](https://github.com/RhetTbull/osxphotos/discussions) or the [osxphotos subreddit](https://www.reddit.com/r/osxphotos/) on Reddit.

## Command Line Usage

This package will install a command line utility called `osxphotos` that allows you to query the Photos database.  Alternatively, you can also run the command line utility like this: `python3 -m osxphotos`

<!--[[[cog
from osxphotos.cli import cli_main
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli_main, ["--help"])
help = result.output.replace("Usage: cli-main", "Usage: osxphotos")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
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
  options. These can be seen by running "OSXPHOTOS_SHOW_HIDDEN=1 osxphotos help
  COMMAND".

Options:
  -v, --version  Show the version and exit.
  -h, --help     Show this message and exit.

Commands:
  about             Print information about osxphotos including license.
  add-locations     Add missing location data to photos in Photos.app using...
  albums            Print out albums found in the Photos library.
  batch-edit        Batch edit photo metadata such as title, description,...
  compare           Compare two Photos libraries to find differences
  docs              Open osxphotos documentation in your browser.
  dump              Print list of all photos & associated info from the...
  exiftool          Run exiftool on previously exported files to update...
  export            Export photos from the Photos database.
  exportdb          Utilities for working with the osxphotos export database
  help              Print help; for help on commands: help <command>.
  import            Import photos and videos into Photos.
  info              Print out descriptive info of the Photos library database.
  inspect           Interactively inspect photos selected in Photos.
  install           Install Python packages into the same environment as...
  keywords          Print out keywords found in the Photos library.
  labels            Print out image classification labels found in the...
  list              Print list of Photos libraries found on the system.
  orphans           Find orphaned photos in a Photos library
  persons           Print out persons (faces) found in the Photos library.
  places            Print out places found in the Photos library.
  push-exif         Write photo metadata to original files in the Photos...
  query             Query the Photos database using 1 or more search...
  repl              Run interactive osxphotos REPL shell (useful for...
  run               Run a python file using same environment as osxphotos.
  shell-completion  Install shell completion for osxphotos.
  show              Show photo, album, or folder in Photos from UUID_OR_NAME
  sync              Sync metadata and albums between Photos libraries.
  template          Interactively render templates for selected photo.
  theme             Manage osxphotos color themes.
  timewarp          Adjust date/time/timezone of photos in Apple Photos.
  tutorial          Display osxphotos tutorial.
  uninstall         Uninstall Python packages from the osxphotos environment
  update            Update the installation to the latest version.
  uuid              Print out unique IDs (UUID) of photos selected in Photos
  version           Check for new version of osxphotos.

```
<!--[[[end]]] -->

To get help on a specific command, use `osxphotos help COMMAND`, for example, `osxphotos help export` to get help on the `export` command.

Some of the commands such as `export` and `query` have a large number of options.  To search for options related to a specific topic, you can use `osxphotos help COMMAND TOPIC`.  For example, `osxphotos help export raw` finds the options related to RAW files (search is case-insensitive):

```
Usage: osxphotos export [OPTIONS] ... DEST

  Export photos from the Photos database. Export path DEST is required.
  Optionally, query the Photos database using 1 or more search options; if
  more than one option is provided, they are treated as "AND" (e.g. search for
  photos matching all options). If no query options are provided, all photos
  will be exported. By default, all versions of all photos will be exported
  including edited versions, live photo movies, burst photos, and associated
  raw images. See --skip-edited, --skip-live, --skip-bursts, and --skip-raw
  options to modify this behavior.

Options that match 'raw':

--has-raw                    Search for photos with both a jpeg and
                             raw version
--skip-raw                   Do not export associated RAW image of a
                             RAW+JPEG pair.  Note: this does not skip RAW
                             photos if the RAW photo does not have an
                             associated JPEG image (e.g. the RAW file was
                             imported to Photos without a JPEG preview).
--convert-to-jpeg            Convert all non-JPEG images (e.g. RAW, HEIC,
                             PNG, etc) to JPEG upon export. Note: does not
                             convert the RAW component of a RAW+JPEG pair as
                             the associated JPEG image will be exported. You
                             can use --skip-raw to skip
                             exporting the associated RAW image of a
                             RAW+JPEG pair. See also --jpeg-quality and
                             --jpeg-ext. Only works if your Mac has a GPU
                             (thus may not work on virtual machines).
```

### Command line examples

#### export all photos to ~/Desktop/export group in folders by date created

`osxphotos export --export-by-date --library ~/Pictures/Photos\ Library.photoslibrary ~/Desktop/export`

#### find all photos with keyword "Kids" and output results to json file named results.json

`osxphotos query --keyword Kids --json --library ~/Pictures/Photos\ Library.photoslibrary >results.json`

#### Find all videos larger than 200MB and add them to an album named "Big Videos" in Photos, creating the album if necessary. Use the last opened library (do not explicitely specify a library)

`osxphotos query --only-movies --min-size 200MB --add-to-album "Big Videos"`

### Tutorial
<!-- OSXPHOTOS-TUTORIAL:START --><!-- OSXPHOTOS-TUTORIAL-HEADER:START --><!-- OSXPHOTOS-TUTORIAL-HEADER:END -->

The design philosophy for osxphotos is "make the easy things easy and make the hard things possible".  To "make the hard things possible", osxphotos is very flexible and has many, many configuration options -- the `export` command for example, has over 100 command line options.  Thus, osxphotos may seem daunting at first.  The purpose of this tutorial is to explain a number of common use cases with examples and, hopefully, make osxphotos less daunting to use.  osxphotos includes several commands for retrieving information from your Photos library but the one most users are interested in is the `export` command which exports photos from the library so that's the focus of this tutorial.

#### Export your photos

`osxphotos export /path/to/export`

This command exports all your photos to the `/path/to/export` directory.

**Note**: osxphotos uses the term 'photo' to refer to a generic media asset in your Photos Library.  A photo may be an image, a video file, a combination of still image and video file (e.g. an Apple "Live Photo" which is an image and an associated "live preview" video file), a JPEG image with an associated RAW image, etc.

#### Export by date

While the previous command will export all your photos (and videos--see note above), it probably doesn't do exactly what you want.  In the previous example, all the photos will be exported to a single folder: `/path/to/export`.  If you have a large library with thousands of images and videos, this likely isn't very useful.  You can use the `--export-by-date` option to export photos to a folder structure organized by year, month, day, e.g. `2021/04/21`:

`osxphotos export /path/to/export --export-by-date`

With this command, a photo that was created on 31 May 2015 would be exported to: `/path/to/export/2015/05/31`

#### Specify directory structure

If you prefer a different directory structure for your exported images, osxphotos provides a very flexible <!-- OSXPHOTOS-TEMPLATE-SYSTEM-LINK:START -->[Template System](#template-system)<!-- OSXPHOTOS-TEMPLATE-SYSTEM-LINK:END --> that allows you to specify the directory structure using the `--directory` option.  For example, this command exported to a directory structure that looks like: `2015/May` (4-digit year / month name):

`osxphotos export /path/to/export --directory "{created.year}/{created.month}"`

The string following `--directory` is an `osxphotos template string`.  Template strings are widely used throughout osxphotos and it's worth your time to learn more about them.  In a template string, the values between the curly braces, e.g. `{created.year}` are replaced with metadata from the photo being exported.  In this case, `{created.year}` is the 4-digit year of the photo's creation date and `{created.month}` is the full month name in the user's locale (e.g. `May`, `mai`, etc.).  In the osxphotos template system these are referred to as template fields. The text not included between `{}` pairs is interpreted literally, in this case `/`, is a directory separator.

osxphotos provides access to almost all the metadata known to Photos about your images.  For example, Photos performs reverse geolocation lookup on photos that contain GPS coordinates to assign place names to the photo.  Using the `--directory` template, you could thus export photos organized by country name:

`osxphotos export /path/to/export --directory "{created.year}/{place.name.country}"`

Of course, some photos might not have an associated place name so the template system allows you specify a default value to use if a template field is null (has no value).

`osxphotos export /path/to/export --directory "{created.year}/{place.name.country,No-Country}"`

The value after the ',' in the template string is the default value, in this case 'No-Country'.  **Note**: If you don't specify a default value and a template field is null, osxphotos will use "_" (underscore character) as the default.

Some template fields, such as `{keyword}`, may expand to more than one value.  For example, if a photo has keywords of "Travel" and "Vacation", `{keyword}` would expand to "Travel", "Vacation".  When used with `--directory`, this would result in the photo being exported to more than one directory (thus more than one copy of the photo would be exported).  For example, if `IMG_1234.JPG` has keywords `Travel`, and `Vacation` and you run the following command:

`osxphotos export /path/to/export --directory "{keyword}"`

the exported files would be:

    /path/to/export/Travel/IMG_1234.JPG
    /path/to/export/Vacation/IMG_1234.JPG

If your photos are organized in folders and albums in Photos you can preserve this structure on export by using the `{folder_album}` template field with the `--directory` option.  For example, if you have a photo in the album `Vacation` which is in the `Travel` folder, the following command would export the photo to the `Travel/Vacation` directory:

`osxphotos export /path/to/export --directory "{folder_album}"`

Photos can belong to more than one album.  In this case, the template field `{folder_album}` will expand to all the album names that the photo belongs to.  For example, if a photo belongs to the albums `Vacation` and `Travel`, the template field `{folder_album}` would expand to `Vacation`, `Travel`.  If the photo belongs to no albums, the template field `{folder_album}` would expand to "_" (the default value).  

All template fields including `{folder_album}` can be further filtered using a number of different filters.  To convert all directory names to lower case for example, use the `lower` filter:

`osxphotos export /path/to/export --directory "{folder_album|lower}"`

If all your photos were organized into various albums under a folder named `Events` but some where also included in other top-level albums and you wanted to export only the `Events` folder, you could use the `filter` option to filter out the other top-level albums by selecting only those folder/album paths that start with `Events`:

`osxphotos export /path/to/export --directory "{folder_album|filter(startswith Events)}"`

You can learn more about the other filters using `osxphotos help export`.

#### Specify exported filename

By default, osxphotos will use the original filename of the photo when exporting.  That is, the filename the photo had when it was taken or imported into Photos.  This is often something like `IMG_1234.JPG` or `DSC05678.dng`.  osxphotos allows you to specify a custom filename template using the `--filename` option in the same way as `--directory` allows you to specify a custom directory name.  For example, Photos allows you specify a title or caption for a photo and you can use this in place of the original filename:

`osxphotos export /path/to/export --filename "{title}"`

The above command will export photos using the title.  Note that you don't need to specify the extension as part of the `--filename` template as osxphotos will automatically add the correct file extension.  Some photos might not have a title so in this case, you could use the default value feature to specify a different name for these photos.  For example, to use the title as the filename, but if no title is specified, use the original filename instead:

    osxphotos export /path/to/export --filename "{title,{original_name}}"
                                                  │    ││  │ 
                                                  │    ││  │ 
         Use photo's title as the filename <──────┘    ││  │
                                                       ││  │
                Value after comma will be used <───────┘│  │
                if title is blank                       │  │
                                                        │  │
                          The default value can be <────┘  │
                          another template field           │
                                                           │
              Use photo's original name if no title <──────┘

The osxphotos template system also allows for limited conditional logic of the type "If a condition is true then do one thing, otherwise, do a different thing". For example, you can use the `--filename` option to name files that are marked as "Favorites" in Photos differently than other files. For example, to add a "#" to the name of every photo that's a favorite:

    osxphotos export /path/to/export --filename "{original_name}{favorite?#,}"
                                                  │              │       │││ 
                                                  │              │       │││ 
         Use photo's original name as filename <──┘              │       │││
                                                                 │       │││
              'favorite' is True if photo is a Favorite, <───────┘       │││
              otherwise, False                                           │││
                                                                         │││
                               '?' specifies a conditional <─────────────┘││
                                                                          ││
                     Value immediately following ? will be used if <──────┘│
                     preceding template field is True or non-blank         │
                                                                           │
                  Value immediately following comma will be used if <──────┘
                  template field is False or blank (null); in this case
                  no value is specified so a blank string "" will be used

Like with `--directory`, using a multi-valued template field such as `{keyword}` may result in more than one copy of a photo being exported.  For example, if `IMG_1234.JPG` has keywords `Travel`, and `Vacation` and you run the following command:

`osxphotos export /path/to/export --filename "{keyword}-{original_name}"`

the exported files would be:

    /path/to/export/Travel-IMG_1234.JPG
    /path/to/export/Vacation-IMG_1234.JPG

#### Edited photos

If a photo has been edited in Photos (e.g. cropped, adjusted, etc.) there will be both an original image and an edited image in the Photos Library.  By default, osxphotos will export both the original and the edited image.  To distinguish between them, osxphotos will append "_edited" to the edited image.  For example, if the original image was named `IMG_1234.JPG`, osxphotos will export the original as `IMG_1234.JPG` and the edited version as `IMG_1234_edited.jpeg`.  **Note:** Photos changes the extension of edited images to ".jpeg" even if the original was named ".JPG".  You can change the suffix appended to edited images using the `--edited-suffix` option:

`osxphotos export /path/to/export --edited-suffix "_EDIT"`

In this example, the edited image would be named `IMG_1234_EDIT.jpeg`.  Like many options in osxphotos, the `--edited-suffix` option can evaluate an osxphotos template string so you could append the modification date (the date the photo was edited) to all edited photos using this command:

`osxphotos export /path/to/export --edited-suffix "_{modified.year}-{modified.mm}-{modified.dd}"`

In this example, if the photo was edited on 21 April 2021, the name of the exported file would be: `IMG_1234_2021-04-21.jpeg`.

You can tell osxphotos to not export edited photos (that is, only export the original unedited photos) using `--skip-edited`:

`osxphotos export /path/to/export --skip-edited`

You can also tell osxphotos to export either the original photo (if the photo has not been edited) or the edited photo (if it has been edited), but not both, using the `--skip-original-if-edited` option:

`osxphotos export /path/to/export --skip-original-if-edited`

As mentioned above, Photos renames JPEG images that have been edited with the ".jpeg" extension.  Some applications use ".JPG" and others use ".jpg" or ".JPEG".  You can use the `--jpeg-ext` option to have osxphotos rename all JPEG files with the same extension.  Valid values are jpeg, jpg, JPEG, JPG; e.g. `--jpeg-ext jpg` to use '.jpg' for all JPEGs.

`osxphotos export /path/to/export --jpeg-ext jpg`

#### Specifying the Photos library

All the above commands operate on the default Photos library.  Most users only use a single Photos library which is also known as the System Photo Library.  It is possible to use Photos with more than one library.  For example, if you hold down the "Option" key while opening Photos, you can select an alternate Photos library.  If you don't specify which library to use, osxphotos will try find the last opened library.  Occasionally it can't determine this and in that case, it will use the System Photos Library.  If you use more than one Photos library and want to explicitly specify which library to use, you can do so with the `--library` option.

`osxphotos export /path/to/export --library ~/Pictures/MyAlternateLibrary.photoslibrary`

#### Missing photos

osxphotos works by copying photos out of the Photos library folder to export them.  You may see osxphotos report that one or more photos are missing and thus could not be exported.  One possible reason for this is that you are using iCloud to synch your Photos library and Photos either hasn't yet synched the cloud library to the local Mac or you have Photos configured to "Optimize Mac Storage" in Photos Preferences. Another reason is that even if you have Photos configured to download originals to the Mac, Photos does not always download photos from shared albums or original screenshots to the Mac.  

If you encounter missing photos you can tell osxphotos to download the missing photos from iCloud using the `--download-missing` option.  `--download-missing` uses AppleScript to communicate with Photos and tell it to download the missing photos.  Photos' AppleScript interface is somewhat buggy and you may find that Photos crashes.  In this case, osxphotos will attempt to restart Photos to resume the download process.  There's also an experimental `--use-photokit` option that will communicate with Photos using a different "PhotoKit" interface.  This option must be used together with `--download-missing`:

`osxphotos export /path/to/export --download-missing`

`osxphotos export /path/to/export --download-missing --use-photokit`

#### Exporting to external disks

If you are exporting to an external network attached storage (NAS) device, you may encounter errors if the network connection is unreliable.  In this case, you can use the `--retry` option so that osxphotos will automatically retry the export.  Use `--retry` with a number that specifies the number of times to retry the export:

`osxphotos export /path/to/export --retry 3`

In this example, osxphotos will attempt to export a photo up to 3 times if it encounters an error.

In addition to `--retry`, the `--exportdb` and `--ramdb` may improve performance when exporting to an external disk or a NAS. When osxphotos exports photos, it creates an export database file named `.osxphotos_export.db` in the export folder which osxphotos uses to keep track of which photos have been exported.  This allows you to restart and export and to use `--update` to update an existing export. If the connection to the export location is slow or flaky, having the export database located on the export disk may decrease performance.  In this case, you can use `--exportdb DBPATH` to instruct osxphotos to store the export database at DBPATH. If using this option, I recommend putting the export database on your Mac system disk (for example, in your home directory). If you intend to use `--update` to update the export in the future, you must remember where the export database is and use the `--exportdb` option every time you update the export.

Another alternative to using `--exportdb` is to use `--ramdb`.  This option instructs osxphotos to use a RAM database instead of a file on disk.  The RAM database is much faster than the file on disk and doesn't require osxphotos to access the network drive to query or write to the database.  When osxphotos completes the export it will write the RAM database to the export location. This can offer a significant performance boost but you will lose state information if osxphotos crashes or is interrupted during export.

#### Exporting metadata with exported photos

Photos tracks a tremendous amount of metadata associated with photos in the library such as keywords, faces and persons, reverse geolocation data, and image classification labels.  Photos' native export capability does not preserve most of this metadata.  osxphotos can, however, access and preserve almost all the metadata associated with photos.  Using the free [`exiftool`](https://exiftool.org/) app, osxphotos can write metadata to exported photos.  Follow the instructions on the exiftool website to install exiftool then you can use the `--exiftool` option to write metadata to exported photos:

`osxphotos export /path/to/export --exiftool`

This will write basic metadata such as keywords, persons, and GPS location to the exported files.  osxphotos includes several additional options that can be used in conjunction with `--exiftool` to modify the metadata that is written by `exiftool`. For example, you can use the `--keyword-template` option to specify custom keywords (again, via the osxphotos template system).  For example, to use the folder and album a photo is in to create hierarchical keywords in the format used by Lightroom Classic:

    osxphotos export /path/to/export --exiftool --keyword-template "{folder_album(>)}"
                                                                     │            │
                                                                     │            │ 
                           folder_album results in the folder(s)  <──┘            │    
                           and album a photo is contained in                      │  
                                                                                  │     
                           The value in () is used as the path separator  <───────┘     
                           for joining the folders and albums.  For example, 
                           if photo is in Folder1/Folder2/Album, (>) produces
                           "Folder1>Folder2>Album" which some programs, such as
                           Lightroom Classic, treat as hierarchical keywords

The above command will write all the regular metadata that `--exiftool` normally writes to the file upon export but will also add an additional keyword in the exported metadata in the form "Folder1>Folder2>Album".  If you did not include the `(>)` in the template string (e.g. `{folder_album}`), folder_album would render in form "Folder1/Folder2/Album".

A powerful feature of Photos is that it uses machine learning algorithms to automatically classify or label photos.  These labels are used when you search for images in Photos but are not otherwise available to the user.  osxphotos is able to read all the labels associated with a photo and makes those available through the template system via the `{label}`.  Think of these as automatic keywords as opposed to the keywords you assign manually in Photos.  One common use case is to use the automatic labels to create new keywords when exporting images so that these labels are embedded in the image's metadata:

`osxphotos export /path/to/export --exiftool --keyword-template "{label}"`

#### Removing a keyword during export

If some of your photos contain a keyword you do not want to be added to the exported file with `--exiftool`, you can use the template system to remove the keyword from the exported file. For example, if you want to remove the keyword "MyKeyword" from all your photos:

`osxphotos export /path/to/export --exiftool --keyword-template "{keyword|remove(MyKeyword)}" --replace-keywords`

In this example, `|remove(MyKeyword)` is a filter which removes `MyKeyword` from the keyword list of every photo being processed.  The `--replace-keywords` option instructs osxphotos to replace the keywords in the exported file with the filtered keywords from `--keyword-template`.

**Note**: When evaluating templates for `--directory` and `--filename`, osxphotos inserts the automatic default value "_" for any template field which is null (empty or blank).  This is to ensure that there's never a null directory or filename created.  For metadata templates such as `--keyword-template`, osxphotos does not provide an automatic default value thus if the template field is null, no keyword would be created.  Of course, you can provide a default value if desired and osxphotos will use this.  For example, to add "nolabel" as a keyword for any photo that doesn't have labels:

`osxphotos export /path/to/export --exiftool --keyword-template "{label,nolabel}"`

#### Sidecar files

Another way to export metadata about your photos is through the use of sidecar files.  These are files that have the same name as your photo (but with a different extension) and carry the metadata.  Many digital asset management applications (for example, PhotoPrism, Lightroom, Digikam, etc.) can read or write sidecar files.  osxphotos can export metadata in exiftool compatible JSON and XMP formats using the `--sidecar` option.  For example, to output metadata to XMP sidecars:

`osxphotos export /path/to/export --sidecar XMP`

Unlike `--exiftool`, you do not need to install exiftool to use the `--sidecar` feature.  Many of the same configuration options that apply to `--exiftool` to modify metadata, for example, `--keyword-template` can also be used with `--sidecar`.  

Sidecar files are named "photoname.ext.sidecar_ext".  For example, if the photo is named `IMG_1234.JPG` and the sidecar format is XMP, the sidecar would be named `IMG_1234.JPG.XMP`.  Some applications expect the sidecar in this case to be named `IMG_1234.XMP`.  You can use the `--sidecar-drop-ext` option to force osxphotos to name the sidecar files in this manner:

`osxphotos export /path/to/export --sidecar XMP --sidecar-drop-ext`

#### Updating a previous export

If you want to use osxphotos to perform periodic backups of your Photos library rather than a one-time export, use the `--update` option.  When `osxphotos export` is run, it creates a database file named `.osxphotos_export.db` in the export folder.  (**Note** Because the filename starts with a ".", you won't see it in Finder which treats "dot-files" like this as hidden.  You will see the file in the Terminal.) . If you run osxphotos with the `--update` option, it will look for this database file and, if found, use it to retrieve state information from the last time it was run to only export new or changed files.  For example:

`osxphotos export /path/to/export --update`

will read the export database located in `/path/to/export/.osxphotos_export.db` and only export photos that have been added or changed since the last time osxphotos was run.  You can run osxphotos with the `--update` option even if it's never been run before.  If the database isn't found, osxphotos will create it.  If you run `osxphotos export` without `--update` in a folder where you had previously exported photos, it will re-export all the photos.  If your intent is to keep a periodic backup of your Photos Library up to date with osxphotos, you should always use `--update`.

If your workflow involves moving files out of the export directory (for example, you move them into a digital asset management app) but you want to use the features of `--update`, you can use the `--only-new` with `--update` to force osxphotos to only export photos that are new (added to the library) since the last update.  In this case, osxphotos will ignore the previously exported files that are now missing.  Without `--only-new`, osxphotos would see that previously exported files are missing and re-export them.

`osxphotos export /path/to/export --update --only-new`

If your workflow involves editing the images you exported from Photos but you still want to maintain a backup with `--update`, you should use the `--ignore-signature` option.  `--ignore-signature` instructs osxphotos to ignore the file's signature (for example, size and date modified) when deciding which files should be updated with `--update`.  If you edit a file in the export directory and then run `--update` without `--ignore-signature`, osxphotos will see that the file is different than the one in the Photos library and re-export it.

`osxphotos export /path/to/export --update --ignore-signature`

#### Dry Run

You can use the `--dry-run` option to have osxphotos "dry run" or test an export without actually exporting any files.  When combined with the `--verbose` option, which causes osxphotos to print out details of every file being exported, this can be a useful tool for testing your export options before actually running a full export.  For example, if you are learning the template system and want to verify that your `--directory` and `--filename` templates are correct, `--dry-run --verbose` will print out the name of each file being exported.

`osxphotos export /path/to/export --dry-run --verbose`

#### Creating a report of all exported files

You can use the `--report` option to create a report, in comma-separated values (CSV) format that will list the details of all files that were exported, skipped, missing, etc. This file format is compatible with programs such as Microsoft Excel.  Provide the name of the report after the `--report` option:

`osxphotos export /path/to/export --report export.csv`

You can also create reports in JSON or SQLite format by changing the extension of the report filename.  For example, to create a JSON report:

`osxphotos export /path/to/export --report export.json`

And to create a SQLite report:

`osxphotos export /path/to/export --report export.sqlite`

#### Exporting only certain photos

By default, osxphotos will export your entire Photos library.  If you want to export only certain photos, osxphotos provides a rich set of "query options" that allow you to query the Photos database to filter out only certain photos that match your query criteria.  The tutorial does not cover all the query options as there are over 50 of them--read the help text (`osxphotos help export`) to better understand the available query options.  No matter which subset of photos you would like to export, there is almost certainly a way for osxphotos to filter these.  For example, you can filter for only images that contain certain keywords or images without a title, images from a specific time of day or specific date range, images contained in specific albums, etc.

For example, to export only photos with keyword `Travel`:

`osxphotos export /path/to/export --keyword "Travel"`

Like many options in osxphotos, `--keyword` (and most other query options) can be repeated to search for more than one term.  For example, to find photos with keyword `Travel` *or* keyword `Vacation`:

`osxphotos export /path/to/export --keyword "Travel" --keyword "Vacation"`

To export only photos contained in the album "Summer Vacation":

`osxphotos export /path/to/export --album "Summer Vacation"`

In Photos, it's possible to have multiple albums with the same name. In this case, osxphotos would export photos from all albums matching the value passed to `--album`.  If you wanted to export only one of the albums and this album is in a folder, the `--regex` option (short for "regular expression"), which does pattern matching, could be used with the `{folder_album}` template to match the specific album.  For example, if you had a "Summer Vacation" album inside the folder "2018" and also one with the same name inside the folder "2019", you could export just the album "2018/Summer Vacation" using this command:

`osxphotos export /path/to/export --regex "2018/Summer Vacation" "{folder_album}"`

This command matches the pattern "2018/Summer Vacation" against the full folder/album path for every photo.

There are also a number of query options to export only certain types of photos.  For example, to export only photos taken with iPhone "Portrait Mode":

`osxphotos export /path/to/export --portrait`

You can also export photos in a certain date range:

`osxphotos export /path/to/export --from-date "2020-01-01" --to-date "2020-02-28"`

or photos added to the library in the last week:

`osxphotos export /path/to/export --added-in-last "1 week"`

#### Converting images to JPEG on export

Photos can store images in many different formats.  osxphotos can convert non-JPEG images (for example, RAW photos) to JPEG on export using the `--convert-to-jpeg` option.  You can specify the JPEG quality (0: worst, 1.0: best) using `--jpeg-quality`.  For example:

`osxphotos export /path/to/export --convert-to-jpeg --jpeg-quality 0.9`

#### Finder attributes

In addition to using `exiftool` to write metadata directly to the image metadata, osxphotos can write certain metadata that is available to the Finder and Spotlight but does not modify the actual image file.  This is done through something called extended attributes which are stored in the filesystem with a file but do not actually modify the file itself. Finder tags and Finder comments are common examples of these.

osxphotos can, for example, write any keywords in the image to Finder tags so that you can search for images in Spotlight or the Finder using the `tag:tagname` syntax:

`osxphotos export /path/to/export --finder-tag-keywords`

`--finder-tag-keywords` also works with `--keyword-template` as described above in the section on `exiftool`:

`osxphotos export /path/to/export --finder-tag-keywords --keyword-template "{label}"`

The `--xattr-template` option allows you to set a variety of other extended attributes.  It is used in the format `--xattr-template ATTRIBUTE TEMPLATE` where ATTRIBUTE is one of 'authors','comment', 'copyright', 'description', 'findercomment', 'headline', 'keywords'.

For example, to set Finder comment to the photo's title and description:

`osxphotos export /path/to/export --xattr-template findercomment "{title}{newline}{descr}"`

In the template string above, `{newline}` instructs osxphotos to insert a new line character ("\n") between the title and description. In this example, if `{title}` or `{descr}` is empty, you'll get "title\n" or "\ndescription" which may not be desired so you can use more advanced features of the template system to handle these cases:

`osxphotos export /path/to/export --xattr-template findercomment "{title,}{title?{descr?{newline},},}{descr,}"`

Explanation of the template string:

    {title,}{title?{descr?{newline},},}{descr,}
     │           │      │ │       │ │  │ 
     │           │      │ │       │ │  │ 
     └──> insert title (or nothing if no title) 
                 │      │ │       │ │  │
                 └───> is there a title?
                        │ │       │ │  │
                        └───> if so, is there a description? 
                          │       │ │  │
                          └───> if so, insert new line 
                                  │ │  │
                                  └───> if descr is blank, insert nothing
                                    │  │ 
                                    └───> if title is blank, insert nothing
                                       │
                                       └───> finally, insert description 
                                             (or nothing if no description)

In this example, `title?` demonstrates use of the boolean (True/False) feature of the template system.  `title?` is read as "Is the title True (or not blank/empty)?  If so, then the value immediately following the `?` is used in place of `title`.  If `title` is blank, then the value immediately following the comma is used instead.  The format for boolean fields is `field?value if true,value if false`.  Either `value if true` or `value if false` may be blank, in which case a blank string ("") is used for the value and both may also be an entirely new template string as seen in the above example.  Using this format, template strings may be nested inside each other to form complex `if-then-else` statements.

The above example, while complex to read, shows how flexible the osxphotos template system is.  If you invest a little time learning how to use the template system you can easily handle almost any use case you have.

See Extended Attributes section in the help for `osxphotos export` for additional information about this feature.

#### Saving and loading options

If you repeatedly run a complex osxphotos export command (for example, to regularly back-up your Photos library), you can save all the options to a configuration file for future use (`--save-config FILE`) and then load them (`--load-config FILE`) instead of repeating each option on the command line.

To save the configuration:

`osxphotos export /path/to/export <all your options here> --update --save-config osxphotos.toml`

Then the next to you run osxphotos, you can simply do this:

`osxphotos export /path/to/export --load-config osxphotos.toml`

The configuration file is a plain text file in [TOML](https://toml.io/en/) format so the `.toml` extension is standard but you can name the file anything you like.

#### Run commands on exported photos for post-processing

You can use the `--post-command` option to run one or more commands against exported files. The `--post-command` option takes two arguments: CATEGORY and COMMAND.  CATEGORY is a string that describes which category of file to run the command against.  The available categories are described in the help text available via: `osxphotos help export`. For example, the `exported` category includes all exported photos and the `skipped` category includes all photos that were skipped when running export with `--update`.  COMMAND is an osxphotos template string which will be rendered then passed to the shell for execution.  

For example, the following command generates a log of all exported files and their associated keywords:

`osxphotos export /path/to/export --post-command exported "echo {shell_quote,{filepath}{comma}{,+keyword,}} >> {shell_quote,{export_dir}/exported.txt}"`

The special template field `{shell_quote}` ensures a string is properly quoted for execution in the shell.  For example, it's possible that a file path or keyword in this example has a space in the value and if not properly quoted, this would cause an error in the execution of the command. When running commands, the template `{filepath}` is set to the full path of the exported file and `{export_dir}` is set to the full path of the base export directory.  

Explanation of the template string:

    {shell_quote,{filepath}{comma}{,+keyword,}}
     │            │         │      │        │
     │            │         │      |        │
     └──> quote everything after comma for proper execution in the shell
                  │         │      │        │
                  └───> filepath of the exported file
                           │       │        │
                           └───> insert a comma 
                                   │        │
                                   └───> join the list of keywords together with a ","
                                            │
                                            └───> if no keywords, insert nothing (empty string: "")

Another example: if you had `exiftool` installed and wanted to wipe all metadata from all exported files, you could use the following:

`osxphotos export /path/to/export --post-command exported "/usr/local/bin/exiftool -all= {filepath|shell_quote}"`

This command uses the `|shell_quote` template filter instead of the `{shell_quote}` template because the only thing that needs to be quoted is the path to the exported file. Template filters filter the value of the rendered template field.  A number of other filters are available and are described in the help text.

#### An example from an actual osxphotos user

Here's a comprehensive use case from an actual osxphotos user that integrates many of the concepts discussed in this tutorial (thank-you Philippe for contributing this!):

    I usually import my iPhone’s photo roll on a more or less regular basis, and it
    includes photos and videos. As a result, the size ot my Photos library may rise
    very quickly. Nevertheless, I will tag and geolocate everything as Photos has a
    quite good keyword management system.

    After a while, I want to take most of the videos out of the library and move them
    to a separate "videos" folder on a different folder / volume. As I might want to
    use them in Final Cut Pro, and since Final Cut is able to import Finder tags into
    its internal library tagging system, I will use osxphotos to do just this.

    Picking the videos can be left to Photos, using a smart folder for instance. Then
    just add a keyword to all videos to be processed. Here I chose "Quik" as I wanted
    to spot all videos created on my iPhone using the Quik application (now part of
    GoPro).

    I want to retrieve my keywords only and make sure they populate the Finder tags, as
    well as export all the persons identified in the videos by Photos.  I also want to
    merge any keywords or persons already in the video metadata with the exported
    metadata.

    Keeping Photo’s edited titles and descriptions and putting both in the Finder
    comments field in a readable manner is also enabled.

    And I want to keep the file’s creation date (using `--touch-file`).

    Finally, use `--strip` to remove any leading or trailing whitespace from processed
    template fields.

`osxphotos export ~/Desktop/folder for exported videos/ --keyword Quik --only-movies --library /path to my.photoslibrary --touch-file --finder-tag-keywords --person-keyword --xattr-template findercomment "{title}{title?{descr?{newline},},}{descr}" --exiftool-merge-keywords --exiftool-merge-persons --exiftool --strip`

#### Color Themes

Some osxphotos commands such as export use color themes to colorize the output to make it more legible. The theme may be specified with the `--theme` option. For example: `osxphotos export /path/to/export --verbose --theme dark` uses a theme suited for dark terminals. If you don't specify the color theme, osxphotos will select a default theme based on the current terminal settings. You can also specify your own default theme. See `osxphotos help theme` for more information on themes and for commands to help manage themes.  Themes are defined in `.theme` files in the `~/.osxphotos/themes` directory and use style specifications compatible with the [rich](https://rich.readthedocs.io/en/stable/style.html) library.

#### Conclusion

osxphotos is very flexible.  If you merely want to backup your Photos library, then spending a few minutes to understand the `--directory` option is likely all you need and you can be up and running in minutes.  However, if you have a more complex workflow, osxphotos likely provides options to implement your workflow.  This tutorial does not attempt to cover every option offered by osxphotos but hopefully it provides a good understanding of what kinds of things are possible and where to explore if you want to learn more.
<!-- OSXPHOTOS-TUTORIAL:END -->

### Files Created By OSXPhotos

The OSXPhotos command line tool creates a number of files during the course of its execution.
OSXPhotos adheres to the [XDG](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) standard for file locations.

* `$XDG_CONFIG_HOME` or `$HOME/.config`: `osxphotos` directory containing configuration files, for example color themes for colorized output.
* `$XDG_DATA_HOME` or `$HOME/.local/share`: `osxphotos` directory containing local data files, for example, the help files displayed with `osxphotos docs`.
* Current working dir: `osxphotos_crash.log` file containing the stack trace of the last crash if OSXPhotos encounters a fatal error during execution.
* export directory (when running `osxphotos export` command): `.osxphotos_export.db` [SQLite](https://www.sqlite.org/index.html) database containing information needed to update an export and track metadata changes in exported photos. *Note*: This file may contain sensitive information such as locations and the names of persons in photos so if you are using `osxphotos export` to share with others, you may want to delete this file. You can also specify an alternate location for the export database using the `--exportdb` flag during export.  See also `osxphotos help exportdb` for more information about built in utilities for working with the export database.
* While osxphotos does not create the file, if present in the root of the export directory, osxphotos will read the file `.osxphotos_keep` to load a list of file/directory patterns which should be excluded from `--cleanup` during export. This file uses the same rule format as [.gitignore](https://git-scm.com/docs/gitignore). See `osxphotos help export cleanup` for more information.

## Python API

In addition to the command line interface, OSXPhotos provides a python API you can use within your own code. For additional information on the API, see [API_README.md](https://github.com/RhetTbull/osxphotos/blob/master/API_README.md) and the [osxphotos documentation](https://rhettbull.github.io/osxphotos/index.html).

## Template System

<!-- OSXPHOTOS-TEMPLATE-HELP:START - Do not remove or modify this section -->
<!-- Generated by cog: see phototemplate.cog.md -->

The templating system converts one or template statements, written in osxphotos metadata templating language, to one or more rendered values using information from the photo being processed.

In its simplest form, a template statement has the form: `"{template_field}"`, for example `"{title}"` which would resolve to the title of the photo.

Template statements may contain one or more modifiers.  The full syntax is:

`"pretext{delim+template_field:subfield(field_arg)|filter[find,replace] conditional&combine_value?bool_value,default}posttext"`

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
- `appends(x)`: Append s[tring] Append x to each value of list of values, e.g. appends(d): ['a', 'b', 'c'] => ['ad', 'bd', 'cd'].
- `prepends(x)`: Prepend s[tring] x to each value of list of values, e.g. prepends(d): ['a', 'b', 'c'] => ['da', 'db', 'dc'].
- `remove(x)`: Remove x from list of values, e.g. remove(b): ['a', 'b', 'c'] => ['a', 'c'].
- `slice(start:stop:step)`: Slice list using same semantics as Python's list slicing, e.g. slice(1:3): ['a', 'b', 'c', 'd'] => ['b', 'c']; slice(1:4:2): ['a', 'b', 'c', 'd'] => ['b', 'd']; slice(1:): ['a', 'b', 'c', 'd'] => ['b', 'c', 'd']; slice(:-1): ['a', 'b', 'c', 'd'] => ['a', 'b', 'c']; slice(::-1): ['a', 'b', 'c', 'd'] => ['d', 'c', 'b', 'a']. See also sslice().
- `sslice(start:stop:step)`: [s(tring) slice] Slice values in a list using same semantics as Python's string slicing, e.g. sslice(1:3):'abcd => 'bc'; sslice(1:4:2): 'abcd' => 'bd', etc. See also slice().
- `filter(x)`: Filter list of values using predicate x; for example, '{folder_album|filter(contains Events)}' returns only folders/albums containing the word 'Events' in their path.
- `path`: Convert values in list into pathlib objects for path manipulation; pathlib properties can be appended and chained. For example '{photo.original_filename|path.stem}' is functionally equivalent to '{original_name}' which doesn't include the extension.
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

`&combine_value`: Template fields may be combined with another template statement to return multiple values. The combine_value is another template statement. For example, the template {created.year&{folder_album,}} would resolve to ["1999", "Vacation"] if the photo was created in 1999 and was in the album Vacation. Because the combine_value is a template statement, multiple templates may be combined together by nesting the combine operator: {template1&{template2&{template3,},},}. In this example, a null default value is used to prevent the default value from being combined if any of the nested templates does not resolve to a value

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

You can define variables for later use in the template string using the format `{var:NAME,VALUE}` where `VALUE` is a template statement.  Variables may then be referenced using the format `%NAME`. For example: `{var:foo,bar}` defines the variable `%foo` to have value `bar`. This can be useful if you want to re-use a complex template value in multiple places within your template string or for allowing the use of characters that would otherwise be prohibited in a template string. For example, the "pipe" (`|`) character is not allowed in a find/replace pair but you can get around this limitation like so: `{var:pipe,{pipe}}{title[-,%pipe]}` which replaces the `-` character with `|` (the value of `%pipe`).

Another use case for variables is filtering combined template values. For example, using the `&combine_value` mechanism to combine two template values that might result in duplicate values, you could do the following: `{var:myvar,{template1&{template2,},}}{%myvar|uniq}` which allows the use of the uniq filter against the combined template values.

Variables can also be referenced as fields in the template string, for example: `{var:year,{created.year}}{original_name}-{%year}`. In some cases, use of variables can make your template string more readable.  Variables can be used as template fields, as values for filters, as values for conditional operations, or as default values.  When used as a conditional value or default value, variables should be treated like any other field and enclosed in braces as conditional and default values are evaluated as template strings. For example: `{var:name,Katie}{person contains {%name}?{%name},Not-{%name}}`.

If you need to use a `%` (percent sign character), you can escape the percent sign by using `%%`.  You can also use the `{percent}` template field where a template field is required. For example:

`{title[:,%%]}` replaces the `:` with `%` and `{title contains Foo?{title}{percent},{title}}` adds `%` to the  title if it contains `Foo`.

<!-- OSXPHOTOS-TEMPLATE-HELP:END -->

The following template field substitutions are availabe for use the templating system.

<!-- OSXPHOTOS-TEMPLATE-TABLE:START - Do not remove or modify this section -->
| Field | Description |
|--------------|-------------|
|{name}|Current filename of the photo|
|{original_name}|Photo's original filename when imported to Photos|
|{title}|Title of the photo|
|{descr}|Description of the photo|
|{media_type}|Special media type resolved in this precedence: selfie, time_lapse, panorama, slow_mo, screenshot, screen_recording, portrait, live_photo, burst, photo, video. Defaults to 'photo' or 'video' if no special type. Customize one or more media types using format: '{media_type,video=vidéo;time_lapse=vidéo_accélérée}'|
|{photo_or_video}|'photo' or 'video' depending on what type the image is. To customize, use default value as in '{photo_or_video,photo=fotos;video=videos}'|
|{hdr}|Photo is HDR?; True/False value, use in format '{hdr?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{edited}|True if photo has been edited (has adjustments), otherwise False; use in format '{edited?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{edited_version}|True if template is being rendered for the edited version of a photo, otherwise False. |
|{favorite}|Photo has been marked as favorite?; True/False value, use in format '{favorite?VALUE_IF_TRUE,VALUE_IF_FALSE}'|
|{burst}|If photo is a burst photo, returns the stem of the burst's key photo, e.g. 'IMG_1234', otherwise returns no value.|
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
|{counter}|A sequential counter, starting at 0, that increments each time it is evaluated.To start counting at a value other than 0, append append '(starting_value)' to the field name.For example, to start counting at 1 instead of 0: '{counter(1)}'.May be formatted using a python string format code.For example, to format as a 5-digit integer and pad with zeros, use '{counter:05d(1)}'which results in 00001, 00002, 00003...etc.You may also specify a stop value which causes the counter to reset to the starting valuewhen the stop value is reached and a step size which causes the counter to increment bythe specified value instead of 1. Use the format '{counter(start,stop,step)}' where start,stop, and step are integers. For example, to count from 1 to 10 by 2, use '{counter(1,11,2)}'.Note that the counter stops counting when the stop value is reached and does not return thestop value. Start, stop, and step are optional and may be omitted. For example, to countfrom 0 by 2s, use '{counter(,,2)}'.You may create an arbitrary number of counters by appending a unique name to the field namepreceded by a period: '{counter.a}', '{counter.b}', etc. Each counter will have its own stateand will start at 0 and increment by 1 unless otherwise specified. Note: {counter} is not suitable for use with 'export' and '--update' as the counter associated with a photo may change between export sessions. See also {id}.|
|{album_seq}|An integer, starting at 0, indicating the photo's index (sequence) in the containing album. Only valid when used in a '--filename' template and only when '{album}' or '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{album_seq}_{original_name}"'. To start counting at a value other than 0, append append '(starting_value)' to the field name.  For example, to start counting at 1 instead of 0: '{album_seq(1)}'. May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{album_seq:05d}' which results in 00000, 00001, 00002...etc. To format while also using a starting value: '{album_seq:05d(1)}' which results in 0001, 00002...etc.This may result in incorrect sequences if you have duplicate albums with the same name; see also '{folder_album_seq}'.|
|{folder_album_seq}|An integer, starting at 0, indicating the photo's index (sequence) in the containing album and folder path. Only valid when used in a '--filename' template and only when '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{folder_album_seq}_{original_name}"'. To start counting at a value other than 0, append '(starting_value)' to the field name. For example, to start counting at 1 instead of 0: '{folder_album_seq(1)}' May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{folder_album_seq:05d}' which results in 00000, 00001, 00002...etc. To format while also using a starting value: '{folder_album_seq:05d(1)}' which results in 0001, 00002...etc.This may result in incorrect sequences if you have duplicate albums with the same name in the same folder; see also '{album_seq}'. |
|{comma}|A comma: ','|
|{semicolon}|A semicolon: ';'|
|{questionmark}|A question mark: '?'|
|{pipe}|A vertical pipe: '\|'|
|{percent}|A percent sign: '%'|
|{ampersand}|an ampersand symbol: '&'|
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
|{osxphotos_version}|The osxphotos version, e.g. '0.75.0'|
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
|{exiftool}|Format: '{exiftool:GROUP:TAGNAME}'; use exiftool (https://exiftool.org) to extract metadata, in form GROUP:TAGNAME, from image.  E.g. '{exiftool:EXIF:Make}' to get camera make, or {exiftool:IPTC:Keywords} to extract keywords. See https://exiftool.org/TagNames/ for list of valid tag names.  You must specify group (e.g. EXIF, IPTC, etc) as used in 'exiftool -G'. exiftool must be installed in the path to use this template.|
|{searchinfo.holiday}|Holiday names associated with a photo, e.g. 'Christmas Day'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.activity}|Activities associated with a photo, e.g. 'Sporting Event'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.venue}|Venues associated with a photo, e.g. name of restaurant; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{searchinfo.venue_type}|Venue types associated with a photo, e.g. 'Restaurant'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).|
|{photo}|Provides direct access to the PhotoInfo object for the photo. Must be used in format '{photo.property}' where 'property' represents a PhotoInfo property. For example: '{photo.favorite}' is the same as '{favorite}' and '{photo.place.name}' is the same as '{place.name}'. '{photo}' provides access to properties that are not available as separate template fields but it assumes some knowledge of the underlying PhotoInfo class.  See https://rhettbull.github.io/osxphotos/ for additional documentation on the PhotoInfo class.|
|{detected_text}|List of text strings found in the image after performing text detection. Using '{detected_text}' will cause osxphotos to perform text detection on your photos using the built-in macOS text detection algorithms which will slow down your export. The results for each photo will be cached in the export database so that future exports with '--update' do not need to reprocess each photo. You may pass a confidence threshold value between 0.0 and 1.0 after a colon as in '{detected_text:0.5}'; The default confidence threshold is 0.75. '{detected_text}' works only on macOS Catalina (10.15) or later. Note: this feature is not the same thing as Live Text in macOS Monterey, which osxphotos does not yet support.|
|{shell_quote}|Use in form '{shell_quote,TEMPLATE}'; quotes the rendered TEMPLATE value(s) for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.|
|{strip}|Use in form '{strip,TEMPLATE}'; strips whitespace from begining and end of rendered TEMPLATE value(s).|
|{format}|Use in form '{format:TYPE:FORMAT,TEMPLATE}'; converts TEMPLATE value to TYPE then formats the value using Python string formatting codes specified by FORMAT; TYPE is one of: 'int', 'float', or 'str'. For example, '{format:float:.1f,{exiftool:EXIF:FocalLength}}' will format focal length to 1 decimal place (e.g. '100.0'). |
|{function}|Execute a python function from an external file and use return value as template substitution. Use in format: {function:file.py::function_name} where 'file.py' is the path/name of the python file and 'function_name' is the name of the function to call. The file name may also be url to a python file, e.g. '{function:https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/template_function.py::example}'. The function will be passed the PhotoInfo object for the photo. See https://github.com/RhetTbull/osxphotos/blob/master/examples/template_function.py for an example of how to implement a template function.|
<!-- OSXPHOTOS-TEMPLATE-TABLE:END -->

## Related Projects

* [rhettbull/exif2findertags](https://github.com/RhetTbull/exif2findertags): Read EXIF metadata from image and video files and convert it to macOS Finder tags and/or Finder comments and other extended attributes.
* [rhettbull/photos_time_warp](https://github.com/RhetTbull/photos_time_warp): Batch adjust the date, time, or timezone of photos in Apple Photos.
* [rhettbull/PhotoScript](https://github.com/RhetTbull/PhotoScript): python wrapper around Photos' applescript API allowing automation of Photos (including creation/deletion of items) from python.
* [ndbroadbent/icloud_photos_downloader](https://github.com/ndbroadbent/icloud_photos_downloader): Download photos from iCloud.

## Contributing

Contributing is easy!  if you find bugs or want to suggest additional features/changes, please open an [issue](https://github.com/rhettbull/osxphotos/issues/) or join the [discussion](https://github.com/RhetTbull/osxphotos/discussions).

I'll gladly consider pull requests for bug fixes or feature implementations.

If you have an interesting example that shows usage of this package, submit an issue or pull request and i'll include it or link to it.

Testing against "real world" Photos libraries would be especially helpful.  If you discover issues in testing against your Photos libraries, please open an issue.  I've done extensive testing against my own Photos library but that's a single data point and I'm certain there are issues lurking in various edge cases I haven't discovered yet.

### Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/britiscurious"><img src="https://avatars1.githubusercontent.com/u/25646439?v=4?s=75" width="75px;" alt="britiscurious"/><br /><sub><b>britiscurious</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=britiscurious" title="Documentation">📖</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=britiscurious" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mwort"><img src="https://avatars3.githubusercontent.com/u/8170417?v=4?s=75" width="75px;" alt="Michel Wortmann"/><br /><sub><b>Michel Wortmann</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=mwort" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/PabloKohan"><img src="https://avatars3.githubusercontent.com/u/8790976?v=4?s=75" width="75px;" alt="Pablo 'merKur' Kohan"/><br /><sub><b>Pablo 'merKur' Kohan</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=PabloKohan" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hshore29"><img src="https://avatars2.githubusercontent.com/u/7023497?v=4?s=75" width="75px;" alt="hshore29"/><br /><sub><b>hshore29</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=hshore29" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://3e.org/"><img src="https://avatars0.githubusercontent.com/u/41439?v=4?s=75" width="75px;" alt="Daniel M. Drucker"/><br /><sub><b>Daniel M. Drucker</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dmd" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Admd" title="Bug reports">🐛</a> <a href="#userTesting-dmd" title="User Testing">📓</a> <a href="#ideas-dmd" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jystervinou"><img src="https://avatars3.githubusercontent.com/u/132356?v=4?s=75" width="75px;" alt="Jean-Yves Stervinou"/><br /><sub><b>Jean-Yves Stervinou</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=jystervinou" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://dethi.me/"><img src="https://avatars2.githubusercontent.com/u/1011520?v=4?s=75" width="75px;" alt="Thibault Deutsch"/><br /><sub><b>Thibault Deutsch</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dethi" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/grundsch"><img src="https://avatars0.githubusercontent.com/u/3874928?v=4?s=75" width="75px;" alt="grundsch"/><br /><sub><b>grundsch</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=grundsch" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/agprimatic"><img src="https://avatars1.githubusercontent.com/u/4685054?v=4?s=75" width="75px;" alt="Ag Primatic"/><br /><sub><b>Ag Primatic</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=agprimatic" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hhoeck"><img src="https://avatars1.githubusercontent.com/u/6313998?v=4?s=75" width="75px;" alt="Horst Höck"/><br /><sub><b>Horst Höck</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=hhoeck" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jstrine"><img src="https://avatars1.githubusercontent.com/u/33943447?v=4?s=75" width="75px;" alt="Jonathan Strine"/><br /><sub><b>Jonathan Strine</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=jstrine" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/finestream"><img src="https://avatars1.githubusercontent.com/u/16638513?v=4?s=75" width="75px;" alt="finestream"/><br /><sub><b>finestream</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=finestream" title="Documentation">📖</a> <a href="#ideas-finestream" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Afinestream" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/synox"><img src="https://avatars2.githubusercontent.com/u/2250964?v=4?s=75" width="75px;" alt="Aravindo Wingeier"/><br /><sub><b>Aravindo Wingeier</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=synox" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://kradalby.no"><img src="https://avatars1.githubusercontent.com/u/98431?v=4?s=75" width="75px;" alt="Kristoffer Dalby"/><br /><sub><b>Kristoffer Dalby</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=kradalby" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Rott-Apple"><img src="https://avatars1.githubusercontent.com/u/67875570?v=4?s=75" width="75px;" alt="Rott-Apple"/><br /><sub><b>Rott-Apple</b></sub></a><br /><a href="#research-Rott-Apple" title="Research">🔬</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/narensankar0529"><img src="https://avatars3.githubusercontent.com/u/74054766?v=4?s=75" width="75px;" alt="narensankar0529"/><br /><sub><b>narensankar0529</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Anarensankar0529" title="Bug reports">🐛</a> <a href="#userTesting-narensankar0529" title="User Testing">📓</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/martinhrpi"><img src="https://avatars2.githubusercontent.com/u/19407684?v=4?s=75" width="75px;" alt="Martin"/><br /><sub><b>Martin</b></sub></a><br /><a href="#research-martinhrpi" title="Research">🔬</a> <a href="#userTesting-martinhrpi" title="User Testing">📓</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/davidjroos"><img src="https://avatars.githubusercontent.com/u/15630844?v=4?s=75" width="75px;" alt="davidjroos "/><br /><sub><b>davidjroos </b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=davidjroos" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://neilpa.me"><img src="https://avatars.githubusercontent.com/u/42419?v=4?s=75" width="75px;" alt="Neil Pankey"/><br /><sub><b>Neil Pankey</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=neilpa" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aneilpa" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://aaronweb.net/"><img src="https://avatars.githubusercontent.com/u/604665?v=4?s=75" width="75px;" alt="Aaron van Geffen"/><br /><sub><b>Aaron van Geffen</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=AaronVanGeffen" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ubrandes"><img src="https://avatars.githubusercontent.com/u/59647284?v=4?s=75" width="75px;" alt="ubrandes "/><br /><sub><b>ubrandes </b></sub></a><br /><a href="#ideas-ubrandes" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://blog.dewost.com/"><img src="https://avatars.githubusercontent.com/u/17090228?v=4?s=75" width="75px;" alt="Philippe Dewost"/><br /><sub><b>Philippe Dewost</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=pdewost" title="Documentation">📖</a> <a href="#example-pdewost" title="Examples">💡</a> <a href="#ideas-pdewost" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/kaduskj"><img src="https://avatars.githubusercontent.com/u/983067?v=4?s=75" width="75px;" alt="kaduskj"/><br /><sub><b>kaduskj</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Akaduskj" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mkirkland4874"><img src="https://avatars.githubusercontent.com/u/36466711?v=4?s=75" width="75px;" alt="mkirkland4874"/><br /><sub><b>mkirkland4874</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Amkirkland4874" title="Bug reports">🐛</a> <a href="#example-mkirkland4874" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jcommisso07"><img src="https://avatars.githubusercontent.com/u/3111054?v=4?s=75" width="75px;" alt="Joseph Commisso"/><br /><sub><b>Joseph Commisso</b></sub></a><br /><a href="#data-jcommisso07" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dssinger"><img src="https://avatars.githubusercontent.com/u/1817903?v=4?s=75" width="75px;" alt="David Singer"/><br /><sub><b>David Singer</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Adssinger" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/oPromessa"><img src="https://avatars.githubusercontent.com/u/21261491?v=4?s=75" width="75px;" alt="oPromessa"/><br /><sub><b>oPromessa</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AoPromessa" title="Bug reports">🐛</a> <a href="#ideas-oPromessa" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=oPromessa" title="Tests">⚠️</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=oPromessa" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=oPromessa" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://spencerchang.me"><img src="https://avatars.githubusercontent.com/u/14796580?v=4?s=75" width="75px;" alt="Spencer Chang"/><br /><sub><b>Spencer Chang</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aspencerc99" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.cs.purdue.edu/homes/dgleich"><img src="https://avatars.githubusercontent.com/u/33995?v=4?s=75" width="75px;" alt="David Gleich"/><br /><sub><b>David Gleich</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dgleich" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://alandefreitas.github.io/alandefreitas/"><img src="https://avatars.githubusercontent.com/u/5369819?v=4?s=75" width="75px;" alt="Alan de Freitas"/><br /><sub><b>Alan de Freitas</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aalandefreitas" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://hyfen.net"><img src="https://avatars.githubusercontent.com/u/6291?v=4?s=75" width="75px;" alt="Andrew Louis"/><br /><sub><b>Andrew Louis</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=hyfen" title="Documentation">📖</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=hyfen" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/neebah"><img src="https://avatars.githubusercontent.com/u/71442026?v=4?s=75" width="75px;" alt="neebah"/><br /><sub><b>neebah</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aneebah" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ahti123"><img src="https://avatars.githubusercontent.com/u/22232632?v=4?s=75" width="75px;" alt="Ahti Liin"/><br /><sub><b>Ahti Liin</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=ahti123" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aahti123" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/xwu64"><img src="https://avatars.githubusercontent.com/u/10580396?v=4?s=75" width="75px;" alt="Xiaoliang Wu"/><br /><sub><b>Xiaoliang Wu</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=xwu64" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/nullpointerninja"><img src="https://avatars.githubusercontent.com/u/62975432?v=4?s=75" width="75px;" alt="nullpointerninja"/><br /><sub><b>nullpointerninja</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Anullpointerninja" title="Bug reports">🐛</a> <a href="#ideas-nullpointerninja" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/infused-kim"><img src="https://avatars.githubusercontent.com/u/7404004?v=4?s=75" width="75px;" alt="Kim"/><br /><sub><b>Kim</b></sub></a><br /><a href="#ideas-infused-kim" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Se7enair"><img src="https://avatars.githubusercontent.com/u/1680106?v=4?s=75" width="75px;" alt="Christoph"/><br /><sub><b>Christoph</b></sub></a><br /><a href="#ideas-Se7enair" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.franzone.com"><img src="https://avatars.githubusercontent.com/u/900684?v=4?s=75" width="75px;" alt="franzone"/><br /><sub><b>franzone</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Afranzone" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://jmuccigr.github.io/"><img src="https://avatars.githubusercontent.com/u/615115?v=4?s=75" width="75px;" alt="John Muccigrosso"/><br /><sub><b>John Muccigrosso</b></sub></a><br /><a href="#ideas-jmuccigr" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://nomadgate.com"><img src="https://avatars.githubusercontent.com/u/1646041?v=4?s=75" width="75px;" alt="Thomas K. Running"/><br /><sub><b>Thomas K. Running</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=tkrunning" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Atkrunning" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://dalisoft.uz"><img src="https://avatars.githubusercontent.com/u/3511344?v=4?s=75" width="75px;" alt="Davlatjon Shavkatov"/><br /><sub><b>Davlatjon Shavkatov</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dalisoft" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=dalisoft" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/zephyr325"><img src="https://avatars.githubusercontent.com/u/5245609?v=4?s=75" width="75px;" alt="zephyr325"/><br /><sub><b>zephyr325</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Azephyr325" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/drodner"><img src="https://avatars.githubusercontent.com/u/10236892?v=4?s=75" width="75px;" alt="drodner"/><br /><sub><b>drodner</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Adrodner" title="Bug reports">🐛</a> <a href="#userTesting-drodner" title="User Testing">📓</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://fmckeogh.github.io"><img src="https://avatars.githubusercontent.com/u/8290136?v=4?s=75" width="75px;" alt="Ferdia McKeogh"/><br /><sub><b>Ferdia McKeogh</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=fmckeogh" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Afmckeogh" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://wellsaidlabs.com"><img src="https://avatars.githubusercontent.com/u/7424737?v=4?s=75" width="75px;" alt="Michael Petrochuk"/><br /><sub><b>Michael Petrochuk</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3APetrochukM" title="Bug reports">🐛</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=PetrochukM" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://qkeddy.github.io/quin-eddy-development-portfolio/"><img src="https://avatars.githubusercontent.com/u/9737814?v=4?s=75" width="75px;" alt="Quin Eddy"/><br /><sub><b>Quin Eddy</b></sub></a><br /><a href="#ideas-qkeddy" title="Ideas, Planning, & Feedback">🤔</a> <a href="#data-qkeddy" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/johnsturgeon"><img src="https://avatars.githubusercontent.com/u/9746310?v=4?s=75" width="75px;" alt="John Sturgeon"/><br /><sub><b>John Sturgeon</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Ajohnsturgeon" title="Bug reports">🐛</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=johnsturgeon" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mave2k"><img src="https://avatars.githubusercontent.com/u/8629837?v=4?s=75" width="75px;" alt="mave2k"/><br /><sub><b>mave2k</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=mave2k" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://danielbeadle.net"><img src="https://avatars.githubusercontent.com/u/6235378?v=4?s=75" width="75px;" alt="Daniel Beadle"/><br /><sub><b>Daniel Beadle</b></sub></a><br /><a href="#ideas-djbeadle" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://eecue.com/"><img src="https://avatars.githubusercontent.com/u/532536?v=4?s=75" width="75px;" alt="Dave Bullock"/><br /><sub><b>Dave Bullock</b></sub></a><br /><a href="#ideas-eecue" title="Ideas, Planning, & Feedback">🤔</a> <a href="#userTesting-eecue" title="User Testing">📓</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aeecue" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pweaver"><img src="https://avatars.githubusercontent.com/u/611620?v=4?s=75" width="75px;" alt="Pweaver"/><br /><sub><b>Pweaver</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Apweaver" title="Bug reports">🐛</a> <a href="#ideas-pweaver" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/aa599"><img src="https://avatars.githubusercontent.com/u/37746269?v=4?s=75" width="75px;" alt="aa599"/><br /><sub><b>aa599</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aaa599" title="Bug reports">🐛</a> <a href="#ideas-aa599" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/swduncan"><img src="https://avatars.githubusercontent.com/u/2053195?v=4?s=75" width="75px;" alt="Steve Duncan"/><br /><sub><b>Steve Duncan</b></sub></a><br /><a href="#ideas-swduncan" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.projany.com"><img src="https://avatars.githubusercontent.com/u/15144745?v=4?s=75" width="75px;" alt="Ian Moir"/><br /><sub><b>Ian Moir</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aianmmoir" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pekingduck"><img src="https://avatars.githubusercontent.com/u/2597142?v=4?s=75" width="75px;" alt="Peking Duck"/><br /><sub><b>Peking Duck</b></sub></a><br /><a href="#ideas-pekingduck" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Apekingduck" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.patreon.com/cclauss"><img src="https://avatars.githubusercontent.com/u/3709715?v=4?s=75" width="75px;" alt="Christian Clauss"/><br /><sub><b>Christian Clauss</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=cclauss" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dvdkon"><img src="https://avatars.githubusercontent.com/u/3526303?v=4?s=75" width="75px;" alt="dvdkon"/><br /><sub><b>dvdkon</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dvdkon" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/wernerzj"><img src="https://avatars.githubusercontent.com/u/130370930?v=4?s=75" width="75px;" alt="wernerzj"/><br /><sub><b>wernerzj</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Awernerzj" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/rajscode"><img src="https://avatars.githubusercontent.com/u/99123253?v=4?s=75" width="75px;" alt="rajscode"/><br /><sub><b>rajscode</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Arajscode" title="Bug reports">🐛</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=rajscode" title="Documentation">📖</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=rajscode" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/MaxLyt"><img src="https://avatars.githubusercontent.com/u/136200430?v=4?s=75" width="75px;" alt="MaxLyt"/><br /><sub><b>MaxLyt</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AMaxLyt" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ces3001"><img src="https://avatars.githubusercontent.com/u/23762610?v=4?s=75" width="75px;" alt="ces3001"/><br /><sub><b>ces3001</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aces3001" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/msolo"><img src="https://avatars.githubusercontent.com/u/5078276?v=4?s=75" width="75px;" alt="msolo"/><br /><sub><b>msolo</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Amsolo" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://trygvevea.com"><img src="https://avatars.githubusercontent.com/u/141714?v=4?s=75" width="75px;" alt="Trygve Vea"/><br /><sub><b>Trygve Vea</b></sub></a><br /><a href="#userTesting-kvisle" title="User Testing">📓</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hydrrrrr"><img src="https://avatars.githubusercontent.com/u/144631381?v=4?s=75" width="75px;" alt="hydrrrrr"/><br /><sub><b>hydrrrrr</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Ahydrrrrr" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/devlarosa"><img src="https://avatars.githubusercontent.com/u/3469731?v=4?s=75" width="75px;" alt="Javier"/><br /><sub><b>Javier</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Adevlarosa" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://catap.ru/blog/"><img src="https://avatars.githubusercontent.com/u/37775?v=4?s=75" width="75px;" alt="Kirill A. Korinsky"/><br /><sub><b>Kirill A. Korinsky</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=catap" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://breun.nl/"><img src="https://avatars.githubusercontent.com/u/102921?v=4?s=75" width="75px;" alt="Nils Breunese"/><br /><sub><b>Nils Breunese</b></sub></a><br /><a href="#maintenance-breun" title="Maintenance">🚧</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=breun" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/420gofOGKush"><img src="https://avatars.githubusercontent.com/u/144961214?v=4?s=75" width="75px;" alt="420gofOGKush"/><br /><sub><b>420gofOGKush</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3A420gofOGKush" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://tja.lv/e"><img src="https://avatars.githubusercontent.com/u/39051?v=4?s=75" width="75px;" alt="Tjalve Aarflot"/><br /><sub><b>Tjalve Aarflot</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AZarK" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mikapietrus"><img src="https://avatars.githubusercontent.com/u/62189731?v=4?s=75" width="75px;" alt="mikapietrus"/><br /><sub><b>mikapietrus</b></sub></a><br /><a href="#ideas-mikapietrus" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/santiagoGPNC"><img src="https://avatars.githubusercontent.com/u/143808451?v=4?s=75" width="75px;" alt="santiagoGPNC"/><br /><sub><b>santiagoGPNC</b></sub></a><br /><a href="#ideas-santiagoGPNC" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/nkxco"><img src="https://avatars.githubusercontent.com/u/147254285?v=4?s=75" width="75px;" alt="nkxco"/><br /><sub><b>nkxco</b></sub></a><br /><a href="#ideas-nkxco" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/nicad"><img src="https://avatars.githubusercontent.com/u/1311134?v=4?s=75" width="75px;" alt="nicad"/><br /><sub><b>nicad</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=nicad" title="Documentation">📖</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=nicad" title="Tests">⚠️</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Anicad" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mikekenyon99"><img src="https://avatars.githubusercontent.com/u/42475982?v=4?s=75" width="75px;" alt="Mike Kenyon"/><br /><sub><b>Mike Kenyon</b></sub></a><br /><a href="#ideas-mikekenyon99" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Amikekenyon99" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/LunarLanding"><img src="https://avatars.githubusercontent.com/u/4441338?v=4?s=75" width="75px;" alt="LunarLanding"/><br /><sub><b>LunarLanding</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=LunarLanding" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3ALunarLanding" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mlevin77"><img src="https://avatars.githubusercontent.com/u/36042498?v=4?s=75" width="75px;" alt="mlevin77"/><br /><sub><b>mlevin77</b></sub></a><br /><a href="#ideas-mlevin77" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://axka.fi"><img src="https://avatars.githubusercontent.com/u/120189068?v=4?s=75" width="75px;" alt="Axel Karjalainen"/><br /><sub><b>Axel Karjalainen</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=axelkar" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/kitschpatrol"><img src="https://avatars.githubusercontent.com/u/194164?v=4?s=75" width="75px;" alt="Eric Mika"/><br /><sub><b>Eric Mika</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Akitschpatrol" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://odedia.org"><img src="https://avatars.githubusercontent.com/u/2992180?v=4?s=75" width="75px;" alt="odedia"/><br /><sub><b>odedia</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aodedia" title="Bug reports">🐛</a> <a href="#ideas-odedia" title="Ideas, Planning, & Feedback">🤔</a> <a href="#research-odedia" title="Research">🔬</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/torarnv"><img src="https://avatars.githubusercontent.com/u/7536?v=4?s=75" width="75px;" alt="Tor Arne Vestbø"/><br /><sub><b>Tor Arne Vestbø</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Atorarnv" title="Bug reports">🐛</a> <a href="#research-torarnv" title="Research">🔬</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=torarnv" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=torarnv" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/garz75"><img src="https://avatars.githubusercontent.com/u/6645395?v=4?s=75" width="75px;" alt="Frederic Garzon"/><br /><sub><b>Frederic Garzon</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Agarz75" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/felciano"><img src="https://avatars.githubusercontent.com/u/407700?v=4?s=75" width="75px;" alt="Ramon Felciano"/><br /><sub><b>Ramon Felciano</b></sub></a><br /><a href="#research-felciano" title="Research">🔬</a> <a href="#ideas-felciano" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dweston"><img src="https://avatars.githubusercontent.com/u/631241?v=4?s=75" width="75px;" alt="Dion Weston"/><br /><sub><b>Dion Weston</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=dweston" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://andyblyler.com"><img src="https://avatars.githubusercontent.com/u/137642?v=4?s=75" width="75px;" alt="Andy Blyler"/><br /><sub><b>Andy Blyler</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=ablyler" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/lasjoe"><img src="https://avatars.githubusercontent.com/u/91013368?v=4?s=75" width="75px;" alt="lasjoe"/><br /><sub><b>lasjoe</b></sub></a><br /><a href="#data-lasjoe" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://daniel-vogelnest.tk"><img src="https://avatars.githubusercontent.com/u/4771860?v=4?s=75" width="75px;" alt="Daniel Vogelnest"/><br /><sub><b>Daniel Vogelnest</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AdanVnest" title="Bug reports">🐛</a> <a href="#data-danVnest" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/alban73"><img src="https://avatars.githubusercontent.com/u/74853805?v=4?s=75" width="75px;" alt="alban73"/><br /><sub><b>alban73</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aalban73" title="Bug reports">🐛</a> <a href="#data-alban73" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/justaLoli"><img src="https://avatars.githubusercontent.com/u/92238102?v=4?s=75" width="75px;" alt="justaLoli"/><br /><sub><b>justaLoli</b></sub></a><br /><a href="#ideas-justaLoli" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/arthurward"><img src="https://avatars.githubusercontent.com/u/8432358?v=4?s=75" width="75px;" alt="arthurward"/><br /><sub><b>arthurward</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Aarthurward" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/svet-b"><img src="https://avatars.githubusercontent.com/u/12831860?v=4?s=75" width="75px;" alt="svet-b"/><br /><sub><b>svet-b</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Asvet-b" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Syntaxheld"><img src="https://avatars.githubusercontent.com/u/6772181?v=4?s=75" width="75px;" alt="Syntaxheld"/><br /><sub><b>Syntaxheld</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3ASyntaxheld" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://christiansievers.info"><img src="https://avatars.githubusercontent.com/u/20228200?v=4?s=75" width="75px;" alt="Christian Sievers"/><br /><sub><b>Christian Sievers</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=christiansievers" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mravery"><img src="https://avatars.githubusercontent.com/u/1683929?v=4?s=75" width="75px;" alt="Avery Chan"/><br /><sub><b>Avery Chan</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Amravery" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dobernhardt"><img src="https://avatars.githubusercontent.com/u/57567625?v=4?s=75" width="75px;" alt="dobernhardt"/><br /><sub><b>dobernhardt</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Adobernhardt" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JxxIT"><img src="https://avatars.githubusercontent.com/u/110342008?v=4?s=75" width="75px;" alt="JxxIT"/><br /><sub><b>JxxIT</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AJxxIT" title="Bug reports">🐛</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=JxxIT" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/KeyPlayerMaek"><img src="https://avatars.githubusercontent.com/u/25553779?v=4?s=75" width="75px;" alt="Marek Toth"/><br /><sub><b>Marek Toth</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AKeyPlayerMaek" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pl804"><img src="https://avatars.githubusercontent.com/u/101955060?v=4?s=75" width="75px;" alt="pl804"/><br /><sub><b>pl804</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=pl804" title="Tests">⚠️</a> <a href="#data-pl804" title="Data">🔣</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cstaubli"><img src="https://avatars.githubusercontent.com/u/6720436?v=4?s=75" width="75px;" alt="Christian Staubli"/><br /><sub><b>Christian Staubli</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Acstaubli" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://yazdanra.com"><img src="https://avatars.githubusercontent.com/u/32798567?v=4?s=75" width="75px;" alt="Yazdan Ranjbar"/><br /><sub><b>Yazdan Ranjbar</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=YazdanRa" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/m-reiter"><img src="https://avatars.githubusercontent.com/u/5221258?v=4?s=75" width="75px;" alt="m-reiter"/><br /><sub><b>m-reiter</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Am-reiter" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.mherzberg.de"><img src="https://avatars.githubusercontent.com/u/12444544?v=4?s=75" width="75px;" alt="Michael Herzberg"/><br /><sub><b>Michael Herzberg</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Amherzberg" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://toot.lv/@eriks"><img src="https://avatars.githubusercontent.com/u/176241?v=4?s=75" width="75px;" alt="Ēriks Remess"/><br /><sub><b>Ēriks Remess</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=EriksRemess" title="Code">💻</a> <a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AEriksRemess" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pkaila"><img src="https://avatars.githubusercontent.com/u/870219?v=4?s=75" width="75px;" alt="pkaila"/><br /><sub><b>pkaila</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/commits?author=pkaila" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ZeliTheZealot"><img src="https://avatars.githubusercontent.com/u/19900255?v=4?s=75" width="75px;" alt="ZeliTheZealot"/><br /><sub><b>ZeliTheZealot</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3AZeliTheZealot" title="Bug reports">🐛</a> <a href="https://github.com/RhetTbull/osxphotos/commits?author=ZeliTheZealot" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/benw-git"><img src="https://avatars.githubusercontent.com/u/85592899?v=4?s=75" width="75px;" alt="benw-git"/><br /><sub><b>benw-git</b></sub></a><br /><a href="https://github.com/RhetTbull/osxphotos/issues?q=author%3Abenw-git" title="Bug reports">🐛</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Known Bugs and Limitations

My goal is make osxphotos as reliable and comprehensive as possible.  The test suite currently has over 800 tests--but there are still some [bugs](https://github.com/RhetTbull/osxphotos/issues?q=is%3Aissue+is%3Aopen+label%3Abug) or incomplete features lurking.  If you find bugs please open an [issue](https://github.com/RhetTbull/osxphotos/issues).  Please consult the list of open bugs before deciding that you want to use this code on your Photos library.  Notable issues include:

* Audio-only files are not handled.  It is possible to store audio-only files in Photos.  osxphotos currently only handles images and videos. See [Issue #436](https://github.com/RhetTbull/osxphotos/issues/436)
* Face coordinates (mouth, left eye, right eye) may not be correct for images where the head is tilted.  See [Issue #196](https://github.com/RhetTbull/osxphotos/issues/196).
* The `--download-missing` option for `osxphotos export` does not work correctly with burst images.  It will download the primary image but not the other burst images.  See [Issue #75](https://github.com/RhetTbull/osxphotos/issues/75).

## Implementation Notes

This package works by creating a copy of the sqlite3 database that photos uses to store data about the photos library. The class PhotosDB then queries this database to extract information about the photos such as persons (faces identified in the photos), albums, keywords, etc.  If your library is large, the database can be hundreds of MB in size and the copy read then can take many 10s of seconds to complete.  Once copied, the entire database is processed and an in-memory data structure is created meaning all subsequent accesses of the PhotosDB object occur much more quickly. The database processing code is rather ugly (though it works and is well tested).  Were I to start this project today, I'd likely use something like SQLAlchemy to map Python objects to the underlying SQL database instead of the way osxphotos does things today.

If apple changes the database format this will likely break.

For additional details about how osxphotos is implemented or if you would like to extend the code, see the [wiki](https://github.com/RhetTbull/osxphotos/wiki).

## Acknowledgements

This project was originally inspired by [photo-export](https://github.com/patrikhson/photo-export) by Patrick Fältström,  Copyright (c) 2015 Patrik Fältström paf@frobbit.se

I use [py-applescript](https://github.com/rdhyee/py-applescript) by "Raymond Yee / rdhyee" to interact with Photos. Rather than import this package, I included the entire package (which is published as public domain code) in a private package to prevent ambiguity with other applescript packages on PyPi. py-applescript uses a native bridge via PyObjC and is very fast compared to the other osascript based packages.
