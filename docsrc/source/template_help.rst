
OSXPhotos Template System
=========================

The templating system converts one or template statements, written in osxphotos metadata templating language, to one or more rendered values using information from the photo being processed.

In its simplest form, a template statement has the form: ``"{template_field}"``\ , for example ``"{title}"`` which would resolve to the title of the photo.

Template statements may contain one or more modifiers.  The full syntax is:

``"pretext{delim+template_field:subfield|filter(path_sep)[find,replace] conditional?bool_value,default}posttext"``

Template statements are white-space sensitive meaning that white space (spaces, tabs) changes the meaning of the template statement.

``pretext`` and ``posttext`` are free form text.  For example, if a photo has title "My Photo Title" the template statement ``"The title of the photo is {title}"``\ , resolves to ``"The title of the photo is My Photo Title"``.  The ``pretext`` in this example is ``"The title if the photo is "`` and the template_field is ``{title}``.

``delim``\ : optional delimiter string to use when expanding multi-valued template values in-place

``+``\ : If present before template ``name``\ , expands the template in place.  If ``delim`` not provided, values are joined with no delimiter.

e.g. if Photo keywords are ``["foo","bar"]``\ :


* ``"{keyword}"`` renders to ``"foo", "bar"``
* ``"{,+keyword}"`` renders to: ``"foo,bar"``
* ``"{; +keyword}"`` renders to: ``"foo; bar"``
* ``"{+keyword}"`` renders to ``"foobar"``

``template_field``\ : The template field to resolve.  See `Template Substitutions <#template-substitutions>`_ for full list of template fields.

`:subfield`: Some templates have sub-fields, For example, `{exiftool:IPTC:Make}\ ``; the template_field is``\ exiftool\ ``and the sub-field is``\ IPTC:Make`.

`|filter`: You may optionally append one or more filter commands to the end of the template field using the vertical pipe ('|') symbol.  Filters may be combined, separated by '|' as in: ``{keyword|capitalize|parens}``.

Valid filters are:


* ``lower``\ : Convert value to lower case, e.g. 'Value' => 'value'.
* ``upper``\ : Convert value to upper case, e.g. 'Value' => 'VALUE'.
* ``strip``\ : Strip whitespace from beginning/end of value, e.g. ' Value ' => 'Value'.
* ``titlecase``\ : Convert value to title case, e.g. 'my value' => 'My Value'.
* ``capitalize``\ : Capitalize first word of value and convert other words to lower case, e.g. 'MY VALUE' => 'My value'.
* ``braces``\ : Enclose value in curly braces, e.g. 'value => '{value}'.
* ``parens``\ : Enclose value in parentheses, e.g. 'value' => '(value')
* ``brackets``\ : Enclose value in brackets, e.g. 'value' => '[value]'
* ``shell_quote``\ : Quotes the value for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.
* `function`: Run custom python function to filter value; use in format 'function:/path/to/file.py::function_name'. See example at https://github.com/RhetTbull/osxphotos/blob/master/examples/template_filter.py

e.g. if Photo keywords are ``["FOO","bar"]``\ :


* ``"{keyword|lower}"`` renders to ``"foo", "bar"``
* ``"{keyword|upper}"`` renders to: ``"FOO", "BAR"``
* ``"{keyword|capitalize}"`` renders to: ``"Foo", "Bar"``
* ``"{keyword|lower|parens}"`` renders to: ``"(foo)", "(bar)"``

e.g. if Photo description is "my description":


* ``"{descr|titlecase}"`` renders to: ``"My Description"``

``(path_sep)``\ : optional path separator to use when joining path-like fields, for example ``{folder_album}``.  Default is "/".

e.g. If Photo is in ``Album1`` in ``Folder1``\ :


* ``"{folder_album}"`` renders to ``["Folder1/Album1"]``
* ``"{folder_album(>)}"`` renders to ``["Folder1>Album1"]``
* ``"{folder_album()}"`` renders to ``["Folder1Album1"]``

`[find,replace]`: optional text replacement to perform on rendered template value.  For example, to replace "/" in an album name, you could use the template `"{album[/,-]}"`.  Multiple replacements can be made by appending "|" and adding another find|replace pair.  e.g. to replace both "/" and ":" in album name: ``"{album[/,-|:,-]}"``.  find/replace pairs are not limited to single characters.  The "|" character cannot be used in a find/replace pair.

