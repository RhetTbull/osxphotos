""" Classes to load/save config settings for osxphotos CLI """
import toml


class InvalidOptions(Exception):
    """ Invalid combination of options. """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class OSXPhotosOptions:
    """ data class to store and load options for osxphotos commands """

    def __init__(self, **kwargs):
        args = locals()

        self._attrs = {}
        self._exclusive = []

        self.set_attributes(args)

    def set_attributes(self, args):
        for attr in self._attrs:
            try:
                arg = args[attr]
                # don't test 'not arg'; need to handle empty strings as valid values
                if arg is None or arg == False:
                    if self._attrs[attr] == ():
                        setattr(self, attr, ())
                    else:
                        setattr(self, attr, self._attrs[attr])
                else:
                    setattr(self, attr, arg)
            except KeyError:
                raise KeyError(f"Missing argument: {attr}")

    def validate(self, cli=False):
        """ validate combinations of otions
        
        Args:
            cli: bool, set to True if called to validate CLI options; will prepend '--' to option names in InvalidOptions.message
        
        Returns:
            True if all options valid
            
        Raises:
            InvalidOption if any combination of options is invalid
            InvalidOption.message will be descriptive message of invalid options
        """
        prefix = "--" if cli else ""
        for opt_pair in self._exclusive:
            val0 = getattr(self, opt_pair[0])
            val1 = getattr(self, opt_pair[1])
            val0 = any(val0) if self._attrs[opt_pair[0]] == () else val0
            val1 = any(val1) if self._attrs[opt_pair[1]] == () else val1
            if val0 and val1:
                raise InvalidOptions(
                    f"{prefix}{opt_pair[0]} and {prefix}{opt_pair[1]} options cannot be used together"
                )
        return True

    def write_to_file(self, filename):
        """ Write self to TOML file

        Args:
            filename: full path to TOML file to write; filename will be overwritten if it exists
        """
        data = {}
        for attr in sorted(self._attrs.keys()):
            val = getattr(self, attr)
            if val in [False, ()]:
                val = None
            else:
                val = list(val) if type(val) == tuple else val

            data[attr] = val

        with open(filename, "w") as fd:
            toml.dump({"export": data}, fd)

    def load_from_file(self, filename, override=None):
        """ Load options from a TOML file.

        Args:
            filename: full path to TOML file
            override: optional ExportOptions object; 
                      if provided, any value that's set in override will be used 
                      to override what's in the TOML file
        
        Returns:
            (ExportOptions, error): tuple of ExportOption object and error string; 
            if there are any errors during the parsing of the TOML file, error will be set
            to a descriptive error message otherwise it will be None
        """
        override = override or ExportOptions()
        loaded = toml.load(filename)
        options = ExportOptions()
        if "export" not in loaded:
            return options, f"[export] section missing from {filename}"

        for attr in loaded["export"]:
            if attr not in self._attrs:
                return options, f"Unknown option: {attr}: {loaded['export'][attr]}"
            val = loaded["export"][attr]
            val = getattr(override, attr) or val
            if self._attrs[attr] == ():
                val = tuple(val)
            setattr(options, attr, val)
        return options, None

    def asdict(self):
        return {attr: getattr(self, attr) for attr in sorted(self._attrs.keys())}


