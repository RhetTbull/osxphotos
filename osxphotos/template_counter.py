""" {counter} template for Metadata Template Language """

from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

__all__ = [
    "DESCRIPTION",
    "get_counter_value",
    "reset_all_counters",
    "reset_counter",
]

# counter settings
CounterSettings = namedtuple("CounterSettings", ("start", "stop", "step"))


@dataclass
class Counter:
    settings: CounterSettings
    count: int = 0


# global variable to hold state of all counters
_counter_state: dict[str, Counter] = {}

DESCRIPTION = dedent(
    """
    A sequential counter, starting at 0, that increments each time it is evaluated.
    To start counting at a value other than 0, append append '(starting_value)' to the field name.
    For example, to start counting at 1 instead of 0: '{counter(1)}'.
    May be formatted using a python string format code.
    For example, to format as a 5-digit integer and pad with zeros, use '{counter:05d(1)}'
    which results in 00001, 00002, 00003...etc.
    You may also specify a stop value which causes the counter to reset to the starting value
    when the stop value is reached and a step size which causes the counter to increment by
    the specified value instead of 1. Use the format '{counter(start,stop,step)}' where start,
    stop, and step are integers. For example, to count from 1 to 10 by 2, use '{counter(1,11,2)}'.
    Note that the counter stops counting when the stop value is reached and does not return the
    stop value. Start, stop, and step are optional and may be omitted. For example, to count
    from 0 by 2s, use '{counter(,,2)}'.
    You may create an arbitrary number of counters by appending a unique name to the field name
    preceded by a period: '{counter.a}', '{counter.b}', etc. Each counter will have its own state
    and will start at 0 and increment by 1 unless otherwise specified.
    """
)


def get_counter_value(field: str, subfield: str | None, fieldarg: str | None) -> str:
    """Get value for {counter} template field"""

    if not field.startswith("counter"):
        raise ValueError(f"Unknown field: {field}")

    if len(field) > 7 and field[7] != ".":
        raise ValueError(f"Invalid field: {field}")

    fieldarg = fieldarg or ""
    args = fieldarg.split(",", 3)
    start, stop, step = args + [""] * (3 - len(args))
    try:
        start = int(start) if start != "" else 0
        stop = int(stop) if stop != "" else 0
        step = int(step) if step != "" else 1
    except TypeError as e:
        raise ValueError(
            f"start, stop, step must be integers: {start}, {stop}, {step}"
        ) from e

    if stop and stop < start:
        raise ValueError(f"stop must be > start: {start=}, {stop=}")

    settings = CounterSettings(start, stop, step)
    if field not in _counter_state:
        _counter_state[field] = Counter(settings=settings)
    elif _counter_state[field].settings != settings:
        raise ValueError(
            f"Counter arguments cannot be changed after initialization: {settings} != {_counter_state[field].settings}"
        )

    counter = _counter_state[field]
    value = counter.settings.start + counter.count
    counter.count += counter.settings.step
    if counter.settings.stop and value >= counter.settings.stop:
        # stop counting, reset to start
        value = counter.settings.start
        counter.count = counter.settings.step

    if format_str := subfield or "":
        value = format_str_value(value, format_str)
    return str(value)


def format_str_value(value: Any, format_str: str | None) -> str:
    """Format value based on format code in field in format id:02d"""
    if not format_str:
        return str(value)
    format_str = "{0:" + f"{format_str}" + "}"
    return format_str.format(value)


def reset_all_counters():
    """Reset all counters to 0"""
    global _counter_state
    _counter_state = {}


def reset_counter(field: str):
    """Reset counter to 0"""
    global _counter_state
    if field in _counter_state:
        _counter_state[field].count = _counter_state[field].settings.start
