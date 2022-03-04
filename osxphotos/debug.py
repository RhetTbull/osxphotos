"""Utilities for debugging"""

import pdb
import sys
from datetime import datetime
from typing import Dict, List

import wrapt
from rich import print

# global variable to control debug output
# set via --debug
DEBUG = False


def set_debug(debug: bool):
    """set debug flag"""
    global DEBUG
    DEBUG = debug


def is_debug():
    """return debug flag"""
    return DEBUG


def debug_watch(wrapped, instance, args, kwargs):
    """For use with wrapt.wrap_function_wrapper to watch calls to a function"""
    caller = sys._getframe().f_back.f_code.co_name
    name = wrapped.__name__
    timestamp = datetime.now().isoformat()
    print(
        f"{timestamp} {name} called from {caller} with args: {args} and kwargs: {kwargs}"
    )
    rv = wrapped(*args, **kwargs)
    print(f"{timestamp} {name} returned: {rv}")
    return rv


def debug_breakpoint(wrapped, instance, args, kwargs):
    """For use with wrapt.wrap_function_wrapper to set breakpoint on a function"""
    pdb.set_trace()
    return wrapped(*args, **kwargs)


def wrap_function(function_path, wrapper):
    """Wrap a function with wrapper function"""
    module, name = function_path.split(".", 1)
    try:
        return wrapt.wrap_function_wrapper(module, name, wrapper)
    except AttributeError as e:
        raise AttributeError(f"{module}.{name} does not exist") from e


def get_debug_args(arg_names: List, argv: List) -> Dict:
    """Get the arguments for the debug options; 
    Some of the debug options like --watch and --breakpoint need to be processed before any other packages are loaded
    so they can't be handled in the normal click argument processing, thus this function is called
    from osxphotos/cli/__init__.py
    
    Assumes multi-valued options are OK and that all options take form of --option VALUE or --option=VALUE
    """
    # argv[0] is the program name
    # argv[1] is the command
    # argv[2:] are the arguments
    args = {}
    for arg_name in arg_names:
        for idx, arg in enumerate(argv[1:]):
            if arg.startswith(f"{arg_name}="):
                arg_value = arg.split("=")[1]
                try:
                    args[arg].append(arg_value)
                except KeyError:
                    args[arg] = [arg_value]
            elif arg == arg_name:
                try:
                    args[arg].append(argv[idx + 2])
                except KeyError:
                    try:
                        args[arg] = [argv[idx + 2]]
                    except IndexError as e:
                        raise ValueError(f"Missing value for {arg}") from e
                except IndexError as e:
                    raise ValueError(f"Missing value for {arg}") from e
    return args