`conditional`: optional conditional expression that is evaluated as boolean (True/False) for use with the `?bool_value` modifier.  Conditional expressions take the form '`not operator value`' where `not` is an optional modifier that negates the `operator`.  Note: the space before the conditional expression is required if you use a conditional expression.  Valid comparison operators are:


* ``contains``\ : template field contains value, similar to python's ``in``
* `matches`: template field contains exactly value, unlike `contains`: does not match partial matches
* ``startswith``\ : template field starts with value
* ``endswith``\ : template field ends with value
* ``<=``\ : template field is less than or equal to value
* ``>=``\ : template field is greater than or equal to value
* ``<``\ : template field is less than value
* ``>``\ : template field is greater than value
* ``==``\ : template field equals value
* ``!=``\ : template field does not equal value

The ``value`` part of the conditional expression is treated as a bare (unquoted) word/phrase.  Multiple values may be separated by '|' (the pipe symbol).  ``value`` is itself a template statement so you can use one or more template fields in ``value`` which will be resolved before the comparison occurs.

For example:


* ``{keyword matches Beach}`` resolves to True if 'Beach' is a keyword. It would not match keyword 'BeachDay'.
* ``{keyword contains Beach}`` resolves to True if any keyword contains the word 'Beach' so it would match both 'Beach' and 'BeachDay'.
* ``{photo.score.overall > 0.7}`` resolves to True if the photo's overall aesthetic score is greater than 0.7.
* ``{keyword|lower contains beach}`` uses the lower case filter to do case-insensitive matching to match any keyword that contains the word 'beach'.
* ``{keyword|lower not contains beach}`` uses the ``not`` modifier to negate the comparison so this resolves to True if there is no keyword that matches 'beach'.

Examples: to export photos that contain certain keywords with the ``osxphotos export`` command's ``--directory`` option:

``--directory "{keyword|lower matches travel|vacation?Travel-Photos,Not-Travel-Photos}"``

This exports any photo that has keywords 'travel' or 'vacation' into a directory 'Travel-Photos' and all other photos into directory 'Not-Travel-Photos'.

This can be used to rename files as well, for example:
``--filename "{favorite?Favorite-{original_name},{original_name}}"``

This renames any photo that is a favorite as 'Favorite-ImageName.jpg' (where 'ImageName.jpg' is the original name of the photo) and all other photos with the unmodified original name.

