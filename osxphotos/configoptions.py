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
            ignore: optional list of strings of keys to ignore from attrs dict
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

    def validate(self, exclusive=None, inclusive=None, dependent=None, cli=False):
        """ validate combinations of otions
        
        Args:
            exclusive: list of tuples in form [("option_1", "option_2")...] which are exclusive; 
                       ie. either option_1 can be set or option_2 but not both; 
            inclusive: list of tuples in form [("option_1", "option_2")...] which are inclusive; 
                       ie. if either option_1 or option_2 is set, the other must be set
            dependent: list of tuples in form [("option_1", ("option_2", "option_3"))...] 
                       where if option_1 is set, then at least one of the options in the second tuple must also be set
            cli: bool, set to True if called to validate CLI options; 
                       will prepend '--' to option names in InvalidOptions.message and change _ to - in option names
        
        Returns:
            True if all options valid
            
        Raises:
            InvalidOption if any combination of options is invalid
            InvalidOption.message will be descriptive message of invalid options
        """
        if not any([exclusive, inclusive, dependent]):
            return True

        prefix = "--" if cli else ""
        if exclusive:
            for a, b in exclusive:
                vala = getattr(self, a)
                valb = getattr(self, b)
                vala = any(vala) if isinstance(vala, tuple) else vala
                valb = any(valb) if isinstance(valb, tuple) else valb
                if vala and valb:
                    stra = a.replace("_", "-") if cli else a
                    strb = b.replace("_", "-") if cli else b
                    raise ConfigOptionsInvalidError(
                        f"{prefix}{stra} and {prefix}{strb} options cannot be used together."
                    )
        if inclusive:
            for a, b in inclusive:
                vala = getattr(self, a)
                valb = getattr(self, b)
                vala = any(vala) if isinstance(vala, tuple) else vala
                valb = any(valb) if isinstance(valb, tuple) else valb
                if any([vala, valb]) and not all([vala, valb]):
                    stra = a.replace("_", "-") if cli else a
                    strb = b.replace("_", "-") if cli else b
                    raise ConfigOptionsInvalidError(
                        f"{prefix}{stra} and {prefix}{strb} options must be used together."
                    )
        if dependent:
            for a, b in dependent:
                vala = getattr(self, a)
                if not isinstance(b, tuple):
                    # python unrolls the tuple if there's a single element
                    b = (b,)
                valb = [getattr(self, x) for x in b]
                valb = [any(x) if isinstance(x, tuple) else x for x in valb]
                if vala and not any(valb):
                    if cli:
                        stra = prefix + a.replace("_", "-")
                        strb = ", ".join(prefix + x.replace("_", "-") for x in b)
                    else:
                        stra = a
                        strb = ", ".join(b)
                    raise ConfigOptionsInvalidError(
                        f"{stra} must be used with at least one of: {strb}."
                    )
        return True

    def write_to_file(self, filename):
        """ Write self to TOML file

        Args:
            filename: full path to TOML file to write; filename will be overwritten if it exists
        """
        # todo: add overwrite and option to merge contents already in TOML file (under different [section] with new content)
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
        return self

    def asdict(self):
        return {attr: getattr(self, attr) for attr in sorted(self._attrs.keys())}
