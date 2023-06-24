""" Use Apple's Vision Framework via PyObjC to perform text detection on images (macOS 10.15+ only) """

import logging
import sys
from typing import List, Optional

from .platform import assert_macos, get_macos_version

assert_macos()

import objc
import Quartz
from Cocoa import NSURL
from Foundation import NSDictionary

# needed to capture system-level stderr
from wurlitzer import pipes

__all__ = ["detect_text", "make_request_handler"]

ver, major, minor = get_macos_version()
if ver == "10" and int(major) < 15:
    vision = False
else:
    import Vision

    vision = True


def detect_text(img_path: str, orientation: Optional[int] = None) -> List:
    """process image at img_path with VNRecognizeTextRequest and return list of results

    Args:
        img_path: path to the image file
        orientation: optional EXIF orientation (if known, passing orientation may improve quality of results)
    """
    if not vision:
        logging.warning("detect_text not implemented for this version of macOS")
        return []

    with objc.autorelease_pool():
        input_url = NSURL.fileURLWithPath_(img_path)

        with pipes() as (out, err):
            # capture stdout and stderr from system calls
            # otherwise, Quartz.CIImage.imageWithContentsOfURL_
            # prints to stderr something like:
            # 2020-09-20 20:55:25.538 python[73042:5650492] Creating client/daemon connection: B8FE995E-3F27-47F4-9FA8-559C615FD774
            # 2020-09-20 20:55:25.652 python[73042:5650492] Got the query meta data reply for: com.apple.MobileAsset.RawCamera.Camera, response: 0
            input_image = Quartz.CIImage.imageWithContentsOfURL_(input_url)

        vision_options = NSDictionary.dictionaryWithDictionary_({})
        if orientation is None:
            vision_handler = (
                Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
                    input_image, vision_options
                )
            )
        elif 1 <= orientation <= 8:
            vision_handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_orientation_options_(
                input_image, orientation, vision_options
            )
        else:
            raise ValueError("orientation must be between 1 and 8")
        results = []
        handler = make_request_handler(results)
        vision_request = (
            Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
        )
        error = vision_handler.performRequests_error_([vision_request], None)
        vision_request.dealloc()
        vision_handler.dealloc()

        for result in results:
            result[0] = str(result[0])

        return results


def make_request_handler(results):
    """results: list to store results"""
    if not isinstance(results, list):
        raise ValueError("results must be a list")

    def handler(request, error):
        if error:
            print(f"Error! {error}")
        else:
            observations = request.results()
            for text_observation in observations:
                recognized_text = text_observation.topCandidates_(1)[0]
                results.append([recognized_text.string(), recognized_text.confidence()])

    return handler
