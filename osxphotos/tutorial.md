<!-- OSXPHOTOS-TUTORIAL-HEADER:START -->

# OSXPhotos Tutorial

## Overview

<!-- OSXPHOTOS-TUTORIAL-HEADER:END -->

The design philosophy for osxphotos is "make the easy things easy and make the hard things possible".  To "make the hard things possible", osxphotos is very flexible and has many, many configuration options -- the `export` command for example, has over 100 command line options.  Thus, osxphotos may seem daunting at first.  The purpose of this tutorial is to explain a number of common use cases with examples and, hopefully, make osxphotos less daunting to use.  osxphotos includes several commands for retrieving information from your Photos library but the one most users are interested in is the `export` command which exports photos from the library so that's the focus of this tutorial.

## Export your photos

`osxphotos export /path/to/export`

This command exports all your photos to the `/path/to/export` directory.

**Note**: osxphotos uses the term 'photo' to refer to a generic media asset in your Photos Library.  A photo may be an image, a video file, a combination of still image and video file (e.g. an Apple "Live Photo" which is an image and an associated "live preview" video file), a JPEG image with an associated RAW image, etc.

## Export by date

While the previous command will export all your photos (and videos--see note above), it probably doesn't do exactly what you want.  In the previous example, all the photos will be exported to a single folder: `/path/to/export`.  If you have a large library with thousands of images and videos, this likely isn't very useful.  You can use the `--export-by-date` option to export photos to a folder structure organized by year, month, day, e.g. `2021/04/21`:

`osxphotos export /path/to/export --export-by-date`

With this command, a photo that was created on 31 May 2015 would be exported to: `/path/to/export/2015/05/31`

## Specify directory structure

If you prefer a different directory structure for your exported images, osxphotos provides a very flexible <!-- OSXPHOTOS-TEMPLATE-SYSTEM-LINK:START -->template system<!-- OSXPHOTOS-TEMPLATE-SYSTEM-LINK:END --> that allows you to specify the directory structure using the `--directory` option.  For example, this command exported to a directory structure that looks like: `2015/May` (4-digit year / month name):

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

## Specify exported filename

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

## Edited photos

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

## Specifying the Photos library

All the above commands operate on the default Photos library.  Most users only use a single Photos library which is also known as the System Photo Library.  It is possible to use Photos with more than one library.  For example, if you hold down the "Option" key while opening Photos, you can select an alternate Photos library.  If you don't specify which library to use, osxphotos will try find the last opened library.  Occasionally it can't determine this and in that case, it will use the System Photos Library.  If you use more than one Photos library and want to explicitly specify which library to use, you can do so with the `--db` option. (db is short for database and is so named because osxphotos operates on the database that Photos uses to manage your Photos library).

`osxphotos export /path/to/export --db ~/Pictures/MyAlternateLibrary.photoslibrary`

## Missing photos

osxphotos works by copying photos out of the Photos library folder to export them.  You may see osxphotos report that one or more photos are missing and thus could not be exported.  One possible reason for this is that you are using iCloud to synch your Photos library and Photos either hasn't yet synched the cloud library to the local Mac or you have Photos configured to "Optimize Mac Storage" in Photos Preferences. Another reason is that even if you have Photos configured to download originals to the Mac, Photos does not always download photos from shared albums or original screenshots to the Mac.  

If you encounter missing photos you can tell osxphotos to download the missing photos from iCloud using the `--download-missing` option.  `--download-missing` uses AppleScript to communicate with Photos and tell it to download the missing photos.  Photos' AppleScript interface is somewhat buggy and you may find that Photos crashes.  In this case, osxphotos will attempt to restart Photos to resume the download process.  There's also an experimental `--use-photokit` option that will communicate with Photos using a different "PhotoKit" interface.  This option must be used together with `--download-missing`:

`osxphotos export /path/to/export --download-missing`

`osxphotos export /path/to/export --download-missing --use-photokit`

## Exporting to external disks

If you are exporting to an external network attached storage (NAS) device, you may encounter errors if the network connection is unreliable.  In this case, you can use the `--retry` option so that osxphotos will automatically retry the export.  Use `--retry` with a number that specifies the number of times to retry the export:

`osxphotos export /path/to/export --retry 3`

In this example, osxphotos will attempt to export a photo up to 3 times if it encounters an error.

