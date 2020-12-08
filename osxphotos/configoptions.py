""" ConfigOptions class to load/save config settings for osxphotos CLI """
import toml


class ConfigOptionsException(Exception):
    """ Invalid combination of options. """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ConfigOptionsInvalidError(ConfigOptionsException):
    pass


class ConfigOptionsLoadError(ConfigOptionsException):
    pass


class ConfigOptions:
    """ data class to store and load options for osxphotos commands """

    def __init__(self, name, attrs, ignore=None):
        """ init ConfigOptions class

        Args:
            name: name for these options, will be used for section heading in TOML file when saving/loading from file
            attrs: dict with name and default value for all allowed attributes
        """
        self._name = name
        self._attrs = attrs.copy()
        if ignore:
            for attrname in ignore:
                self._attrs.pop(attrname, None)

        self.set_attributes(attrs)

    def set_attributes(self, args):
        for attr in self._attrs:
            try:
                arg = args[attr]
                # don't test 'not arg'; need to handle empty strings as valid values
                if arg is None or arg == False:
                    if type(self._attrs[attr]) == tuple:
                        setattr(self, attr, ())
                    else:
                        setattr(self, attr, self._attrs[attr])
                else:
                    setattr(self, attr, arg)
            except KeyError:
                raise KeyError(f"Missing argument: {attr}")

    def validate(self, exclusive, cli=False):
        """ validate combinations of otions
        
        Args:
            cli: bool, set to True if called to validate CLI options; will prepend '--' to option names in InvalidOptions.message
        
        Returns:
            True if all options valid
            
        Raises:
            InvalidOption if any combination of options is invalid
            InvalidOption.message will be descriptive message of invalid options
        """
        if not exclusive:
            return True

        prefix = "--" if cli else ""
        for opt_pair in exclusive:
            val0 = getattr(self, opt_pair[0])
            val1 = getattr(self, opt_pair[1])
            val0 = any(val0) if self._attrs[opt_pair[0]] == () else val0
            val1 = any(val1) if self._attrs[opt_pair[1]] == () else val1
            if val0 and val1:
                raise ConfigOptionsInvalidError(
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
            toml.dump({self._name: data}, fd)

    def load_from_file(self, filename, override=False):
        """ Load options from a TOML file.

        Args:
            filename: full path to TOML file
            override: bool; if True, values in the TOML file will override values already set in the instance

        Raises:
            ConfigOptionsLoadError if there are any errors during the parsing of the TOML file
        """
        loaded = toml.load(filename)
        name = self._name
        if name not in loaded:
            raise ConfigOptionsLoadError(f"[{name}] section missing from {filename}")

        for attr in loaded[name]:
            if attr not in self._attrs:
                raise ConfigOptionsLoadError(
                    f"Unknown option: {attr} = {loaded[name][attr]}"
                )
            val = loaded[name][attr]
            if not override:
                # use value from self if set
                val = getattr(self, attr) or val
            if type(self._attrs[attr]) == tuple:
                val = tuple(val)
            setattr(self, attr, val)
        return self, None

    def asdict(self):
        return {attr: getattr(self, attr) for attr in sorted(self._attrs.keys())}
