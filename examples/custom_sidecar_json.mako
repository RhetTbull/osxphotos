<%doc>
    Mako template to dump a full json representation of the photo object
    Can be run from the command line with:
    osxphotos export /path/to/export --sidecar-template custom_sidecar_json.mako "{filepath}.json" yes no yes

    The template will be passed three variables for rendering:
        photo: a PhotoInfo object for the photo being exported
        photo_path: a pathlib.Path object for the photo file being exported
        sidecar_path: a pathlib.Path object for the sidecar file being written
</%doc>
${photo.json(shallow=False, indent=4)}