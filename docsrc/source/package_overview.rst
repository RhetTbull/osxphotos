
Example uses of the OSXPhotos python package
----------------------------------

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
       export()