In addition to `--retry`, the `--exportdb` and `--ramdb` may improve performance when exporting to an external disk or a NAS. When osxphotos exports photos, it creates an export database file named `.osxphotos_export.db` in the export folder which osxphotos uses to keep track of which photos have been exported.  This allows you to restart and export and to use `--update` to update an existing export. If the connection to the export location is slow or flaky, having the export database located on the export disk may decrease performance.  In this case, you can use `--exportdb DBPATH` to instruct osxphotos to store the export database at DBPATH. If using this option, I recommend putting the export database on your Mac system disk (for example, in your home directory). If you intend to use `--update` to update the export in the future, you must remember where the export database is and use the `--exportdb` option every time you update the export.

Another alternative to using `--exportdb` is to use `--ramdb`.  This option instructs osxphotos to use a RAM database instead of a file on disk.  The RAM database is much faster than the file on disk and doesn't require osxphotos to access the network drive to query or write to the database.  When osxphotos completes the export it will write the RAM database to the export location. This can offer a significant performance boost but you will lose state information if osxphotos crashes or is interrupted during export.

## Exporting metadata with exported photos

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

## Removing a keyword during export

If some of your photos contain a keyword you do not want to be added to the exported file with `--exiftool`, you can use the template system to remove the keyword from the exported file. For example, if you want to remove the keyword "MyKeyword" from all your photos:

`osxphotos export /path/to/export --exiftool --keyword-template "{keyword|remove(MyKeyword)}" --replace-keywords`

In this example, `|remove(MyKeyword)` is a filter which removes `MyKeyword` from the keyword list of every photo being processed.  The `--replace-keywords` option instructs osxphotos to replace the keywords in the exported file with the filtered keywords from `--keyword-template`.

**Note**: When evaluating templates for `--directory` and `--filename`, osxphotos inserts the automatic default value "_" for any template field which is null (empty or blank).  This is to ensure that there's never a null directory or filename created.  For metadata templates such as `--keyword-template`, osxphotos does not provide an automatic default value thus if the template field is null, no keyword would be created.  Of course, you can provide a default value if desired and osxphotos will use this.  For example, to add "nolabel" as a keyword for any photo that doesn't have labels:

`osxphotos export /path/to/export --exiftool --keyword-template "{label,nolabel}"`

## Sidecar files

Another way to export metadata about your photos is through the use of sidecar files.  These are files that have the same name as your photo (but with a different extension) and carry the metadata.  Many digital asset management applications (for example, PhotoPrism, Lightroom, Digikam, etc.) can read or write sidecar files.  osxphotos can export metadata in exiftool compatible JSON and XMP formats using the `--sidecar` option.  For example, to output metadata to XMP sidecars:

`osxphotos export /path/to/export --sidecar XMP`

Unlike `--exiftool`, you do not need to install exiftool to use the `--sidecar` feature.  Many of the same configuration options that apply to `--exiftool` to modify metadata, for example, `--keyword-template` can also be used with `--sidecar`.  

Sidecar files are named "photoname.ext.sidecar_ext".  For example, if the photo is named `IMG_1234.JPG` and the sidecar format is XMP, the sidecar would be named `IMG_1234.JPG.XMP`.  Some applications expect the sidecar in this case to be named `IMG_1234.XMP`.  You can use the `-sidecar-drop-ext` option to force osxphotos to name the sidecar files in this manner:

`osxphotos export /path/to/export --sidecar XMP -sidecar-drop-ext`

## Updating a previous export

