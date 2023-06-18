""" ScoreInfo class to expose computed score info from the library """

from dataclasses import asdict, dataclass

from ._constants import _PHOTOS_4_VERSION

__all__ = ["ScoreInfo"]


@dataclass(frozen=True)
class ScoreInfo:
    """Computed photo score info associated with a photo from the Photos library"""

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

    def asdict(self):
        """Return ScoreInfo as a dict"""
        return asdict(self)
