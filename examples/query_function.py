""" example function for osxphotos --query-function """


from typing import List

from osxphotos import PhotoInfo


# call this with --query-function:examples/query_function.py::best_selfies
def best_selfies(photos: List[PhotoInfo]) -> List[PhotoInfo]:
    """your query function should take a list of PhotoInfo objects and return a list of PhotoInfo objects (or empty list)"""
    # this example finds your best selfie for every year

    # get list of selfies sorted by date
    photos = sorted([p for p in photos if p.selfie], key=lambda p: p.date)

    start_year = photos[0].date.year
    stop_year = photos[-1].date.year
    print(start_year, stop_year)

    return photos