class ExportOptions(OSXPhotosOptions):
    """ data class to store and load options for export command """

    def __init__(
        self,
        db=None,
        photos_library=None,
        keyword=None,
        person=None,
        album=None,
        folder=None,
        uuid=None,
        uuid_from_file=None,
        title=None,
        no_title=False,
        description=None,
        no_description=False,
        uti=None,
        ignore_case=False,
        edited=False,
        external_edit=False,
        favorite=False,
        not_favorite=False,
        hidden=False,
        not_hidden=False,
        shared=False,
        not_shared=False,
        from_date=None,
        to_date=None,
        verbose=False,
        missing=False,
        update=True,
        dry_run=False,
        export_as_hardlink=False,
        touch_file=False,
        overwrite=False,
        export_by_date=False,
        skip_edited=False,
        skip_original_if_edited=False,
        skip_bursts=False,
        skip_live=False,
        skip_raw=False,
        person_keyword=False,
        album_keyword=False,
        keyword_template=None,
        description_template=None,
        current_name=False,
        convert_to_jpeg=False,
        jpeg_quality=None,
        sidecar=None,
        only_photos=False,
        only_movies=False,
        burst=False,
        not_burst=False,
        live=False,
        not_live=False,
        download_missing=False,
        exiftool=False,
        ignore_date_modified=False,
        portrait=False,
        not_portrait=False,
        screenshot=False,
        not_screenshot=False,
        slow_mo=False,
        not_slow_mo=False,
        time_lapse=False,
        not_time_lapse=False,
        hdr=False,
        not_hdr=False,
        selfie=False,
        not_selfie=False,
        panorama=False,
        not_panorama=False,
        has_raw=False,
        directory=None,
        filename_template=None,
        edited_suffix=None,
        original_suffix=None,
        place=None,
        no_place=False,
        has_comment=False,
        no_comment=False,
        has_likes=False,
        no_likes=False,
        no_extended_attributes=False,
        label=None,
        deleted=False,
        deleted_only=False,
        use_photos_export=False,
        use_photokit=False,
        report=None,
        cleanup=False,
        **kwargs,
    ):
        args = locals()

        # valid attributes and default values
        self._attrs = {
            "db": None,
            "photos_library": (),
            "keyword": (),
            "person": (),
            "album": (),
            "folder": (),
            "uuid": (),
            "uuid_from_file": None,
            "title": (),
            "no_title": False,
            "description": (),
            "no_description": False,
            "uti": None,
            "ignore_case": False,
            "edited": False,
            "external_edit": False,
            "favorite": False,
            "not_favorite": False,
            "hidden": False,
            "not_hidden": False,
            "shared": False,
            "not_shared": False,
            "from_date": None,
            "to_date": None,
            "verbose": False,
            "missing": False,
            "update": False,
            "dry_run": False,
            "export_as_hardlink": False,
            "touch_file": False,
            "overwrite": False,
            "export_by_date": False,
            "skip_edited": False,
            "skip_original_if_edited": False,
            "skip_bursts": False,
            "skip_live": False,
            "skip_raw": False,
            "person_keyword": False,
            "album_keyword": False,
            "keyword_template": (),
            "description_template": None,
            "current_name": False,
            "convert_to_jpeg": False,
            "jpeg_quality": None,
            "sidecar": (),
            "only_photos": False,
            "only_movies": False,
            "burst": False,
            "not_burst": False,
            "live": False,
            "not_live": False,
            "download_missing": False,
            "exiftool": False,
            "ignore_date_modified": False,
            "portrait": False,
            "not_portrait": False,
            "screenshot": False,
            "not_screenshot": False,
            "slow_mo": False,
            "not_slow_mo": False,
            "time_lapse": False,
            "not_time_lapse": False,
            "hdr": False,
            "not_hdr": False,
            "selfie": False,
            "not_selfie": False,
            "panorama": False,
            "not_panorama": False,
            "has_raw": False,
            "directory": None,
            "filename_template": None,
            "edited_suffix": None,
            "original_suffix": None,
            "place": (),
            "no_place": False,
            "has_comment": False,
            "no_comment": False,
            "has_likes": False,
            "no_likes": False,
            "no_extended_attributes": False,
            "label": (),
            "deleted": False,
            "deleted_only": False,
            "use_photos_export": False,
            "use_photokit": False,
            "report": None,
            "cleanup": False,
        }

        self._exclusive = [
            ["favorite", "not_favorite"],
            ["hidden", "not_hidden"],
            ["title", "no_title"],
            ["description", "no_description"],
        ]

        self.set_attributes(args)
