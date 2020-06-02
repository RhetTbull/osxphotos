""" Yet another simple exiftool wrapper 
    I rolled my own for following reasons: 
    1. I wanted something under MIT license (best alternative was licensed under GPL/BSD)
    2. I wanted singleton behavior so only a single exiftool process was ever running
    If these aren't important to you, I highly recommend you use Sven Marnach's excellent 
    pyexiftool: https://github.com/smarnach/pyexiftool which provides more functionality """

import json
import logging
import os
import subprocess
import sys
from functools import lru_cache  # pylint: disable=syntax-error

from .utils import _debug

# exiftool -stay_open commands outputs this EOF marker after command is run
EXIFTOOL_STAYOPEN_EOF = "{ready}"
EXIFTOOL_STAYOPEN_EOF_LEN = len(EXIFTOOL_STAYOPEN_EOF)


@lru_cache(maxsize=1)
def get_exiftool_path():
    """ return path of exiftool, cache result """
    result = subprocess.run(["which", "exiftool"], stdout=subprocess.PIPE)
    exiftool_path = result.stdout.decode("utf-8")
    if _debug():
        logging.debug("exiftool path = %s" % (exiftool_path))
    if exiftool_path:
        return exiftool_path.rstrip()
    else:
        raise FileNotFoundError(
            "Could not find exiftool. Please download and install from "
            "https://exiftool.org/"
        )


class _ExifToolProc:
    """ Runs exiftool in a subprocess via Popen
        Creates a singleton object """

    def __new__(cls, *args, **kwargs):
        """ create new object or return instance of already created singleton """
        if not hasattr(cls, "instance") or not cls.instance:
            cls.instance = super().__new__(cls)

        return cls.instance

    def __init__(self, exiftool=None):
        """ construct _ExifToolProc singleton object or return instance of already created object
            exiftool: optional path to exiftool binary (if not provided, will search path to find it) """

        if hasattr(self, "_process_running") and self._process_running:
            # already running
            if exiftool is not None:
                logging.warning(
                    f"exiftool subprocess already running, "
                    f"ignoring exiftool={exiftool}"
                )
            return

        self._exiftool = exiftool if exiftool else get_exiftool_path()
        self._process_running = False
        self._start_proc()

    @property
    def process(self):
        """ return the exiftool subprocess """
        if self._process_running:
            return self._process
        else:
            raise ValueError("exiftool process is not running")

    @property
    def pid(self):
        """ return process id (PID) of the exiftool process """
        return self._process.pid

    @property
    def exiftool(self):
        """ return path to exiftool process """
        return self._exiftool

    def _start_proc(self):
        """ start exiftool in batch mode """

        if self._process_running:
            logging.warning("exiftool already running: {self._process}")
            return

        # open exiftool process
        self._process = subprocess.Popen(
            [
                self._exiftool,
                "-stay_open",  # keep process open in batch mode
                "True",  # -stay_open=True, keep process open in batch mode
                "-@",  # read command-line arguments from file
                "-",  # read from stdin
                "-common_args",  # specifies args common to all commands subsequently run
                "-n",  # no print conversion (e.g. print tag values in machine readable format)
                "-G",  # print group name for each tag
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._process_running = True

    def _stop_proc(self):
        """ stop the exiftool process if it's running, otherwise, do nothing """
        if not self._process_running:
            logging.warning("exiftool process is not running")
            return

        self._process.stdin.write(b"-stay_open\n")
        self._process.stdin.write(b"False\n")
        self._process.stdin.flush()
        try:
            self._process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning(
                f"exiftool pid {self._process.pid} did not exit, killing it"
            )
            self._process.kill()
            self._process.communicate()

        del self._process
        self._process_running = False

    def __del__(self):
        self._stop_proc()


class ExifTool:
    """ Basic exiftool interface for reading and writing EXIF tags """

    def __init__(self, filepath, exiftool=None, overwrite=True):
        """ Return ExifTool object
            file: path to image file
            exiftool: path to exiftool, if not specified will look in path
            overwrite: if True, will overwrite image file without creating backup, default=False """
        self.file = filepath
        self.overwrite = overwrite
        self.data = {}
        self._exiftoolproc = _ExifToolProc(exiftool=exiftool)
        self._process = self._exiftoolproc.process
        self._read_exif()

    def setvalue(self, tag, value):
        """ Set tag to value(s) 
            if value is None, will delete tag """

        if value is None:
            value = ""
        command = [f"-{tag}={value}"]
        if self.overwrite:
            command.append("-overwrite_original")
        self.run_commands(*command)

    def addvalues(self, tag, *values):
        """ Add one or more value(s) to tag
            If more than one value is passed, each value will be added to the tag
            Notes: exiftool may add duplicate values for some tags so the caller must ensure
                   the values being added are not already in the EXIF data
                   For some tags, such as IPTC:Keywords, this will add a new value to the list of keywords, 
                   but for others, such as EXIF:ISO, this will literally add a value to the existing value.
                   It's up to the caller to know what exiftool will do for each tag
                   If setvalue called before addvalues, exiftool does not appear to add duplicates, 
                   but if addvalues called without first calling setvalue, exiftool will add duplicate values
        """
        if not values:
            raise ValueError("Must pass at least one value")

        command = []
        for value in values:
            if value is None:
                raise ValueError("Can't add None value to tag")
            command.append(f"-{tag}+={value}")

        if self.overwrite:
            command.append("-overwrite_original")

        if command:
            self.run_commands(*command)

    def run_commands(self, *commands, no_file=False):
        """ run commands in the exiftool process and return result 
            no_file: (bool) do not pass the filename to exiftool (default=False)
                     by default, all commands will be run against self.file
                     use no_file=True to run a command without passing the filename """
        if not (hasattr(self, "_process") and self._process):
            raise ValueError("exiftool process is not running")

        if not commands:
            raise TypeError("must provide one or more command to run")

        filename = os.fsencode(self.file) if not no_file else b""
        command_str = (
            b"\n".join([c.encode("utf-8") for c in commands])
            + b"\n"
            + filename
            + b"\n"
            + b"-execute\n"
        )

        if _debug():
            logging.debug(command_str)

        # send the command
        self._process.stdin.write(command_str)
        self._process.stdin.flush()

        # read the output
        output = b""
        while EXIFTOOL_STAYOPEN_EOF not in str(output):
            output += self._process.stdout.readline().strip()
        return output[:-EXIFTOOL_STAYOPEN_EOF_LEN]

    @property
    def pid(self):
        """ return process id (PID) of the exiftool process """
        return self._process.pid

    @property
    def version(self):
        """ returns exiftool version """
        ver = self.run_commands("-ver", no_file=True)
        return ver.decode("utf-8")

    def as_dict(self):
        """ return dictionary of all EXIF tags and values from exiftool 
            returns empty dict if no tags
        """
        json_str = self.run_commands("-json")
        if json_str:
            exifdict = json.loads(json_str)
            return exifdict[0]
        else:
            return dict()

    def json(self):
        """ returns JSON string containing all EXIF tags and values from exiftool """
        return self.run_commands("-json")

    def _read_exif(self):
        """ read exif data from file """
        data = self.as_dict()
        self.data = {k: v for k, v in data.items()}

    def __str__(self):
        return f"file: {self.file}\nexiftool: {self._exiftoolproc._exiftool}"
