""" Find 'bad photos' and add them to an album

This is inspired by this blog post: https://www.muchen.ca/blog/2022/cleanup-photos/

This is an osxphotos query function, that when run as follows, 
will add all photos with low quality scores to the album 'Bad Photos'

osxphotos query --query-function bad_photos.py::bad_photos --add-to-album "Bad Photos"
"""

from typing import List

from osxphotos import PhotoInfo


# Call this with: osxphotos query --query-function bad_photos.py::bad_photos --add-to-album "Bad Photos"
def bad_photos(photos: List[PhotoInfo]) -> List[PhotoInfo]:
    """your query function should take a list of PhotoInfo objects and return a list of PhotoInfo objects (or empty list)"""
    # this example finds bad photos (as measured by Photos' own scoring system)
    # don't include screenshots as Photos tends to give low scores to screenshots

    return [p for p in photos if not p.screenshot and is_bad_photo(p)]


def is_bad_photo(p: PhotoInfo) -> bool:
    """Look at photo's ScoreInfo to find photos that have low scores
    (and hence might be considered bad photos)
    """
    return any(
        [
            p.score.failure < -0.1,
            p.score.harmonious_color < -0.1,
            p.score.interesting_subject < -0.7,
            p.score.intrusive_object_presence < -0.999,
            p.score.noise < -0.75,
            p.score.pleasant_composition < -0.8,
            p.score.pleasant_lighting < -0.7,
            p.score.pleasant_perspective < -0.6,
            p.score.tastefully_blurred < -0.9,
            p.score.well_framed_subject < -0.7,
            p.score.well_timed_shot < -0.7,
        ]
    )
