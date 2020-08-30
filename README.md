# OSXPhotos

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python package](https://github.com/RhetTbull/osxphotos/workflows/Python%20package/badge.svg)

- [OSXPhotos](#osxphotos)
  * [What is osxphotos?](#what-is-osxphotos)
  * [Supported operating systems](#supported-operating-systems)
  * [Installation instructions](#installation-instructions)
  * [Command Line Usage](#command-line-usage)
  * [Example uses of the package](#example-uses-of-the-package)
  * [Package Interface](#package-interface)
    + [PhotosDB](#photosdb)
    + [PhotoInfo](#photoinfo)
    + [ExifInfo](#exifinfo)
    + [AlbumInfo](#albuminfo)
    + [ImportInfo](#importinfo)
    + [FolderInfo](#folderinfo)
    + [PlaceInfo](#placeinfo)
    + [ScoreInfo](#scoreinfo)
    + [PersonInfo](#personinfo)
    + [FaceInfo](#faceinfo)
    + [Template Substitutions](#template-substitutions)
    + [Utility Functions](#utility-functions)
  * [Examples](#examples)
  * [Related Projects](#related-projects)
  * [Contributing](#contributing)
  * [Known Bugs](#known-bugs)
  * [Implementation Notes](#implementation-notes)
  * [Dependencies](#dependencies)
  * [Acknowledgements](#acknowledgements)

  
## What is osxphotos?

OSXPhotos provides the ability to interact with and query Apple's Photos.app library database on MacOS. Using this package you can query the Photos database for information about the photos stored in a Photos library on your Mac--for example, file name, file path, and metadata such as keywords/tags, persons/faces, albums, etc. You can also easily export both the original and edited photos.

## Supported operating systems

Only works on MacOS (aka Mac OS X). Tested on MacOS 10.12.6 / Photos 2.0, 10.13.6 / Photos 3.0, MacOS 10.14.5, 10.14.6 / Photos 4.0, MacOS 10.15.1 - 10.15.6 / Photos 5.0.

Alpha support for MacOS 10.16/MacOS 11 Big Sur Beta / Photos 6.0.

Requires python >= 3.7. 

This package will read Photos databases for any supported version on any supported OS version.  E.g. you can read a database created with Photos 4.0 on MacOS 10.14 on a machine running MacOS 10.12.


## Installation instructions

OSXPhotos uses setuptools, thus simply run:

	python3 setup.py install

You can also install directly from [pypi](https://pypi.org/project/osxphotos/):

    pip install osxphotos
	
**WARNING** The git repo for this project is very large (> 1GB) because it contains multiple Photos libraries used for testing on different versions of MacOS.  If you just want to use the osxphotos package in your own code, I recommend you install the latest version from [PyPI](https://pypi.org/project/osxphotos/). If you just want to use the command line utility, you can download a pre-built executable of the latest [release](https://github.com/RhetTbull/osxphotos/releases) or you can install via `pip` which also installs the command line app.  If you aren't comfortable with running python on your Mac, start with the pre-built executable.

## Command Line Usage

This package will install a command line utility called `osxphotos` that allows you to query the Photos database.  Alternatively, you can also run the command line utility like this: `python3 -m osxphotos`

If you only care about the command line tool, you can download an executable of the latest [release](https://github.com/RhetTbull/osxphotos/releases).  Alternatively, I recommend installing with [pipx](https://github.com/pipxproject/pipx)

After installing pipx:
`pipx install osxphotos`

Then you should be able to run `osxphotos` on the command line:

```
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
```

To get help on a specific command, use `osxphotos help <command_name>`

Example: `osxphotos help export`

```
Usage: osxphotos export [OPTIONS] [PHOTOS_LIBRARY]... DEST

  Export photos from the Photos database. Export path DEST is required.
  Optionally, query the Photos database using 1 or more search options;  if
  more than one option is provided, they are treated as "AND"  (e.g. search
  for photos matching all options). If no query options are provided, all
  photos will be exported. By default, all versions of all photos will be
  exported including edited versions, live photo movies, burst photos, and
  associated RAW images.  See --skip-edited, --skip-live, --skip-bursts, and
  --skip-raw options to modify this behavior.

Options:
  --db <Photos database path>     Specify Photos database path. Path to Photos
                                  library/database can be specified using
                                  either --db or directly as PHOTOS_LIBRARY
                                  positional argument. If neither --db or
                                  PHOTOS_LIBRARY provided, will attempt to
                                  find the library to use in the following
                                  order: 1. last opened library, 2. system
                                  library, 3. ~/Pictures/Photos
                                  Library.photoslibrary
  -V, --verbose                   Print verbose output.
  --keyword KEYWORD               Search for photos with keyword KEYWORD. If
                                  more than one keyword, treated as "OR", e.g.
                                  find photos matching any keyword
  --person PERSON                 Search for photos with person PERSON. If
                                  more than one person, treated as "OR", e.g.
                                  find photos matching any person
  --album ALBUM                   Search for photos in album ALBUM. If more
                                  than one album, treated as "OR", e.g. find
                                  photos matching any album
  --folder FOLDER                 Search for photos in an album in folder
                                  FOLDER. If more than one folder, treated as
                                  "OR", e.g. find photos in any FOLDER.  Only
                                  searches top level folders (e.g. does not
                                  look at subfolders)
  --uuid UUID                     Search for photos with UUID(s).
  --uuid-from-file FILE           Search for photos with UUID(s) loaded from
                                  FILE. Format is a single UUID per line.
                                  Lines preceeded with # are ignored.
  --title TITLE                   Search for TITLE in title of photo.
  --no-title                      Search for photos with no title.
  --description DESC              Search for DESC in description of photo.
  --no-description                Search for photos with no description.
  --place PLACE                   Search for PLACE in photo's reverse
                                  geolocation info
  --no-place                      Search for photos with no associated place
                                  name info (no reverse geolocation info)
  --label LABEL                   Search for photos with image classification
                                  label LABEL (Photos 5 only). If more than
                                  one label, treated as "OR", e.g. find photos
                                  matching any label
  --uti UTI                       Search for photos whose uniform type
                                  identifier (UTI) matches UTI
  -i, --ignore-case               Case insensitive search for title,
                                  description, place, keyword, person, or
                                  album.
  --edited                        Search for photos that have been edited.
  --external-edit                 Search for photos edited in external editor.
  --favorite                      Search for photos marked favorite.
  --not-favorite                  Search for photos not marked favorite.
  --hidden                        Search for photos marked hidden.
  --not-hidden                    Search for photos not marked hidden.
  --shared                        Search for photos in shared iCloud album
                                  (Photos 5 only).
  --not-shared                    Search for photos not in shared iCloud album
                                  (Photos 5 only).
  --burst                         Search for photos that were taken in a
                                  burst.
  --not-burst                     Search for photos that are not part of a
                                  burst.
  --live                          Search for Apple live photos
  --not-live                      Search for photos that are not Apple live
                                  photos.
  --portrait                      Search for Apple portrait mode photos.
  --not-portrait                  Search for photos that are not Apple
                                  portrait mode photos.
  --screenshot                    Search for screenshot photos.
  --not-screenshot                Search for photos that are not screenshot
                                  photos.
  --slow-mo                       Search for slow motion videos.
  --not-slow-mo                   Search for photos that are not slow motion
                                  videos.
  --time-lapse                    Search for time lapse videos.
  --not-time-lapse                Search for photos that are not time lapse
                                  videos.
  --hdr                           Search for high dynamic range (HDR) photos.
  --not-hdr                       Search for photos that are not HDR photos.
  --selfie                        Search for selfies (photos taken with front-
                                  facing cameras).
  --not-selfie                    Search for photos that are not selfies.
  --panorama                      Search for panorama photos.
  --not-panorama                  Search for photos that are not panoramas.
  --has-raw                       Search for photos with both a jpeg and RAW
                                  version
  --only-movies                   Search only for movies (default searches
                                  both images and movies).
  --only-photos                   Search only for photos/images (default
                                  searches both images and movies).
  --from-date DATETIME            Search by start item date, e.g.
                                  2000-01-12T12:00:00,
                                  2001-01-12T12:00:00-07:00, or 2000-12-31
                                  (ISO 8601).
  --to-date DATETIME              Search by end item date, e.g.
                                  2000-01-12T12:00:00,
                                  2001-01-12T12:00:00-07:00, or 2000-12-31
                                  (ISO 8601).
  --deleted                       Include photos from the 'Recently Deleted'
                                  folder.
  --deleted-only                  Include only photos from the 'Recently
                                  Deleted' folder.
  --update                        Only export new or updated files. See notes
                                  below on export and --update.
  --dry-run                       Dry run (test) the export but don't actually
                                  export any files; most useful with --verbose
  --export-as-hardlink            Hardlink files instead of copying them.
                                  Cannot be used with --exiftool which creates
                                  copies of the files with embedded EXIF data.
  --touch-file                    Sets the file's modification time to match
                                  photo date.
  --overwrite                     Overwrite existing files. Default behavior
                                  is to add (1), (2), etc to filename if file
                                  already exists. Use this with caution as it
                                  may create name collisions on export. (e.g.
                                  if two files happen to have the same name)
  --export-by-date                Automatically create output folders to
                                  organize photos by date created (e.g.
                                  DEST/2019/12/20/photoname.jpg).
  --skip-edited                   Do not export edited version of photo if an
                                  edited version exists.
  --skip-bursts                   Do not export all associated burst images in
                                  the library if a photo is a burst photo.
  --skip-live                     Do not export the associated live video
                                  component of a live photo.
  --skip-raw                      Do not export associated RAW images of a
                                  RAW/jpeg pair.  Note: this does not skip RAW
                                  photos if the RAW photo does not have an
                                  associated jpeg image (e.g. the RAW file was
                                  imported to Photos without a jpeg preview).
  --person-keyword                Use person in image as keyword/tag when
                                  exporting metadata.
  --album-keyword                 Use album name as keyword/tag when exporting
                                  metadata.
  --keyword-template TEMPLATE     For use with --exiftool, --sidecar; specify
                                  a template string to use as keyword in the
                                  form '{name,DEFAULT}' This is the same
                                  format as --directory.  For example, if you
                                  wanted to add the full path to the folder
                                  and album photo is contained in as a keyword
                                  when exporting you could specify --keyword-
                                  template "{folder_album}" You may specify
                                  more than one template, for example
                                  --keyword-template "{folder_album}"
                                  --keyword-template "{created.year}" See
                                  Templating System below.
  --description-template TEMPLATE
                                  For use with --exiftool, --sidecar; specify
                                  a template string to use as description in
                                  the form '{name,DEFAULT}' This is the same
                                  format as --directory.  For example, if you
                                  wanted to append 'exported with osxphotos on
                                  [today's date]' to the description, you
                                  could specify --description-template
                                  "{descr} exported with osxphotos on
                                  {today.date}" See Templating System below.
  --current-name                  Use photo's current filename instead of
                                  original filename for export.  Note:
                                  Starting with Photos 5, all photos are
                                  renamed upon import.  By default, photos are
                                  exported with the the original name they had
                                  before import.
  --sidecar FORMAT                Create sidecar for each photo exported;
                                  valid FORMAT values: xmp, json; --sidecar
                                  json: create JSON sidecar useable by
                                  exiftool (https://exiftool.org/) The sidecar
                                  file can be used to apply metadata to the
                                  file with exiftool, for example: "exiftool
                                  -j=photoname.json photoname.jpg" The sidecar
                                  file is named in format photoname.json
                                  --sidecar xmp: create XMP sidecar used by
                                  Adobe Lightroom, etc.The sidecar file is
                                  named in format photoname.xmp
  --download-missing              Attempt to download missing photos from
                                  iCloud. The current implementation uses
                                  Applescript to interact with Photos to
                                  export the photo which will force Photos to
                                  download from iCloud if the photo does not
                                  exist on disk.  This will be slow and will
                                  require internet connection. This obviously
                                  only works if the Photos library is synched
                                  to iCloud.  Note: --download-missing does
                                  not currently export all burst images; only
                                  the primary photo will be exported--
                                  associated burst images will be skipped.
  --exiftool                      Use exiftool to write metadata directly to
                                  exported photos. To use this option,
                                  exiftool must be installed and in the path.
                                  exiftool may be installed from
                                  https://exiftool.org/.  Cannot be used with
                                  --export-as-hardlink.
  --directory DIRECTORY           Optional template for specifying name of
                                  output directory in the form
                                  '{name,DEFAULT}'. See below for additional
                                  details on templating system.
  --filename FILENAME             Optional template for specifying name of
                                  output file in the form '{name,DEFAULT}'.
                                  File extension will be added automatically--
                                  do not include an extension in the FILENAME
                                  template. See below for additional details
                                  on templating system.
  --edited-suffix SUFFIX          Optional suffix for naming edited photos.
                                  Default name for edited photos is in form
                                  'photoname_edited.ext'. For example, with '
                                  --edited-suffix _bearbeiten', the edited
                                  photo would be named
                                  'photoname_bearbeiten.ext'.  The default
                                  suffix is '_edited'.
  --no-extended-attributes        Don't copy extended attributes when
                                  exporting.  You only need this if exporting
                                  to a filesystem that doesn't support Mac OS
                                  extended attributes.  Only use this if you
                                  get an error while exporting.
  -h, --help                      Show this message and exit.

** Export **
When exporting photos, osxphotos creates a database in the top-level export
folder called '.osxphotos_export.db'.  This database preserves state
information used for determining which files need to be updated when run with
--update.  It is recommended that if you later move the export folder tree you
also move the database file.

The --update option will only copy new or updated files from the library to
the export folder.  If a file is changed in the export folder (for example,
you edited the exported image), osxphotos will detect this as a difference and
re-export the original image from the library thus overwriting the changes.
If using --update, the exported library should be treated as a backup, not a
working copy where you intend to make changes.

Note: The number of files reported for export and the number actually exported
may differ due to live photos, associated RAW images, and edited photos which
are reported in the total photos exported.

Implementation note: To determine which files need to be updated, osxphotos
stores file signature information in the '.osxphotos_export.db' database. The
signature includes size, modification time, and filename.  In order to
minimize run time, --update does not do a full comparison (diff) of the files
nor does it compare hashes of the files.  In normal usage, this is sufficient
for updating the library. You can always run export without the --update
option to re-export the entire library thus rebuilding the
'.osxphotos_export.db' database.


** Templating System **

With the --directory and --filename options you may specify a template for the
export directory or filename, respectively. The directory will be appended to
the export path specified in the export DEST argument to export.  For example,
if template is '{created.year}/{created.month}', and export desitnation DEST
is '/Users/maria/Pictures/export', the actual export directory for a photo
would be '/Users/maria/Pictures/export/2020/March' if the photo was created in
March 2020. Some template substitutions may result in more than one value, for
example '{album}' if photo is in more than one album or '{keyword}' if photo
has more than one keyword. In this case, more than one copy of the photo will
be exported, each in a separate directory or with a different filename.

The templating system may also be used with the --keyword-template option to
set keywords on export (with --exiftool or --sidecar), for example, to set a
new keyword in format 'folder/subfolder/album' to preserve the folder/album
structure, you can use --keyword-template "{folder_album}"

In the template, valid template substitutions will be replaced by the
corresponding value from the table below.  Invalid substitutions will result
in a an error and the script will abort.

If you want the actual text of the template substition to appear in the
rendered name, use double braces, e.g. '{{' or '}}', thus using
'{created.year}/{{name}}' for --directory would result in output of
2020/{name}/photoname.jpg

You may specify an optional default value to use if the substitution does not
contain a value (e.g. the value is null) by specifying the default value after
a ',' in the template string: for example, if template is
'{created.year}/{place.address,NO_ADDRESS}' but there was no address
associated with the photo, the resulting output would be:
'2020/NO_ADDRESS/photoname.jpg'. If specified, the default value may not
contain a brace symbol ('{' or '}').

If you do not specify a default value and the template substitution has no
value, '_' (underscore) will be used as the default value. For example, in the
above example, this would result in '2020/_/photoname.jpg' if address was
null.

Substitution                    Description
{name}                          Current filename of the photo
{original_name}                 Photo's original filename when imported to
                                Photos
{title}                         Title of the photo
{descr}                         Description of the photo
{created.date}                  Photo's creation date in ISO format, e.g.
                                '2020-03-22'
{created.year}                  4-digit year of file creation time
{created.yy}                    2-digit year of file creation time
{created.mm}                    2-digit month of the file creation time
                                (zero padded)
{created.month}                 Month name in user's locale of the file
                                creation time
{created.mon}                   Month abbreviation in the user's locale of
                                the file creation time
{created.dd}                    2-digit day of the month (zero padded) of
                                file creation time
{created.dow}                   Day of week in user's locale of the file
                                creation time
{created.doy}                   3-digit day of year (e.g Julian day) of file
                                creation time, starting from 1 (zero padded)
{created.hour}                  2-digit hour of the file creation time
{created.min}                   2-digit minute of the file creation time
{created.sec}                   2-digit second of the file creation time
{created.strftime}              Apply strftime template to file creation
                                date/time. Should be used in form
                                {created.strftime,TEMPLATE} where TEMPLATE
                                is a valid strftime template, e.g.
                                {created.strftime,%Y-%U} would result in
                                year-week number of year: '2020-23'. If used
                                with no template will return null value. See
                                https://strftime.org/ for help on strftime
                                templates.
{modified.date}                 Photo's modification date in ISO format,
                                e.g. '2020-03-22'
{modified.year}                 4-digit year of file modification time
{modified.yy}                   2-digit year of file modification time
{modified.mm}                   2-digit month of the file modification time
                                (zero padded)
{modified.month}                Month name in user's locale of the file
                                modification time
{modified.mon}                  Month abbreviation in the user's locale of
                                the file modification time
{modified.dd}                   2-digit day of the month (zero padded) of
                                the file modification time
{modified.doy}                  3-digit day of year (e.g Julian day) of file
                                modification time, starting from 1 (zero
                                padded)
{modified.hour}                 2-digit hour of the file modification time
{modified.min}                  2-digit minute of the file modification time
{modified.sec}                  2-digit second of the file modification time
{today.date}                    Current date in iso format, e.g.
                                '2020-03-22'
{today.year}                    4-digit year of current date
{today.yy}                      2-digit year of current date
{today.mm}                      2-digit month of the current date (zero
                                padded)
{today.month}                   Month name in user's locale of the current
                                date
{today.mon}                     Month abbreviation in the user's locale of
                                the current date
{today.dd}                      2-digit day of the month (zero padded) of
                                current date
{today.dow}                     Day of week in user's locale of the current
                                date
{today.doy}                     3-digit day of year (e.g Julian day) of
                                current date, starting from 1 (zero padded)
{today.hour}                    2-digit hour of the current date
{today.min}                     2-digit minute of the current date
{today.sec}                     2-digit second of the current date
{today.strftime}                Apply strftime template to current
                                date/time. Should be used in form
                                {today.strftime,TEMPLATE} where TEMPLATE is
                                a valid strftime template, e.g.
                                {today.strftime,%Y-%U} would result in year-
                                week number of year: '2020-23'. If used with
                                no template will return null value. See
                                https://strftime.org/ for help on strftime
                                templates.
{place.name}                    Place name from the photo's reverse
                                geolocation data, as displayed in Photos
{place.country_code}            The ISO country code from the photo's
                                reverse geolocation data
{place.name.country}            Country name from the photo's reverse
                                geolocation data
{place.name.state_province}     State or province name from the photo's
                                reverse geolocation data
{place.name.city}               City or locality name from the photo's
                                reverse geolocation data
{place.name.area_of_interest}   Area of interest name (e.g. landmark or
                                public place) from the photo's reverse
                                geolocation data
{place.address}                 Postal address from the photo's reverse
                                geolocation data, e.g. '2007 18th St NW,
                                Washington, DC 20009, United States'
{place.address.street}          Street part of the postal address, e.g.
                                '2007 18th St NW'
{place.address.city}            City part of the postal address, e.g.
                                'Washington'
{place.address.state_province}  State/province part of the postal address,
                                e.g. 'DC'
{place.address.postal_code}     Postal code part of the postal address, e.g.
                                '20009'
{place.address.country}         Country name of the postal address, e.g.
                                'United States'
{place.address.country_code}    ISO country code of the postal address, e.g.
                                'US'

The following substitutions may result in multiple values. Thus if specified
for --directory these could result in multiple copies of a photo being being
exported, one to each directory.  For example: --directory
'{created.year}/{album}' could result in the same photo being exported to each
of the following directories if the photos were created in 2019 and were in
albums 'Vacation' and 'Family': 2019/Vacation, 2019/Family

Substitution        Description
{album}             Album(s) photo is contained in
{folder_album}      Folder path + album photo is contained in. e.g.
                    'Folder/Subfolder/Album' or just 'Album' if no enclosing
                    folder
{keyword}           Keyword(s) assigned to photo
{person}            Person(s) / face(s) in a photo
{label}             Image categorization label associated with a photo
                    (Photos 5 only)
{label_normalized}  All lower case version of 'label' (Photos 5 only)
```

Example: export all photos to ~/Desktop/export group in folders by date created

`osxphotos export --export-by-date ~/Pictures/Photos\ Library.photoslibrary ~/Desktop/export`

**Note**: Photos library/database path can also be specified using --db option:

`osxphotos export --export-by-date --db ~/Pictures/Photos\ Library.photoslibrary ~/Desktop/export`

Example: find all photos with keyword "Kids" and output results to json file named results.json:

`osxphotos query --keyword Kids --json ~/Pictures/Photos\ Library.photoslibrary >results.json`

Example: export photos to file structure based on 4-digit year and full name of month of photo's creation date:

`osxphotos export ~/Desktop/export --directory "{created.year}/{created.month}"`

Example: export default library using 'country name/year' as output directory (but use "NoCountry/year" if country not specified), add persons, album names, and year as keywords, write exif metadata to files when exporting, update only changed files, print verbose ouput

`osxphotos export ~/Desktop/export --directory "{place.name.country,NoCountry}/{created.year}"  --person-keyword --album-keyword --keyword-template "{created.year}" --exiftool --update --verbose`


## Example uses of the package 

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

Pass the path to a Photos library or to a specific database file (e.g. "/Users/smith/Pictures/Photos Library.photoslibrary" or "/Users/smith/Pictures/Photos Library.photoslibrary/database/photos.db").  Normally, it's recommended you pass the path the .photoslibrary folder, not the actual database path.  The latter option is provided for debugging -- e.g. for reading a database file if you don't have the entire library. Path to photos library may be passed **either** as first argument **or** as named argument `dbfile`. **Note**: In Photos, users may specify a different library to open by holding down the *option* key while opening Photos.app. See also [get_last_library_path](#get_last_library_path) and [get_system_library_path](#get_system_library_path)

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

#### `album_info`
```python
# assumes photosdb is a PhotosDB object (see above)
albums = photosdb.album_info
```

Returns a list of [AlbumInfo](#AlbumInfo) objects representing albums in the database or empty list if there are no albums.  See also [albums](#albums).

#### `albums`
```python
# assumes photosdb is a PhotosDB object (see above)
album_names = photosdb.albums
```

Returns a list of the album names found in the Photos library.  

**Note**: In Photos 5.0 (MacOS 10.15/Catalina), It is possible to have more than one album with the same name in Photos.  Albums with duplicate names are treated as a single album and the photos in each are combined.  For example, if you have two albums named "Wedding" and each has 2 photos, osxphotos will treat this as a single album named "Wedding" with 4 photos in it.

See also [album_info](#album_info.)

#### `albums_shared`

Returns list of shared album names found in photos database (e.g. albums shared via iCloud photo sharing)

**Note**: *Only valid for Photos 5 / MacOS 10.15*; on Photos <= 4, prints warning and returns empty list.

#### `import_info`

Returns a list of [ImportInfo](#importinfo) objects representing the import sessions for the database.

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

- ```keywords```: list of one or more keywords.  Returns only photos containing the keyword(s).  If more than one keyword is provided finds photos matching any of the keywords (e.g. treated as "or")
- ```uuid```: list of one or more uuids.  Returns only photos whos UUID matches.  **Note**: The UUID is the universally unique identifier that the Photos database uses to identify each photo.  You shouldn't normally need to use this but it is a way to access a specific photo if you know the UUID.  If more than more uuid is provided, returns photos that match any of the uuids (e.g. treated as "or")
- ```persons```: list of one or more persons. Returns only photos containing the person(s).  If more than one person provided, returns photos that match any of the persons (e.g. treated as "or")
- ```albums```: list of one or more album names.  Returns only photos contained in the album(s). If more than one album name is provided, returns photos contained in any of the albums (.e.g. treated as "or")
- ```images```: bool; if True, returns photos/images; default is True
- ```movies```: bool; if True, returns movies/videos; default is True 
- ```from_date```: datetime.datetime; if provided, finds photos where creation date >= from_date; default is None
- ```to_date```: datetime.datetime; if provided, finds photos where creation date <= to_date; default is None
- ```intrash```: if True, finds only photos in the "Recently Deleted" or trash folder, if False does not find any photos in the trash; default is False

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

```python
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
Returns a list of [AlbumInfo](#AlbumInfo) objects representing the albums the photo is contained in.  See also [albums](#albums).

#### `import_info`
Returns an [ImportInfo](#importinfo) object representing the import session associated with the photo or `None` if there is no associated import session.

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

#### `height`
Returns height of the photo in pixels.  If image has been edited, returns height of the edited image, otherwise returns height of the original image.  See also [original_height](#original_height).

#### `width`
Returns width of the photo in pixels.  If image has been edited, returns width of the edited image, otherwise returns width of the original image.  See also [original_width](#original_width).

#### `orientation`
Returns EXIF orientation value of the photo as integer.  If image has been edited, returns orientation of the edited image, otherwise returns orientation of the original image. See also [original_orientation](#original_orientation).

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

#### `external_edit`
Returns `True` if the picture was edited in an external editor (outside Photos.app), otherwise `False`

#### `favorite`
Returns `True` if the picture has been marked as a favorite, otherwise `False`

#### `hidden`
Returns `True` if the picture has been marked as hidden, otherwise `False`

#### `intrash`
Returns `True` if the picture is in the trash ('Recently Deleted' folder), otherwise `False`

#### `location`
Returns latitude and longitude as a tuple of floats (latitude, longitude).  If location is not set, latitude and longitude are returned as `None`

#### `place`
Returns a [PlaceInfo](#PlaceInfo) object with reverse geolocation data or None if there is the photo has no reverse geolocation information.

#### `shared`
Returns True if photo is in a shared album, otherwise False.

**Note**: *Only valid on Photos 5 / MacOS 10.15*; on Photos <= 4, returns None instead of True/False. 

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
Returns Uniform Type Identifier (UTI) for the image, for example: 'public.jpeg' or 'com.apple.quicktime-movie'

#### `burst`
Returns True if photos is a burst image (e.g. part of a set of burst images), otherwise False.
See [burst_photos](#burst_photos)

#### `burst_photos`
If photo is a burst image (see [burst](#burst)), returns a list of PhotoInfo objects for all other photos in the same burst set. If not a burst image, returns empty list.

Example below gets list of all photos that are bursts, selects one of of them and prints out the names of the other images in the burst set.  PhotosDB.photos() will only return the photos in the burst set that the user [selected](https://support.apple.com/guide/photos/view-photo-bursts-phtde06a275d/mac) using "Make a Selection..." in Photos or the key image Photos selected if the user has not yet made a selection.  This is similar to how Photos displays and counts burst photos.  Using `burst_photos` you can access the other images in the burst set to export them, etc. 

```python
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

#### `live_photo`
Returns True if photo is an Apple live photo (ie. it has an associated "live" video component), otherwise returns False.  See [path_live_photo](#path_live_photo).

#### `path_live_photo`
Returns the path to the live video component of a [live photo](#live_photo). If photo is not a live photo, returns None.

**Note**: will also return None if the live video component is missing on disk. It's possible that the original photo may be on disk ([ismissing](#ismissing)==False) but the video component is missing, likely because it has not been downloaded from iCloud.

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

**Note**: Only valid on Photos 5; on earlier versions, returns empty list. In Photos 5, Photos runs machine learning image categorization against photos in the library and automatically assigns labels to photos such as "People", "Dog", "Water", etc.  A photo may have zero or more labels associated with it.  See also [labels](#labels).  

#### `exif_info`
Returns an [ExifInfo](#exifinfo) object with EXIF details from the Photos database.  See [ExifInfo](#exifinfo) for additional details.

**Note**: Only valid on Photos 5; on earlier versions, returns `None`.  The EXIF details returned are a subset of the actual EXIF data in a typical image.  At import Photos stores this subset in the database and it's this stored data that `exif_info` returns.

See also `exiftool`.

#### `exiftool`
Returns an ExifTool object for the photo which provides an interface to [exiftool](https://exiftool.org/) allowing you to read or write the actual EXIF data in the image file inside the Photos library.  If [exif_info](#exif-info) doesn't give you all the data you need, you can use `exiftool` to read the entire EXIF contents of the image.

If the file is missing from the library (e.g. not downloaded from iCloud), returns None. 

exiftool must be installed in the path for this to work.  If exiftool cannot be found in the path, calling `exiftool` will log a warning and return `None`.  You can check the exiftool path using `osxphotos.exiftool.get_exiftool_path` which will raise FileNotFoundError if exiftool cannot be found.

```python
>>> import osxphotos
>>> osxphotos.exiftool.get_exiftool_path()
'/usr/local/bin/exiftool'
>>>
```

`ExifTool` provides the following methods:

- `as_dict()`: returns all EXIF metadata found in the file as a dictionary in following form (Note: this shows just a subset of available metadata).  See [exiftool](https://exiftool.org/) documentation to understand which metadata keys are available.
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

- `json()`: returns same information as `as_dict()` but as a serialized JSON string.

- `setvalue(tag, value)`: write to the EXIF data in the photo file. To delete a tag, use setvalue with value = `None`. For example:
```python
photo.exiftool.setvalue("XMP:Title", "Title of photo")
```
- `addvalues(tag, *values)`: Add one or more value(s) to tag.  For a tag that accepts multiple values, like "IPTC:Keywords", this will add the values as additional list values.  However, for tags which are not usually lists, such as "EXIF:ISO" this will literally add the new value to the old value which is probably not the desired effect.  Be sure you understand the behavior of the individual tag before using this. For example:
```python
photo.exiftool.addvalues("IPTC:Keywords", "vacation", "beach")
```

**Caution**: I caution against writing new EXIF data to photos in the Photos library because this will overwrite the original copy of the photo and could adversely affect how Photos behaves.  `exiftool.as_dict()` is useful for getting access to all the photos information but if you want to write new EXIF data, I recommend you export the photo first then write the data.  [PhotoInfo.export()](#export) does this if called with `exiftool=True`.

#### `score`
Returns a [ScoreInfo](#scoreinfo) data class object which provides access to the computed aesthetic scores for each photo.

**Note**: Valid only for Photos 5; returns None for earlier Photos versions.

#### `json()`
Returns a JSON representation of all photo info 

#### `export()`
`export(dest, *filename, edited=False, live_photo=False, export_as_hardlink=False, overwrite=False, increment=True, sidecar_json=False, sidecar_xmp=False, use_photos_export=False, timeout=120, exiftool=False, no_xattr=False, use_albums_as_keywords=False, use_persons_as_keywords=False)`

Export photo from the Photos library to another destination on disk.  
- dest: must be valid destination path as str (or exception raised).
- *filename (optional): name of picture as str; if not provided, will use current filename.  **NOTE**: if provided, user must ensure file extension (suffix) is correct. For example, if photo is .CR2 file, edited image may be .jpeg.  If you provide an extension different than what the actual file is, export will print a warning but will happily export the photo using the incorrect file extension.  e.g. to get the extension of the edited photo, look at [PhotoInfo.path_edited](#path_edited).
- edited: boolean; if True (default=False), will export the edited version of the photo (or raise exception if no edited version)
- export_as_hardlink: boolean; if True (default=False), will hardlink files instead of copying them
- overwrite: boolean; if True (default=False), will overwrite files if they alreay exist
- live_photo: boolean; if True (default=False), will also export the associted .mov for live photos; exported live photo will be named filename.mov
- increment: boolean; if True (default=True), will increment file name until a non-existent name is found
- sidecar_json: (boolean, default = False); if True will also write a json sidecar with metadata in format readable by exiftool; sidecar filename will be dest/filename.json where filename is the stem of the photo name
- sidecar_xmp: (boolean, default = False); if True will also write a XMP sidecar with metadata; sidecar filename will be dest/filename.xmp where filename is the stem of the photo name
- use_photos_export: boolean; (default=False), if True will attempt to export photo via applescript interaction with Photos; useful for forcing download of missing photos.  This only works if the Photos library being used is the default library (last opened by Photos) as applescript will directly interact with whichever library Photos is currently using.
- timeout: (int, default=120) timeout in seconds used with use_photos_export
- exiftool: (boolean, default = False) if True, will use [exiftool](https://exiftool.org/) to write metadata directly to the exported photo; exiftool must be installed and in the system path
- no_xattr: (boolean, default = False); if True, exports file without preserving extended attributes
- use_albums_as_keywords: (boolean, default = False); if True, will use album names as keywords when exporting metadata with exiftool or sidecar
- use_persons_as_keywords: (boolean, default = False); if True, will use person names as keywords when exporting metadata with exiftool or sidecar

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

**Implementation Note**: Because the usual python file copy methods don't preserve all the metadata available on MacOS, export uses `/usr/bin/ditto` to do the copy for export. ditto preserves most metadata such as extended attributes, permissions, ACLs, etc.

#### <a name="rendertemplate">`render_template()`</a>

`render_template(template_str, none_str = "_", path_sep = None, expand_inplace = False, inplace_sep = None)`
Render template string for photo.  none_str is used if template substitution results in None value and no default specified. 
- `template_str`: str in form "{name,DEFAULT}" where name is one of the values in table below. The "," and default value that follows are optional. If specified, "DEFAULT" will be used if "name" is None.  This is useful for values which are not always present, for example reverse geolocation data.
- `none_str`: optional str to use as substitution when template value is None and no default specified in the template string.  default is "_".
- `path_sep`: optional character to use as path separator, default is os.path.sep
- `expand_inplace`: expand multi-valued substitutions in-place as a single string instead of returning individual strings
- `inplace_sep`: optional string to use as separator between multi-valued keywords with expand_inplace; default is ','

Returns a tuple of (rendered, unmatched) where rendered is a list of rendered strings with all substitutions made and unmatched is a list of any strings that resembled a template substitution but did not match a known substitution. E.g. if template contained "{foo}", unmatched would be ["foo"].

e.g. `render_filepath_template("{created.year}/{foo}", photo)` would return `(["2020/{foo}"],["foo"])`

If you want to include "{" or "}" in the output, use "{{" or "}}"

e.g. `render_filepath_template("{created.year}/{{foo}}", photo)` would return `(["2020/{foo}"],[])`

Some substitutions, notably `album`, `keyword`, and `person` could return multiple values, hence a new string will be return for each possible substitution (hence why a list of rendered strings is returned).  For example, a photo in 2 albums: 'Vacation' and 'Family' would result in the following rendered values if template was "{created.year}/{album}" and created.year == 2020: `["2020/Vacation","2020/Family"]` 

See [Template Substitutions](#template-substitutions) for additional details.

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

### FolderInfo 
PhotosDB.folder_info returns a list of FolderInfo objects representing the top level folders in the library.  Each FolderInfo object represents a single folder in the Photos library.

#### `uuid`
Returns the universally unique identifier (uuid) of the folder.  This is how Photos keeps track of individual objects within the database.

#### `title`
Returns the title or name of the folder.

#### `album_info`
Returns a list of [AlbumInfo](#AlbumInfo) objects representing each album contained in the folder.

#### `subfolders`
Returns a list of [FolderInfo](#FolderInfo) objects representing the sub-folders of the folder.  

#### `parent`
Returns a [FolderInfo](#FolderInfo) object representing the folder's parent folder or `None` if album is not a in a folder.

**Note**: FolderInfo and AlbumInfo objects effectively work as a linked list.  The children of a folder are contained in `subfolders` and `album_info` and the parent object of both `AlbumInfo` and `FolderInfo` is represented by `parent`.  For example:

```python
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

- `country`; the name of the country associated with the placemark.
- `state_province`; administrativeArea, The state or province associated with the placemark.
- `sub_administrative_area`; additional administrative area information for the placemark.
- `city`; locality; the city associated with the placemark.
- `additional_city_info`; subLocality, Additional city-level information for the placemark.
- `ocean`; the name of the ocean associated with the placemark.
- `area_of_interest`; areasOfInterest, The relevant areas of interest associated with the placemark.
- `inland_water`; the name of the inland water body associated with the placemark.
- `region`; the geographic region associated with the placemark.
- `sub_throughfare`; additional street-level information for the placemark.
- `postal_code`; the postal code associated with the placemark.
- `street_address`; throughfare, The street address associated with the placemark.
- `body_of_water`; in Photos 4, any body of water; in Photos 5 contains the union of ocean and inland_water

**Note**: In Photos <= 4.0, only the following fields are defined; all others are set to empty list:

- `country`
- `state_province`
- `sub_administrative_area`
- `city` 
- `additional_city_info`
- `area_of_interest`
- `body_of_water`

#### `country_code`
Returns the country_code of place, for example "GB".  Returns `None` if PhotoInfo contains no country code.

#### `address_str`
Returns the full postal address as a string if defined, otherwise `None`.

For example: "2038 18th St NW, Washington, DC  20009, United States"

#### `address`:
Returns a `PostalAddress` namedtuple with details of the postal address containing the following fields:
- `city`
- `country`
- `postal_code`
- `state`
- `street`
- `sub_administrative_area`
- `sub_locality`
- `iso_country_code`

For example:
```python
>>> photo.place.address
PostalAddress(street='3700 Wailea Alanui Dr', sub_locality=None, city='Kihei', sub_administrative_area='Maui', state='HI', postal_code='96753', country='United States', iso_country_code='US')
>>> photo.place.address.postal_code
'96753'
```
### ScoreInfo
[PhotoInfo.score](#score) returns a ScoreInfo object that exposes the computed aesthetic scores for each photo (**Photos 5 only**).  I have not yet reverse engineered the meaning of each score.  The `overall` score seems to the most useful and appears to be a composite of the other scores.  The following score properties are currently available:

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

#### `face_rect()`
Returns list of x, y coordinates as tuples `[(x0, y0), (x1, y1)]` representing the corners of rectangular region that contains the face.  Coordinates are in same format and [reference frame](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#coordinate-system) as used by [Pillow](https://pypi.org/project/Pillow/) imaging library.  **Note**: face_rect() and all other properties/methods that return coordinates refer to the *current version* of the image. E.g. if the image has been edited ([`PhotoInfo.hasadjustments`](#hasadjustments)), these refer to [`PhotoInfo.path_edited`](#pathedited).  If the image has no adjustments, these coordinates refer to the original photo ([`PhotoInfo.path`](#path)).

#### `center`
Coordinates as (x, y) tuple for the center of the detected face.

#### `mouth`
Coordinates as (x, y) tuple for the mouth of the detected face.

#### `left_eye`
Coordinates as (x, y) tuple for the left eye of the detected face.

#### `right_eye`
Coordinates as (x, y) tuple for the right eye of the detected face.

#### `size_pixels`
Diameter of detected face region in pixels.

#### `roll_pitch_yaw()`
Roll, pitch, and yaw of face region in radians.  Returns a tuple of (roll, pitch, yaw)

#### roll
Roll of face region in radians. 

#### pitch 
Pitch of face region in radians. 

#### yaw 
Yaw of face region in radians. 

#### `Additional properties`
The following additional properties are also available but are not yet fully documented.

- `center_x`: x coordinate of center of face in Photos' internal reference frame
- `center_y`: y coordinate of center of face in Photos' internal reference frame
- `mouth_x`: x coordinate of mouth in Photos' internal reference frame
- `mouth_y`: y coordinate of mouth in Photos' internal reference frame
- `left_eye_x`: x coordinate of left eye in Photos' internal reference frame
- `left_eye_y`: y coordinate of left eye in Photos' internal reference frame
- `right_eye_x`: x coordinate of right eye in Photos' internal reference frame
- `right_eye_y`: y coordinate of right eye in Photos' internal reference frame
- `size`: size of face region in Photos' internal reference frame
- `quality`: quality measure of detected face
- `source_width`: width in pixels of photo
- `source_height`: height in pixels of photo
- `has_smile`: 
- `left_eye_closed`: 
- `right_eye_closed`:
- `manual`: 
- `face_type`:
- `age_type`:
- `bald_type`:
- `eye_makeup_type`:
- `eye_state`:
- `facial_hair_type`:
- `gender_type`:
- `glasses_type`:
- `hair_color_type`:
- `lip_makeup_type`:
- `smile_type`:

#### `asdict()`
Returns a dictionary representation of the FaceInfo instance.

#### `json()`
Returns a JSON representation of the FaceInfo instance.

### Template Substitutions

The following substitutions are availabe for use with `PhotoInfo.render_template()` 
| Substitution | Description |
|--------------|-------------|
|{name}|Current filename of the photo|
|{original_name}|Photo's original filename when imported to Photos|
|{title}|Title of the photo|
|{descr}|Description of the photo|
|{created.date}|Photo's creation date in ISO format, e.g. '2020-03-22'|
|{created.year}|4-digit year of file creation time|
|{created.yy}|2-digit year of file creation time|
|{created.mm}|2-digit month of the file creation time (zero padded)|
|{created.month}|Month name in user's locale of the file creation time|
|{created.mon}|Month abbreviation in the user's locale of the file creation time|
|{created.dd}|2-digit day of the month (zero padded) of file creation time|
|{created.dow}|Day of week in user's locale of the file creation time|
|{created.doy}|3-digit day of year (e.g Julian day) of file creation time, starting from 1 (zero padded)|
|{created.hour}|2-digit hour of the file creation time|
|{created.min}|2-digit minute of the file creation time|
|{created.sec}|2-digit second of the file creation time|
|{created.strftime}|Apply strftime template to file creation date/time. Should be used in form {created.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {created.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. See https://strftime.org/ for help on strftime templates.|
|{modified.date}|Photo's modification date in ISO format, e.g. '2020-03-22'|
|{modified.year}|4-digit year of file modification time|
|{modified.yy}|2-digit year of file modification time|
|{modified.mm}|2-digit month of the file modification time (zero padded)|
|{modified.month}|Month name in user's locale of the file modification time|
|{modified.mon}|Month abbreviation in the user's locale of the file modification time|
|{modified.dd}|2-digit day of the month (zero padded) of the file modification time|
|{modified.doy}|3-digit day of year (e.g Julian day) of file modification time, starting from 1 (zero padded)|
|{modified.hour}|2-digit hour of the file modification time|
|{modified.min}|2-digit minute of the file modification time|
|{modified.sec}|2-digit second of the file modification time|
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
|{album}|Album(s) photo is contained in|
|{folder_album}|Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder|
|{keyword}|Keyword(s) assigned to photo|
|{person}|Person(s) / face(s) in a photo|
|{label}|Image categorization label associated with a photo (Photos 5 only)|
|{label_normalized}|All lower case version of 'label' (Photos 5 only)|

### Utility Functions

The following functions are located in osxphotos.utils

#### `get_system_library_path()`

**MacOS 10.15 Only** Returns path to System Photo Library as string.  On MacOS version < 10.15, returns None.

#### `get_last_library_path()`

Returns path to last opened Photo Library as string.  

#### `list_photo_libraries()`

Returns list of Photos libraries found on the system.  **Note**: On MacOS 10.15, this appears to list all libraries. On older systems, it may not find some libraries if they are not located in ~/Pictures.  Provided for convenience but do not rely on this to find all libraries on the system.

#### `dd_to_dms_str(lat, lon)`
Convert latitude, longitude in degrees to degrees, minutes, seconds as string.
- `lat`: latitude in degrees
- `lon`: longitude in degrees
returns: string tuple in format ("51 deg 30' 12.86\\" N", "0 deg 7' 54.50\\" W")
This is the same format used by exiftool's json format.


## Examples

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

## Related Projects

- [rhettbull/photosmeta](https://github.com/rhettbull/photosmeta): uses osxphotos and [exiftool](https://exiftool.org/) to apply metadata from Photos as exif data in the photo files.  Can also export photos while preserving metadata and also apply Photos keywords as spotlight tags to make it easier to search for photos using spotlight.  This is mostly made obsolete by osxphotos.  The one feature that photosmeta has that osxphotos does not is ability to update the metadata of the actual photo files in the Photos library without exporting them. (Use with caution!)
- [rhettbull/PhotoScript](https://github.com/RhetTbull/PhotoScript): python wrapper around Photos' applescript API allowing automation of Photos (including creation/deletion of items) from python.
- [patrikhson/photo-export](https://github.com/patrikhson/photo-export): Exports older versions of Photos databases.  Provided the inspiration for osxphotos.
- [orangeturtle739/photos-export](https://github.com/orangeturtle739/photos-export): Set of scripts to export Photos libraries.
- [ndbroadbent/icloud_photos_downloader](https://github.com/ndbroadbent/icloud_photos_downloader): Download photos from iCloud.  Currently unmaintained.
- [AaronVanGeffen/ExportPhotosLibrary](https://github.com/AaronVanGeffen/ExportPhotosLibrary): Another python script for exporting older versions of Photos libraries.
- [MossieurPropre/PhotosAlbumExporter](https://github.com/MossieurPropre/PhotosAlbumExporter): Javascript script to export photos while maintaining album structure.
- [ajslater/magritte](https://github.com/ajslater/magritte): Another python command line script for exporting photos from older versions of Photos libraries.

## Contributing

Contributing is easy!  if you find bugs or want to suggest additional features/changes, please open an [issue](https://github.com/rhettbull/osxphotos/issues/).

I'll gladly consider pull requests for bug fixes or feature implementations.  

If you have an interesting example that shows usage of this package, submit an issue or pull request and i'll include it or link to it.

Testing against "real world" Photos libraries would be especially helpful.  If you discover issues in testing against your Photos libraries, please open an issue.  I've done extensive testing against my own Photos library but that's a since data point and I'm certain there are issues lurking in various edge cases I haven't discovered yet.

### Contributors

Thank-you to the following people who have contributed to improving osxphotos!  If I've inadvertently left you off, please open an issue or send me a note.

- [britiscurious](https://github.com/britiscurious)
- [Michel Wortmann](https://github.com/mwort)
- [hshore29](https://github.com/hshore29)
- [Pablo 'merKur' Kohan](https://github.com/PabloKohan)
- [Jean-Yves Stervinou](https://github.com/jystervinou)
- [Thibault Deutsch](https://github.com/dethi)
- [grundsch](https://github.com/grundsch)
- [Ag Primatic](https://github.com/agprimatic)
- [Daniel M. Drucker](https://github.com/dmd)


## Known Bugs

My goal is make osxphotos as reliable and comprehensive as possible.  The test suite currently has over 600 tests--but there are still some [bugs](https://github.com/RhetTbull/osxphotos/issues?q=is%3Aissue+is%3Aopen+label%3Abug) or incomplete features lurking.  If you find bugs please open an [issue](https://github.com/RhetTbull/osxphotos/issues).  Notable issues include:

- Face coordinates (mouth, left eye, right eye) may not be correct for images where the head is tilted.  See [Issue #196](https://github.com/RhetTbull/osxphotos/issues/196).
- RAW images imported to Photos with an associated jpeg preview are not handled correctly by osxphotos.  osxphotos query and export will operate on the jpeg preview instead of the RAW image as will `PhotoInfo.path`.  If the user selects "Use RAW as original" in Photos, the RAW image will be exported or operated on but the jpeg will be ignored.  See [Issue #101](https://github.com/RhetTbull/osxphotos/issues/101). Note: Beta version of fix for this bug is implemented in the current version of osxphotos.
- The `--download-missing` option for `osxphotos export` does not work correctly with burst images.  It will download the primary image but not the other burst images.  See [Issue #75](https://github.com/RhetTbull/osxphotos/issues/75).

## Implementation Notes

This package works by creating a copy of the sqlite3 database that photos uses to store data about the photos library. The class PhotosDB then queries this database to extract information about the photos such as persons (faces identified in the photos), albums, keywords, etc.  If your library is large, the database can be hundreds of MB in size and the copy read then  can take many 10s of seconds to complete.  Once copied, the entire database is processed and an in-memory data structure is created meaning all subsequent accesses of the PhotosDB object occur much more quickly. 

If apple changes the database format this will likely break.

Apple does provide a framework ([PhotoKit](https://developer.apple.com/documentation/photokit?language=objc)) for querying the user's Photos library and I attempted to create the functionality in this package using this framework but unfortunately PhotoKit does not provide access to much of the needed metadata (such as Faces/Persons) and Apple's System Integrity Protection (SIP) made the interface unreliable.  If you'd like to experiment with the PhotoKit interface, here's some sample [code](https://gist.github.com/RhetTbull/41cc85e5bdeb30f761147ce32fba5c94).  While copying the sqlite file is a bit kludgy, it allows osxphotos to provide access to all available metadata.

For additional details about how osxphotos is implemented or if you would like to extend the code, see the [wiki](https://github.com/RhetTbull/osxphotos/wiki).

## Dependencies
- [PyObjC](https://pythonhosted.org/pyobjc/)
- [PyYAML](https://pypi.org/project/PyYAML/)
- [Click](https://pypi.org/project/click/)
- [Mako](https://www.makotemplates.org/)
- [bpylist2](https://pypi.org/project/bpylist2/)
- [pathvalidate](https://pypi.org/project/pathvalidate/)

## Acknowledgements
This project was originally inspired by [photo-export](https://github.com/patrikhson/photo-export) by Patrick Fältström,  Copyright (c) 2015 Patrik Fältström paf@frobbit.se

I use [py-applescript](https://github.com/rdhyee/py-applescript) by "Raymond Yee / rdhyee" to interact with Photos. Rather than import this package, I included the entire package (which is published as public domain code) in a private package to prevent ambiguity with other applescript packages on PyPi. py-applescript uses a native bridge via PyObjC and is very fast compared to the other osascript based packages.