If you want to use osxphotos to perform periodic backups of your Photos library rather than a one-time export, use the `--update` option.  When `osxphotos export` is run, it creates a database file named `.osxphotos_export.db` in the export folder.  (**Note** Because the filename starts with a ".", you won't see it in Finder which treats "dot-files" like this as hidden.  You will see the file in the Terminal.) . If you run osxphotos with the `--update` option, it will look for this database file and, if found, use it to retrieve state information from the last time it was run to only export new or changed files.  For example:

`osxphotos export /path/to/export --update`

will read the export database located in `/path/to/export/.osxphotos_export.db` and only export photos that have been added or changed since the last time osxphotos was run.  You can run osxphotos with the `--update` option even if it's never been run before.  If the database isn't found, osxphotos will create it.  If you run `osxphotos export` without `--update` in a folder where you had previously exported photos, it will re-export all the photos.  If your intent is to keep a periodic backup of your Photos Library up to date with osxphotos, you should always use `--update`.

If your workflow involves moving files out of the export directory (for example, you move them into a digital asset management app) but you want to use the features of `--update`, you can use the `--only-new` with `--update` to force osxphotos to only export photos that are new (added to the library) since the last update.  In this case, osxphotos will ignore the previously exported files that are now missing.  Without `--only-new`, osxphotos would see that previously exported files are missing and re-export them.

`osxphotos export /path/to/export --update --only-new`

If your workflow involves editing the images you exported from Photos but you still want to maintain a backup with `--update`, you should use the `--ignore-signature` option.  `--ignore-signature` instructs osxphotos to ignore the file's signature (for example, size and date modified) when deciding which files should be updated with `--update`.  If you edit a file in the export directory and then run `--update` without `--ignore-signature`, osxphotos will see that the file is different than the one in the Photos library and re-export it.

`osxphotos export /path/to/export --update --ignore-signature`

## Dry Run

You can use the `--dry-run` option to have osxphotos "dry run" or test an export without actually exporting any files.  When combined with the `--verbose` option, which causes osxphotos to print out details of every file being exported, this can be a useful tool for testing your export options before actually running a full export.  For example, if you are learning the template system and want to verify that your `--directory` and `--filename` templates are correct, `--dry-run --verbose` will print out the name of each file being exported.

`osxphotos export /path/to/export --dry-run --verbose`

## Creating a report of all exported files

You can use the `--report` option to create a report, in comma-separated values (CSV) format that will list the details of all files that were exported, skipped, missing, etc. This file format is compatible with programs such as Microsoft Excel.  Provide the name of the report after the `--report` option:

`osxphotos export /path/to/export --report export.csv`

You can also create reports in JSON or SQLite format by changing the extension of the report filename.  For example, to create a JSON report:

`osxphotos export /path/to/export --report export.json`

And to create a SQLite report:

`osxphotos export /path/to/export --report export.sqlite`

## Exporting only certain photos

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

## Converting images to JPEG on export

Photos can store images in many different formats.  osxphotos can convert non-JPEG images (for example, RAW photos) to JPEG on export using the `--convert-to-jpeg` option.  You can specify the JPEG quality (0: worst, 1.0: best) using `--jpeg-quality`.  For example:

`osxphotos export /path/to/export --convert-to-jpeg --jpeg-quality 0.9`

## Finder attributes

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

## Saving and loading options

If you repeatedly run a complex osxphotos export command (for example, to regularly back-up your Photos library), you can save all the options to a configuration file for future use (`--save-config FILE`) and then load them (`--load-config FILE`) instead of repeating each option on the command line.

To save the configuration:

`osxphotos export /path/to/export <all your options here> --update --save-config osxphotos.toml`

Then the next to you run osxphotos, you can simply do this:

`osxphotos export /path/to/export --load-config osxphotos.toml`

The configuration file is a plain text file in [TOML](https://toml.io/en/) format so the `.toml` extension is standard but you can name the file anything you like.

## Run commands on exported photos for post-processing

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

## An example from an actual osxphotos user

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

`osxphotos export ~/Desktop/folder for exported videos/ --keyword Quik --only-movies --db /path to my.photoslibrary --touch-file --finder-tag-keywords --person-keyword --xattr-template findercomment "{title}{title?{descr?{newline},},}{descr}" --exiftool-merge-keywords --exiftool-merge-persons --exiftool --strip`

## Color Themes

Some osxphotos commands such as export use color themes to colorize the output to make it more legible. The theme may be specified with the `--theme` option. For example: `osxphotos export /path/to/export --verbose --theme dark` uses a theme suited for dark terminals. If you don't specify the color theme, osxphotos will select a default theme based on the current terminal settings. You can also specify your own default theme. See `osxphotos help theme` for more information on themes and for commands to help manage themes.  Themes are defined in `.theme` files in the `~/.osxphotos/themes` directory and use style specifications compatible with the [rich](https://rich.readthedocs.io/en/stable/style.html) library.

## Conclusion

osxphotos is very flexible.  If you merely want to backup your Photos library, then spending a few minutes to understand the `--directory` option is likely all you need and you can be up and running in minutes.  However, if you have a more complex workflow, osxphotos likely provides options to implement your workflow.  This tutorial does not attempt to cover every option offered by osxphotos but hopefully it provides a good understanding of what kinds of things are possible and where to explore if you want to learn more.
