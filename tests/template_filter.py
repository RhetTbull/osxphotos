""" Example of using a custom python function as an osxphotos template filter 

    Use in formath:
    "{template_field|template_filter.py::myfilter}"

    Your filter function will receive a list of strings even if the template renders to a single value.  
    You should expect a list and return a list and be able to handle multi-value templates like {keyword}
    as well as single-value templates like {original_name}
"""

from typing import List

def myfilter(values: List[str]) -> List[str]:
    """ Custom filter to append "foo-" to template value """
    values = ["foo-" + val for val in values]
    return values