``?bool_value``\ : Template fields may be evaluated as boolean (True/False) by appending "?" after the field name (and following "(path_sep)" or "[find/replace]".  If a field is True (e.g. photo is HDR and field is ``"{hdr}"``\ ) or has any value, the value following the "?" will be used to render the template instead of the actual field value.  If the template field evaluates to False (e.g. in above example, photo is not HDR) or has no value (e.g. photo has no title and field is ``"{title}"``\ ) then the default value following a "," will be used.  

e.g. if photo is an HDR image,


* ``"{hdr?ISHDR,NOTHDR}"`` renders to ``"ISHDR"``

and if it is not an HDR image,


* ``"{hdr?ISHDR,NOTHDR}"`` renders to ``"NOTHDR"``

``,default``\ : optional default value to use if the template name has no value.  This modifier is also used for the value if False for boolean-type fields (see above) as well as to hold a sub-template for values like ``{created.strftime}``.  If no default value provided, "_" is used.

e.g., if photo has no title set,


* ``"{title}"`` renders to "_"
* ``"{title,I have no title}"`` renders to ``"I have no title"``

Template fields such as ``created.strftime`` use the default value to pass the template to use for ``strftime``.  

e.g., if photo date is 4 February 2020, 19:07:38,


* ``"{created.strftime,%Y-%m-%d-%H%M%S}"`` renders to ``"2020-02-04-190738"``

Some template fields such as ``"{media_type}"`` use the default value to allow customization of the output. For example, ``"{media_type}"`` resolves to the special media type of the photo such as ``panorama`` or ``selfie``.  You may use the default value to override these in form: ``"{media_type,video=vidéo;time_lapse=vidéo_accélérée}"``. In this example, if photo was a time_lapse photo, ``media_type`` would resolve to ``vidéo_accélérée`` instead of ``time_lapse``.

Either or both bool_value or default (False value) may be empty which would result in empty string ``""`` when rendered.

If you want to include "{" or "}" in the output, use "{openbrace}" or "{closebrace}" template substitution.

e.g. ``"{created.year}/{openbrace}{title}{closebrace}"`` would result in ``"2020/{Photo Title}"``.

Template Substitutions
----------------------

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - {name}
     - Current filename of the photo
   * - {original_name}
     - Photo's original filename when imported to Photos
   * - {title}
     - Title of the photo
   * - {descr}
     - Description of the photo
   * - {media_type}
     - Special media type resolved in this precedence: selfie, time_lapse, panorama, slow_mo, screenshot, portrait, live_photo, burst, photo, video. Defaults to 'photo' or 'video' if no special type. Customize one or more media types using format: '{media_type,video=vidéo;time_lapse=vidéo_accélérée}'
   * - {photo_or_video}
     - 'photo' or 'video' depending on what type the image is. To customize, use default value as in '{photo_or_video,photo=fotos;video=videos}'
   * - {hdr}
     - Photo is HDR?; True/False value, use in format '{hdr?VALUE_IF_TRUE,VALUE_IF_FALSE}'
   * - {edited}
     - True if photo has been edited (has adjustments), otherwise False; use in format '{edited?VALUE_IF_TRUE,VALUE_IF_FALSE}'
   * - {edited_version}
     - True if template is being rendered for the edited version of a photo, otherwise False.
   * - {favorite}
     - Photo has been marked as favorite?; True/False value, use in format '{favorite?VALUE_IF_TRUE,VALUE_IF_FALSE}'
   * - {created.date}
     - Photo's creation date in ISO format, e.g. '2020-03-22'
   * - {created.year}
     - 4-digit year of photo creation time
   * - {created.yy}
     - 2-digit year of photo creation time
   * - {created.mm}
     - 2-digit month of the photo creation time (zero padded)
   * - {created.month}
     - Month name in user's locale of the photo creation time
   * - {created.mon}
     - Month abbreviation in the user's locale of the photo creation time
   * - {created.dd}
     - 2-digit day of the month (zero padded) of photo creation time
   * - {created.dow}
     - Day of week in user's locale of the photo creation time
   * - {created.doy}
     - 3-digit day of year (e.g Julian day) of photo creation time, starting from 1 (zero padded)
   * - {created.hour}
     - 2-digit hour of the photo creation time
   * - {created.min}
     - 2-digit minute of the photo creation time
   * - {created.sec}
     - 2-digit second of the photo creation time
   * - {created.strftime}
     - Apply strftime template to file creation date/time. Should be used in form {created.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {created.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. See https://strftime.org/ for help on strftime templates.
   * - {modified.date}
     - Photo's modification date in ISO format, e.g. '2020-03-22'; uses creation date if photo is not modified
   * - {modified.year}
     - 4-digit year of photo modification time; uses creation date if photo is not modified
   * - {modified.yy}
     - 2-digit year of photo modification time; uses creation date if photo is not modified
   * - {modified.mm}
     - 2-digit month of the photo modification time (zero padded); uses creation date if photo is not modified
   * - {modified.month}
     - Month name in user's locale of the photo modification time; uses creation date if photo is not modified
   * - {modified.mon}
     - Month abbreviation in the user's locale of the photo modification time; uses creation date if photo is not modified
   * - {modified.dd}
     - 2-digit day of the month (zero padded) of the photo modification time; uses creation date if photo is not modified
   * - {modified.dow}
     - Day of week in user's locale of the photo modification time; uses creation date if photo is not modified
   * - {modified.doy}
     - 3-digit day of year (e.g Julian day) of photo modification time, starting from 1 (zero padded); uses creation date if photo is not modified
   * - {modified.hour}
     - 2-digit hour of the photo modification time; uses creation date if photo is not modified
   * - {modified.min}
     - 2-digit minute of the photo modification time; uses creation date if photo is not modified
   * - {modified.sec}
     - 2-digit second of the photo modification time; uses creation date if photo is not modified
   * - {modified.strftime}
     - Apply strftime template to file modification date/time. Should be used in form {modified.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {modified.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. Uses creation date if photo is not modified. See https://strftime.org/ for help on strftime templates.
   * - {today.date}
     - Current date in iso format, e.g. '2020-03-22'
   * - {today.year}
     - 4-digit year of current date
   * - {today.yy}
     - 2-digit year of current date
   * - {today.mm}
     - 2-digit month of the current date (zero padded)
   * - {today.month}
     - Month name in user's locale of the current date
   * - {today.mon}
     - Month abbreviation in the user's locale of the current date
   * - {today.dd}
     - 2-digit day of the month (zero padded) of current date
   * - {today.dow}
     - Day of week in user's locale of the current date
   * - {today.doy}
     - 3-digit day of year (e.g Julian day) of current date, starting from 1 (zero padded)
   * - {today.hour}
     - 2-digit hour of the current date
   * - {today.min}
     - 2-digit minute of the current date
   * - {today.sec}
     - 2-digit second of the current date
   * - {today.strftime}
     - Apply strftime template to current date/time. Should be used in form {today.strftime,TEMPLATE} where TEMPLATE is a valid strftime template, e.g. {today.strftime,%Y-%U} would result in year-week number of year: '2020-23'. If used with no template will return null value. See https://strftime.org/ for help on strftime templates.
   * - {place.name}
     - Place name from the photo's reverse geolocation data, as displayed in Photos
   * - {place.country_code}
     - The ISO country code from the photo's reverse geolocation data
   * - {place.name.country}
     - Country name from the photo's reverse geolocation data
   * - {place.name.state_province}
     - State or province name from the photo's reverse geolocation data
   * - {place.name.city}
     - City or locality name from the photo's reverse geolocation data
   * - {place.name.area_of_interest}
     - Area of interest name (e.g. landmark or public place) from the photo's reverse geolocation data
   * - {place.address}
     - Postal address from the photo's reverse geolocation data, e.g. '2007 18th St NW, Washington, DC 20009, United States'
   * - {place.address.street}
     - Street part of the postal address, e.g. '2007 18th St NW'
   * - {place.address.city}
     - City part of the postal address, e.g. 'Washington'
   * - {place.address.state_province}
     - State/province part of the postal address, e.g. 'DC'
   * - {place.address.postal_code}
     - Postal code part of the postal address, e.g. '20009'
   * - {place.address.country}
     - Country name of the postal address, e.g. 'United States'
   * - {place.address.country_code}
     - ISO country code of the postal address, e.g. 'US'
   * - {searchinfo.season}
     - Season of the year associated with a photo, e.g. 'Summer'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).
   * - {exif.camera_make}
     - Camera make from original photo's EXIF information as imported by Photos, e.g. 'Apple'
   * - {exif.camera_model}
     - Camera model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s'
   * - {exif.lens_model}
     - Lens model from original photo's EXIF information as imported by Photos, e.g. 'iPhone 6s back camera 4.15mm f/2.2'
   * - {moment}
     - The moment title of the photo
   * - {uuid}
     - Photo's internal universally unique identifier (UUID) for the photo, a 36-character string unique to the photo, e.g. '128FB4C6-0B16-4E7D-9108-FB2E90DA1546'
   * - {id}
     - A unique number for the photo based on its primary key in the Photos database. A sequential integer, e.g. 1, 2, 3...etc.  Each asset associated with a photo (e.g. an image and Live Photo preview) will share the same id. May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{id:05d}' which results in 00001, 00002, 00003...etc.
   * - {album_seq}
     - An integer, starting at 0, indicating the photo's index (sequence) in the containing album. Only valid when used in a '--filename' template and only when '{album}' or '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{album\ *seq}*\ {original_name}"'. To start counting at a value other than 0, append append a period and the starting value to the field name.  For example, to start counting at 1 instead of 0: '{album_seq.1}'. May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{album_seq:05d}' which results in 00000, 00001, 00002...etc. This may result in incorrect sequences if you have duplicate albums with the same name; see also '{folder_album_seq}'.
   * - {folder_album_seq}
     - An integer, starting at 0, indicating the photo's index (sequence) in the containing album and folder path. Only valid when used in a '--filename' template and only when '{folder_album}' is used in the '--directory' template. For example '--directory "{folder_album}" --filename "{folder_album\ *seq}*\ {original_name}"'. To start counting at a value other than 0, append append a period and the starting value to the field name.  For example, to start counting at 1 instead of 0: '{folder_album_seq.1}' May be formatted using a python string format code. For example, to format as a 5-digit integer and pad with zeros, use '{folder_album_seq:05d}' which results in 00000, 00001, 00002...etc. This may result in incorrect sequences if you have duplicate albums with the same name in the same folder; see also '{album_seq}'.
   * - {comma}
     - A comma: ','
   * - {semicolon}
     - A semicolon: ';'
   * - {questionmark}
     - A question mark: '?'
   * - {pipe}
     - A vertical pipe: '|'
   * - {openbrace}
     - An open brace: '{'
   * - {closebrace}
     - A close brace: '}'
   * - {openparens}
     - An open parentheses: '('
   * - {closeparens}
     - A close parentheses: ')'
   * - {openbracket}
     - An open bracket: '['
   * - {closebracket}
     - A close bracket: ']'
   * - {newline}
     - A newline: '\n'
   * - {lf}
     - A line feed: '\n', alias for {newline}
   * - {cr}
     - A carriage return: '\r'
   * - {crlf}
     - a carriage return + line feed: '\r\n'
   * - {osxphotos_version}
     - The osxphotos version, e.g. '0.49.4'
   * - {osxphotos_cmd_line}
     - The full command line used to run osxphotos
   * - {album}
     - Album(s) photo is contained in
   * - {folder_album}
     - Folder path + album photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder
   * - {project}
     - Project(s) photo is contained in (such as greeting cards, calendars, slideshows)
   * - {album_project}
     - Album(s) and project(s) photo is contained in; treats projects as regular albums
   * - {folder_album_project}
     - Folder path + album (includes projects as albums) photo is contained in. e.g. 'Folder/Subfolder/Album' or just 'Album' if no enclosing folder
   * - {keyword}
     - Keyword(s) assigned to photo
   * - {person}
     - Person(s) / face(s) in a photo
   * - {label}
     - Image categorization label associated with a photo (Photos 5+ only). Labels are added automatically by Photos using machine learning algorithms to categorize images. These are not the same as {keyword} which refers to the user-defined keywords/tags applied in Photos.
   * - {label_normalized}
     - All lower case version of 'label' (Photos 5+ only)
   * - {comment}
     - Comment(s) on shared Photos; format is 'Person name: comment text' (Photos 5+ only)
   * - {exiftool}
     - Format: '{exiftool:GROUP:TAGNAME}'; use exiftool (https://exiftool.org) to extract metadata, in form GROUP:TAGNAME, from image.  E.g. '{exiftool:EXIF:Make}' to get camera make, or {exiftool:IPTC:Keywords} to extract keywords. See https://exiftool.org/TagNames/ for list of valid tag names.  You must specify group (e.g. EXIF, IPTC, etc) as used in ``exiftool -G``. exiftool must be installed in the path to use this template.
   * - {searchinfo.holiday}
     - Holiday names associated with a photo, e.g. 'Christmas Day'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).
   * - {searchinfo.activity}
     - Activities associated with a photo, e.g. 'Sporting Event'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).
   * - {searchinfo.venue}
     - Venues associated with a photo, e.g. name of restaurant; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).
   * - {searchinfo.venue_type}
     - Venue types associated with a photo, e.g. 'Restaurant'; (Photos 5+ only, applied automatically by Photos' image categorization algorithms).
   * - {photo}
     - Provides direct access to the PhotoInfo object for the photo. Must be used in format '{photo.property}' where 'property' represents a PhotoInfo property. For example: '{photo.favorite}' is the same as '{favorite}' and '{photo.place.name}' is the same as '{place.name}'. '{photo}' provides access to properties that are not available as separate template fields but it assumes some knowledge of the underlying PhotoInfo class.  See https://rhettbull.github.io/osxphotos/ for additional documentation on the PhotoInfo class.
   * - {detected_text}
     - List of text strings found in the image after performing text detection. Using '{detected_text}' will cause osxphotos to perform text detection on your photos using the built-in macOS text detection algorithms which will slow down your export. The results for each photo will be cached in the export database so that future exports with '--update' do not need to reprocess each photo. You may pass a confidence threshold value between 0.0 and 1.0 after a colon as in '{detected_text:0.5}'; The default confidence threshold is 0.75. '{detected_text}' works only on macOS Catalina (10.15) or later. Note: this feature is not the same thing as Live Text in macOS Monterey, which osxphotos does not yet support.
   * - {shell_quote}
     - Use in form '{shell_quote,TEMPLATE}'; quotes the rendered TEMPLATE value(s) for safe usage in the shell, e.g. My file.jpeg => 'My file.jpeg'; only adds quotes if needed.
   * - {strip}
     - Use in form '{strip,TEMPLATE}'; strips whitespace from begining and end of rendered TEMPLATE value(s).
   * - {function}
     - Execute a python function from an external file and use return value as template substitution. Use in format: {function:file.py::function_name} where 'file.py' is the name of the python file and 'function_name' is the name of the function to call. The function will be passed the PhotoInfo object for the photo. See https://github.com/RhetTbull/osxphotos/blob/master/examples/template_function.py for an example of how to implement a template function.

