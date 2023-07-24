<%doc>
Mako template to dump a full json representation of the photo object
Can be run from the command line with:
osxphotos export /path/to/export --sidecar-template custom_sidecar_json.mako "{filepath}.json" yes yes no
</%doc>
${photo.json(shallow=False, indent=4)}