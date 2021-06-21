""" example function for osxphotos --query-function """

from typing import List

from osxphotos import PhotoInfo


# call this with --query-function:examples/query_function.py::best_selfies
def best_selfies(photos: List[PhotoInfo]) -> List[PhotoInfo]:
    """your query function should take a list of PhotoInfo objects and return a list of PhotoInfo objects (or empty list)"""
    # this example finds your best selfie for every year

    # get list of selfies sorted by date
    photos = sorted([p for p in photos if p.selfie], key=lambda p: p.date)
    if not photos:
        return []

    start_year = photos[0].date.year
    stop_year = photos[-1].date.year
    best_selfies = []
    for year in range(start_year, stop_year + 1):
        # find best selfie each year as determined by overall aesthetic score
        selfies = sorted(
            [p for p in photos if p.date.year == year],
            key=lambda p: p.score.overall,
            reverse=True,
        )
        if selfies:
            best_selfies.append(selfies[0])

    return best_selfies
