The templating system converts one or template statements, written in osxphotos templating language, to one or more rendered values using information from the photo being processed. 

In its simplest form, a template statement has the form: `"{template_field}"`, for example `"{title}"` which would resolve to the title of the photo.

Template statements may contain one or more modifiers.  The full syntax is:

`"pretext{delim+template_field:subfield|filter(path_sep)[find,replace]?bool_value,default}posttext"`

Template statements are white-space sensitive meaning that white space (spaces, tabs) changes the meaning of the template statement.

`pretext` and `posttext` are free form text.  For example, if a photo has title "My Photo Title". the template statement `"The title of the photo is {title}"`, resolves to `"The title of the photo is My Photo Title"`.  The `pretext` in this example is `"The title if the photo is "` and the template_field is `{title}`.  


`delim`: optional delimiter string to use when expanding multi-valued template values in-place

`+`: If present before template `name`, expands the template in place.  If `delim` not provided, values are joined with no delimiter.

e.g. if Photo keywords are `["foo","bar"]`:

- `"{keyword}"` renders to `"foo", "bar"`
- `"{,+keyword}"` renders to: `"foo,bar"`
- `"{; +keyword}"` renders to: `"foo; bar"`
- `"{+keyword}"` renders to `"foobar"`

`template_field`: The template field to resolve.  See [Template Substitutions](#template-substitutions) for full list of template fields. 

`:subfield`: Some templates have sub-fields, For example, `{exiftool:IPTC:Make}`; the template_field is `exiftool` and the sub-field is `IPTC:Make`.

`|filter`: You may optionally append one or more filter commands to the end of the template field using the vertical pipe ('|') symbol.  Valid filters are:

<!-- OSXPHOTOS-FILTER-TABLE:START - Do not remove or modify this section -->
- lower: Convert value to lower case, e.g. 'Value' => 'value'.
- upper: Convert value to upper case, e.g. 'Value' => 'VALUE'.
- strip: Strip whitespace from beginning/end of value, e.g. ' Value ' => 'Value'.
- title: Convert value to title case, e.g. 'my value' => 'My Value'.
- capitalize: Capitalize first word of value and convert other words to lower case, e.g. 'MY VALUE' => 'My value'.
- braces: Enclose value in curly braces, e.g. 'value => '{value}'.
- parens: Enclose value in parentheses, e.g. 'value' => '(value')
- brackets: Enclose value in brackets, e.g. 'value' => '[value]'
<!-- OSXPHOTOS-FILTER-TABLE:END -->

e.g. if Photo keywords are `["FOO","bar"]`:

- `"{keyword|lower}"` renders to `"foo", "bar"`
- `"{keyword|upper}"` renders to: `"FOO", "BAR"`
- `"{keyword|capitalize}"` renders to: `"Foo", "Bar"`

e.g. if Photo description is "my description":

- `"{descr|title}"` renders to: `"My Description"`

`PATH_SEP`: optional path separator to use when joining path like fields, for example `{folder_album}`.  May also be provided as `path_sep` argument in `render_template()`.  If provided both in the call to `render_template()` and in the template itself, the value in the template string takes precedence.  If not provided in either the template string or in `path_sep` argument, defaults to `os.path.sep`.

e.g. If Photo is in `Album1` in `Folder1`:

- `"{folder_album}"` renders to `["Folder1/Album1"]`
- `"{folder_album(:)}"` renders to `["Folder1:Album1"]`
- `"{folder_album()}"` renders to `["Folder1Album1"]`

`[OLD,NEW]`: optional text replacement to perform on rendered template value.  For example, to replace "/" in an album name, you could use the template `"{album[/,-]}"`.

`?TRUE_VALUE`: optional value to use if name is boolean-type field which evaluates to true.  For example `"{hdr}"` evaluates to True if photo is an high dynamic range (HDR) image and False otherwise. In these types of fields, use `?TRUE_VALUE` to provide the value if True and `,DEFAULT` to provide the value of False.  

e.g. if photo is an HDR image,

- `"{hdr?ISHDR,NOTHDR}"` renders to `["ISHDR"]`

and if it is not an HDR image,

- `"{hdr?ISHDR,NOTHDR}"` renders to `["NOTHDR"]`

Either or both `TRUE_VALUE` or `DEFAULT` (False value) may be empty which would result in empty string `[""]` when rendered.

`,DEFAULT`: optional default value to use if the template name has no value.  This modifier is also used for the value if False for boolean-type fields (see above) as well as to hold a sub-template for values like `{created.strftime}`.  If no default value provided, "_" is used. May also be provided in the `none_str` argument to `render_template()`.  If provided both in the template string and in `none_str`, the value in the template string takes precedence.

e.g., if photo has no title set,

- `"{title}"` renders to ["_"]
- `"{title,I have no title}"` renders to `["I have no title"]`

Template fields such as `created.strftime` use the DEFAULT value to pass the template to use for `strftime`.  

e.g., if photo date is 4 February 2020, 19:07:38,

- `"{created.strftime,%Y-%m-%d-%H%M%S}"` renders to `["2020-02-04-190738"]`

Some template fields such as `"{media_type}"` use the `DEFAULT` value to allow customization of the output. For example, `"{media_type}"` resolves to the special media type of the photo such as `panorama` or `selfie`.  You may use the `DEFAULT` value to override these in form: `"{media_type,video=vidéo;time_lapse=vidéo_accélérée}"`. In this example, if photo was a time_lapse photo, `media_type` would resolve to `vidéo_accélérée` instead of `time_lapse`. 

If you want to include "{" or "}" in the output, use "{openbrace}" or "{closebrace}" template substitution.

e.g. `render_template("{created.year}/{openbrace}{foo}{closebrace}", photo)` would return `(["2020/{foo}"],[])`

