""" PhotoInfo methods to expose computed score info from the library """

import logging
from dataclasses import dataclass

from .._constants import _PHOTOS_4_VERSION


@dataclass(frozen=True)
class ScoreInfo:
    """ Computed photo score info associated with a photo from the Photos library """

    overall: float
    curation: float
    promotion: float
    highlight_visibility: float
    behavioral: float
    failure: float
    harmonious_color: float
    immersiveness: float
    interaction: float
    interesting_subject: float
    intrusive_object_presence: float
    lively_color: float
    low_light: float
    noise: float
    pleasant_camera_tilt: float
    pleasant_composition: float
    pleasant_lighting: float
    pleasant_pattern: float
    pleasant_perspective: float
    pleasant_post_processing: float
    pleasant_reflection: float
    pleasant_symmetry: float
    sharply_focused_subject: float
    tastefully_blurred: float
    well_chosen_subject: float
    well_framed_subject: float
    well_timed_shot: float


@property
def score(self):
    """ Computed score information for a photo

    Returns:
        ScoreInfo instance
    """

    if self._db._db_version <= _PHOTOS_4_VERSION:
        logging.debug(f"score not implemented for this database version")
        return None

    try:
        return self._scoreinfo  # pylint: disable=access-member-before-definition
    except AttributeError:
        try:
            scores = self._db._db_scoreinfo_uuid[self.uuid]
            self._scoreinfo = ScoreInfo(
                overall=scores["overall_aesthetic"],
                curation=scores["curation"],
                promotion=scores["promotion"],
                highlight_visibility=scores["highlight_visibility"],
                behavioral=scores["behavioral"],
                failure=scores["failure"],
                harmonious_color=scores["harmonious_color"],
                immersiveness=scores["immersiveness"],
                interaction=scores["interaction"],
                interesting_subject=scores["interesting_subject"],
                intrusive_object_presence=scores["intrusive_object_presence"],
                lively_color=scores["lively_color"],
                low_light=scores["low_light"],
                noise=scores["noise"],
                pleasant_camera_tilt=scores["pleasant_camera_tilt"],
                pleasant_composition=scores["pleasant_composition"],
                pleasant_lighting=scores["pleasant_lighting"],
                pleasant_pattern=scores["pleasant_pattern"],
                pleasant_perspective=scores["pleasant_perspective"],
                pleasant_post_processing=scores["pleasant_post_processing"],
                pleasant_reflection=scores["pleasant_reflection"],
                pleasant_symmetry=scores["pleasant_symmetry"],
                sharply_focused_subject=scores["sharply_focused_subject"],
                tastefully_blurred=scores["tastefully_blurred"],
                well_chosen_subject=scores["well_chosen_subject"],
                well_framed_subject=scores["well_framed_subject"],
                well_timed_shot=scores["well_timed_shot"],
            )
            return self._scoreinfo
        except KeyError:
            self._scoreinfo = ScoreInfo(
                overall=0.0,
                curation=0.0,
                promotion=0.0,
                highlight_visibility=0.0,
                behavioral=0.0,
                failure=0.0,
                harmonious_color=0.0,
                immersiveness=0.0,
                interaction=0.0,
                interesting_subject=0.0,
                intrusive_object_presence=0.0,
                lively_color=0.0,
                low_light=0.0,
                noise=0.0,
                pleasant_camera_tilt=0.0,
                pleasant_composition=0.0,
                pleasant_lighting=0.0,
                pleasant_pattern=0.0,
                pleasant_perspective=0.0,
                pleasant_post_processing=0.0,
                pleasant_reflection=0.0,
                pleasant_symmetry=0.0,
                sharply_focused_subject=0.0,
                tastefully_blurred=0.0,
                well_chosen_subject=0.0,
                well_framed_subject=0.0,
                well_timed_shot=0.0,
            )
            return self._scoreinfo
