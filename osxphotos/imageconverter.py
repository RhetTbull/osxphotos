""" ImageConverter class
    Convert an image to JPEG using CoreImage -- 
    for example, RAW to JPEG.  Only works if Mac equipped with GPU. """

# reference: https://stackoverflow.com/questions/59330149/coreimage-ciimage-write-jpg-is-shifting-colors-macos/59334308#59334308

import logging
import pathlib

import Metal
import Quartz
from Cocoa import NSURL
from Foundation import NSDictionary

# needed to capture system-level stderr
from wurlitzer import pipes


class ImageConverter:
    """ Convert images to jpeg.  This class is a singleton
        which will re-use the Core Image CIContext to avoid
        creating a new context for every conversion. """

    def __new__(cls, *args, **kwargs):
        """ create new object or return instance of already created singleton """
        if not hasattr(cls, "instance") or not cls.instance:
            cls.instance = super().__new__(cls)

        return cls.instance

    def __init__(self):
        """ return existing singleton or create a new one """

        if hasattr(self, "context"):
            return

        """ initialize CIContext """
        context_options = NSDictionary.dictionaryWithDictionary_(
            {
                "workingColorSpace": Quartz.CoreGraphics.kCGColorSpaceExtendedSRGB,
                "workingFormat": Quartz.kCIFormatRGBAh,
            }
        )
        mtldevice = Metal.MTLCreateSystemDefaultDevice()
        self.context = Quartz.CIContext.contextWithMTLDevice_options_(
            mtldevice, context_options
        )

    def write_jpeg(self, input_path, output_path, compression_quality=1.0):
        """ convert image to jpeg and write image to output_path

        Args:
            input_path: path to input image (e.g. '/path/to/import/file.CR2') as str or pathlib.Path
            output_path: path to exported jpeg (e.g. '/path/to/export/file.jpeg') as str or pathlib.Path
            compression_quality: JPEG compression quality, float in range 0.0 to 1.0; default is 1.0 (best quality)

        Return:
            True if conversion successful, else False

        Raises:
            ValueError if compression quality not in range 0.0 to 1.0
            FileNotFoundError if input_path doesn't exist
        """

        # accept input_path or output_path as pathlib.Path
        if not isinstance(input_path, str):
            input_path = str(input_path)

        if not isinstance(output_path, str):
            output_path = str(output_path)

        if not pathlib.Path(input_path).is_file():
            raise FileNotFoundError(f"could not find {input_path}")

        if not (0.0 <= compression_quality <= 1.0):
            raise ValueError(
                "illegal value for compression_quality: {compression_quality}"
            )

        input_url = NSURL.fileURLWithPath_(input_path)
        output_url = NSURL.fileURLWithPath_(output_path)

        with pipes() as (out, err):
            # capture stdout and stderr from system calls
            # otherwise, Quartz.CIImage.imageWithContentsOfURL_
            # prints to stderr something like:
            # 2020-09-20 20:55:25.538 python[73042:5650492] Creating client/daemon connection: B8FE995E-3F27-47F4-9FA8-559C615FD774
            # 2020-09-20 20:55:25.652 python[73042:5650492] Got the query meta data reply for: com.apple.MobileAsset.RawCamera.Camera, response: 0
            input_image = Quartz.CIImage.imageWithContentsOfURL_(input_url)

        if input_image is None:
            logging.debug(f"Could not create CIImage for {input_path}")
            return False

        output_colorspace = input_image.colorSpace() or Quartz.CGColorSpaceCreateWithName(
            Quartz.CoreGraphics.kCGColorSpaceSRGB
        )

        output_options = NSDictionary.dictionaryWithDictionary_(
            {"kCGImageDestinationLossyCompressionQuality": compression_quality}
        )
        _, error = self.context.writeJPEGRepresentationOfImage_toURL_colorSpace_options_error_(
            input_image, output_url, output_colorspace, output_options, None
        )
        if not error:
            return True
        else:
            logging.debug(
                "Error converting file {input_path} to jpeg at {output_path}: {error}"
            )
            return False

