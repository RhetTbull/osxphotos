""" test ImageConverter """

import os

import pytest

skip_test = "OSXPHOTOS_TEST_CONVERT" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip if running on GitHub actions, no GPU."
)


TEST_HEIC = "tests/test-images/IMG_3092.heic"
TEST_RAW = "tests/test-images/IMG_0476_2.CR2"
TEST_JPEG = "tests/test-images/IMG_3984.jpeg"
TEST_IMAGES = [TEST_HEIC, TEST_RAW, TEST_JPEG]
TEST_NOT_AN_IMAGE = "tests/README.md"
TEST_IMAGE_DOES_NOT_EXIST = "tests/test-images/NOT-A-FILE.heic"


def test_image_converter_singleton():
    """test that ImageConverter is a singleton"""
    from osxphotos.imageconverter import ImageConverter

    convert1 = ImageConverter()
    convert2 = ImageConverter()

    assert convert1 == convert2


def test_image_converter():
    """test conversion of different image types"""
    import pathlib
    import tempfile

    from osxphotos.imageconverter import ImageConverter

    converter = ImageConverter()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with tempdir:
        for imgfile in TEST_IMAGES:
            imgfile = pathlib.Path(imgfile)
            outfile = pathlib.Path(tempdir.name) / f"{imgfile.stem}.jpeg"
            outfile2 = pathlib.Path(tempdir.name) / f"{imgfile.stem}_2.jpeg"

            # call write_jpeg with both pathlib.Path and str arguments
            assert converter.write_jpeg(imgfile, outfile)
            assert converter.write_jpeg(str(imgfile), str(outfile2))
            assert outfile.is_file()
            assert outfile2.is_file()


def test_image_converter_compression_quality():
    """test conversion of different image types with custom compression quality"""
    import pathlib
    import tempfile

    from osxphotos.imageconverter import ImageConverter

    converter = ImageConverter()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with tempdir:
        for imgfile in TEST_IMAGES:
            imgfile = pathlib.Path(imgfile)
            outfile = pathlib.Path(tempdir.name) / f"{imgfile.stem}.jpeg"

            # call write_jpeg with both pathlib.Path and str arguments
            assert converter.write_jpeg(imgfile, outfile, compression_quality=0.1)
            assert outfile.is_file()
            assert outfile.stat().st_size < 1000000


def test_image_converter_bad_compression_quality():
    """test illegal compression quality"""
    import pathlib
    import tempfile

    from osxphotos.imageconverter import ImageConverter

    converter = ImageConverter()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with tempdir:
        imgfile = pathlib.Path(TEST_HEIC)
        outfile = pathlib.Path(tempdir.name) / f"{imgfile.stem}.jpeg"
        with pytest.raises(ValueError):
            converter.write_jpeg(imgfile, outfile, compression_quality=2.0)
        with pytest.raises(ValueError):
            converter.write_jpeg(imgfile, outfile, compression_quality=-1.0)


def test_image_converter_bad_file():
    """Try to convert a file that's not an image"""
    import pathlib
    import tempfile

    from osxphotos.imageconverter import ImageConversionError, ImageConverter

    converter = ImageConverter()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with tempdir:
        imgfile = pathlib.Path(TEST_NOT_AN_IMAGE)
        outfile = pathlib.Path(tempdir.name) / f"{imgfile.stem}.jpeg"
        with pytest.raises(ImageConversionError):
            converter.write_jpeg(imgfile, outfile)


def test_image_converter_missing_file():
    """Try to convert a file that's not an image"""
    import pathlib
    import tempfile

    from osxphotos.imageconverter import ImageConverter

    converter = ImageConverter()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with tempdir:
        imgfile = pathlib.Path(TEST_IMAGE_DOES_NOT_EXIST)
        outfile = pathlib.Path(tempdir.name) / f"{imgfile.stem}.jpeg"
        with pytest.raises(FileNotFoundError):
            converter.write_jpeg(imgfile, outfile)
