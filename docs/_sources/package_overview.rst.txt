OSXPhotos Python Package Overview
=================================

Example uses of the OSXPhotos python package
--------------------------------------------

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

    """Export all photos to specified directory using album names as folders
    If file has been edited, also export the edited version,
    otherwise, export the original version
    This will result in duplicate photos if photo is in more than album

    This is not a complete export utility but is meant to show how to use the OSXPhotos API
    """

    import os.path
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
            albums = p.albums
            if not albums:
                albums = [default_album]
            for album in albums:
                click.echo(f"Exporting {p.filename} in album {album}")

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
                # export unedited version
                exported = p.export(
                    dest_dir, use_photos_export=p.ismissing or not p.path
                )
                if exported:
                    click.echo(f"Exported {p.original_filename} to {exported}")
                else:
                    click.echo(
                        f"Error exporting {p.original_filename}, no files exported"
                    )
                if p.hasadjustments:
                    # export edited version
                    exported = p.export(
                        dest_dir,
                        edited=True,
                        use_photos_export=p.ismissing or not p.path_edited,
                    )
                    if exported:
                        click.echo(
                            f"Exported edited version of {p.original_filename} to {exported}"
                        )
                    else:
                        click.echo(
                            f"Error exporting {p.original_filename}, no files exported"
                        )


    if __name__ == "__main__":
        export()


OSXPhotos REPL
--------------

The osxphotos command line interface includes a REPL (Run-Evaluate-Print Loop) for testing and development.

The REPL is started with the command: ``osxphotos repl``::

   $ osxphotos repl
   python version: 3.10.2 (main, Feb  2 2022, 07:36:01) [Clang 12.0.0 (clang-1200.0.32.29)]
   osxphotos version: 0.47.10
   Using last opened Photos library: /Users/user/Pictures/Photos Library.photoslibrary
   Loading database
   Processing database /Users/user/Pictures/Photos Library.photoslibrary/database/photos.db
   Processing database /Users/user/Pictures/Photos Library.photoslibrary/database/Photos.sqlite
   Database locked, creating temporary copy.
   Processing database.
   Database version: 6000, 5.
   Processing persons in photos.
   Processing detected faces in photos.
   Processing albums.
   Processing keywords.
   Processing photo details.
   Processing import sessions.
   Processing additional photo details.
   Processing face details.
   Processing photo labels.
   Processing EXIF details.
   Processing computed aesthetic scores.
   Processing comments and likes for shared photos.
   Processing moments.
   Done processing details from Photos library.
   Done: took 18.54 seconds
   Getting photos
   Found 31581 photos in 0.77 seconds

   The following classes have been imported from osxphotos:
   - AlbumInfo, ExifTool, PhotoInfo, PhotoExporter, ExportOptions, ExportResults, PhotosDB, PlaceInfo, QueryOptions, MomentInfo, ScoreInfo, SearchInfo

   The following variables are defined:
   - photosdb: PhotosDB() instance for '/Users/user/Pictures/Photos Library.photoslibrary'
   - photos: list of PhotoInfo objects for all photos filtered with any query options passed on command line (len=31581)
   - all_photos: list of PhotoInfo objects for all photos in photosdb, including those in the trash (len=31581)
   - selected: list of PhotoInfo objects for any photos selected in Photos (len=0)

   The following functions may be helpful:
   - get_photo(uuid): return a PhotoInfo object for photo with uuid; e.g. get_photo('B13F4485-94E0-41CD-AF71-913095D62E31')
   - get_selected(); return list of PhotoInfo objects for photos selected in Photos
   - show(photo): open a photo object in the default viewer; e.g. show(selected[0])
   - show(path): open a file at path in the default viewer; e.g. show('/path/to/photo.jpg')
   - spotlight(photo): open a photo and spotlight it in Photos
   - inspect(object): print information about an object; e.g. inspect(PhotoInfo)
   - explore(object): interactively explore an object with objexplore; e.g. explore(PhotoInfo)
   - q, quit, quit(), exit, exit(): exit this interactive shell

   >>>

Using the osxphotos CLI to run python code
------------------------------------------

The osxphotos CLI can also be used to run your own python code using the ``osxphotos run`` command.

This is useful if you have installed the CLI using ``pipx`` but want to use the osxphotos programmatic interface in your own scripts.

If you need to install any additional python packages to use in your own scripts, you can use the ``osxphotos install`` command
which installs python packages just as ``pip`` does but into the same virtual environment that osxphotos is installed in.

Likewise, you can use ``osxphotos uninstall`` to uninstall any installed python packages.

These features are also useful for developing custom functions to use with ``--query-function`` and ``--post-function``
as well as ``{function}`` templates and ``function:`` filters.
