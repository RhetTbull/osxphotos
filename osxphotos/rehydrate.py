"""Rehydrate a class from a dictionary"""

from __future__ import annotations

import datetime
from typing import Any, Type


def rehydrate_class(data: dict[Any, Any], cls: Type) -> object:
    """Rehydrate a class that's been deserialized from JSON created from asdict()

    Args:
        data: dictionary of class data; datetimes should be in ISO formatted strings
        cls: class to rehydrate into

    Returns:
        Rehydrated class instance

    Note:
        This function is not a complete solution for all classes, but it's a good starting point.
        It doesn't handle all edge cases, such as classes with required arguments in __init__.
        The only special data types are datetimes, which are parsed from ISO formatted strings.
        Lists of dictionaries and nested dictionary are also supported.
    """
    if isinstance(data, list):
        # If the data is a list, create a list of rehydrated class instances
        return [rehydrate_class(item, cls) for item in data]

    instance = cls()

    for key, value in data.items():
        if isinstance(value, dict):
            # If the value is a dictionary, create a new class instance recursively
            setattr(instance, key, rehydrate_class(value, type(key, (object,), {})))
        elif isinstance(value, list):
            # If the value is a list, check if it contains dictionaries
            if all(isinstance(item, dict) for item in value):
                # If all items in the list are dictionaries, create a list of rehydrated class instances
                setattr(
                    instance,
                    key,
                    [rehydrate_class(item, type(key, (object,), {})) for item in value],
                )
            else:
                setattr(instance, key, value)
        elif "date" in key.lower() and value is not None:
            # If the key contains "date" and the value is not None, try to parse it as a datetime
            try:
                setattr(instance, key, datetime.datetime.fromisoformat(value))
            except (ValueError, TypeError):
                setattr(instance, key, value)
        else:
            setattr(instance, key, value)

    return instance
