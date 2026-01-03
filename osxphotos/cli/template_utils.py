"""Utilities for template field handling"""

from __future__ import annotations

from osxphotos.phototemplate import (
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
    TEMPLATE_SUBSTITUTIONS_PATHLIB,
)

# All template substitutions combined
ALL_TEMPLATE_SUBSTITUTIONS = (
    TEMPLATE_SUBSTITUTIONS
    | TEMPLATE_SUBSTITUTIONS_MULTI_VALUED
    | TEMPLATE_SUBSTITUTIONS_PATHLIB
)

# Template lookup dictionary for field suggestions
TEMPLATE_LOOKUP = {
    k.lower().replace("{", "").replace("}", ""): v.lower()
    for k, v in ALL_TEMPLATE_SUBSTITUTIONS.items()
}


def suggest_template_fields(unmatched: list[str]) -> list[str]:
    """For fields that are not matched, suggest possible fields"""
    # this is a very simple suggestion algorithm that just looks for
    # fields that start with the unmatched text or contain the unmatched text
    suggestions = []
    for un in unmatched:
        un = un.lower()
        for field, description in TEMPLATE_LOOKUP.items():
            if field.startswith(un):
                suggestions.append(field)
            elif un in field or un in description:
                suggestions.append(field)
            elif field.startswith(un[0]):
                # if first letter matches, suggest
                suggestions.append(field)
    return suggestions
