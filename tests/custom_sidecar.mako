<%doc>
    This is an example Mako template for use with --sidecar-template
    For more information on Mako templates, see https://docs.makotemplates.org/en/latest/

    The template will be passed three variables for rendering:
    photo: a PhotoInfo object for the photo being exported
    photo_path: a pathlib.Path object for the photo file being exported
    sidecar_path: a pathlib.Path object for the sidecar file being written
</%doc>

<%def name="rating(photo)" filter="trim">\
    % if photo.favorite:
        ★★★★★
    % else:
        ★☆☆☆☆
    % endif
</%def>\

Sidecar: ${sidecar_path.name}
    Photo: ${photo_path.name}
    UUID: ${photo.uuid}
    Rating: ${rating(photo)}
