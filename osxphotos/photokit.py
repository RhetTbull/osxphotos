""" Interface to Apple's PhotoKit framework for direct access to photos stored
    in the user's Photos library.  This is not by any means a complete implementation
    but does provide basic functionality for access metada about media assets and
    exporting assets from the library.

"""

# NOTES:
# - This likely leaks memory like a sieve as I need to ensure all the
#   Objective C objects are cleaned up.
# - There are several techniques used for handling PhotoKit's various
#   asynchronous calls used in this code: event loop+notification, threading
#   event, while loop. I've experimented with each to find the one that works.
#   Happy to accept PRs from someone who knows PyObjC better than me and can
#   find a cleaner way to do this!

# TODO:
# BUG: LivePhotoAsset.export always exports edited version if Live Photo has been edited, even if other version requested
# add original=False to export instead of version= (and maybe others like path())
# make burst/live methods get uuid from self instead of passing as arg

import copy
import pathlib
import threading
import time

import AVFoundation
import CoreServices
import Foundation
import objc
import Photos
import Quartz
from Foundation import NSNotificationCenter, NSObject
from PyObjCTools import AppHelper

from .fileutil import FileUtil
from .utils import _get_os_version, get_preferred_uti_extension, increment_filename

# NOTE: This requires user have granted access to the terminal (e.g. Terminal.app or iTerm)
# to access Photos.  This should happen automatically the first time it's called. I've
# not figured out how to get the call to requestAuthorization_ to actually work in the case
# where Terminal doesn't automatically ask (e.g. if you use tcctutil to reset terminal priveleges)
# In the case where permission to use Photos was removed or reset, it looks like you also need
# to remove permission to for Full Disk Access then re-run the script in order for Photos to
# re-ask for permission

### constants
# which version to export, use either PHOTOS_VERSION_X or the longer PhotoKit name
PHOTOS_VERSION_ORIGINAL = (
    PHImageRequestOptionsVersionOriginal
) = Photos.PHImageRequestOptionsVersionOriginal
PHOTOS_VERSION_UNADJUSTED = (
    PHImageRequestOptionsVersionUnadjusted
) = Photos.PHImageRequestOptionsVersionUnadjusted
PHOTOS_VERSION_CURRENT = (
    PHImageRequestOptionsVersionCurrent
) = Photos.PHImageRequestOptionsVersionCurrent

# notification that gets sent to Notification Center
PHOTOKIT_NOTIFICATION_FINISHED_REQUEST = "PyPhotoKitNotificationFinishedRequest"

# minimum amount to sleep while waiting for export
MIN_SLEEP = 0.015

### utility functions
def NSURL_to_path(url):
    """ Convert URL string as represented by NSURL to a path string """
    nsurl = Foundation.NSURL.alloc().initWithString_(
        Foundation.NSString.alloc().initWithString_(str(url))
    )
    path = nsurl.fileSystemRepresentation().decode("utf-8")
    nsurl.dealloc()
    return path


def path_to_NSURL(path):
    """ Convert path string to NSURL """
    pathstr = Foundation.NSString.alloc().initWithString_(str(path))
    url = Foundation.NSURL.fileURLWithPath_(pathstr)
    pathstr.dealloc()
    return url


def check_photokit_authorization():
    """ Check authorization to use user's Photos Library

    Returns:
       True if user has authorized access to the Photos library, otherwise False 
    """

    auth_status = Photos.PHPhotoLibrary.authorizationStatus()
    return auth_status == Photos.PHAuthorizationStatusAuthorized


def request_photokit_authorization():
    """ Request authorization to user's Photos Library

    Returns:
        authorization status

    Note: In actual practice, the terminal process running the python code
          will do the actual request.
    """

    (_, major, _) = _get_os_version()

    def handler(status):
        pass

    auth_status = 0
    if int(major) < 16:
        auth_status = Photos.PHPhotoLibrary.authorizationStatus()
        if auth_status != Photos.PHAuthorizationStatusAuthorized:
            # it seems the first try fails after Terminal prompts user for access so try again
            for _ in range(2):
                Photos.PHPhotoLibrary.requestAuthorization_(handler)
                auth_status = Photos.PHPhotoLibrary.authorizationStatus()
                if auth_status == Photos.PHAuthorizationStatusAuthorized:
                    break
    else:
        # requestAuthorization deprecated in 10.16/11.0
        # but requestAuthorizationForAccessLevel not yet implemented in pyobjc (will be in ver 7.0)
        # https://developer.apple.com/documentation/photokit/phphotolibrary/3616053-requestauthorizationforaccesslev?language=objc
        auth_status = Photos.PHPhotoLibrary.authorizationStatus()
        if auth_status != Photos.PHAuthorizationStatusAuthorized:
            # it seems the first try fails after Terminal prompts user for access so try again
            for _ in range(2):
                Photos.PHPhotoLibrary.requestAuthorization_(handler)
                auth_status = Photos.PHPhotoLibrary.authorizationStatus()
                if auth_status == Photos.PHAuthorizationStatusAuthorized:
                    break

    return auth_status


### exceptions
class PhotoKitError(Exception):
    """Base class for exceptions in this module. """

    pass


class PhotoKitFetchFailed(PhotoKitError):
    """Exception raised for errors in the input. """

    pass


class PhotoKitAuthError(PhotoKitError):
    """Exception raised if unable to authorize use of PhotoKit. """

    pass


class PhotoKitExportError(PhotoKitError):
    """Exception raised if unable to export asset. """

    pass


class PhotoKitMediaTypeError(PhotoKitError):
    """ Exception raised if an unknown mediaType() is encountered """

    pass


### helper classes
class ImageData:
    """ Simple class to hold the data passed to the handler for 
        requestImageDataAndOrientationForAsset_options_resultHandler_ 
    """

    def __init__(
        self, metadata=None, uti=None, image_data=None, info=None, orientation=None
    ):
        self.metadata = metadata
        self.uti = uti
        self.image_data = image_data
        self.info = info
        self.orientation = orientation


class AVAssetData:
    """ Simple class to hold the data passed to the handler for 
    """

    def __init__(self):
        self.asset = None
        self.export_session = None
        self.info = None
        self.audiomix = None


class PHAssetResourceData:
    """ Simple class to hold data from 
    requestDataForAssetResource:options:dataReceivedHandler:completionHandler:
    """

    def __init__(self):
        self.data = b""


# class LivePhotoData:
#     """ Simple class to hold the data passed to the handler for
#         requestLivePhotoForAsset:targetSize:contentMode:options:resultHandler:
#     """

#     def __init__(self):
#         self.live_photo = None
#         self.info = None


class PhotoKitNotificationDelegate(NSObject):
    """ Handles notifications from NotificationCenter;
        used with asynchronous PhotoKit requests to stop event loop when complete
    """

    def liveNotification_(self, note):
        if note.name() == PHOTOKIT_NOTIFICATION_FINISHED_REQUEST:
            AppHelper.stopEventLoop()

    def __del__(self):
        pass
        # super(NSObject, self).dealloc()


### main class implementation
class PhotoAsset:
    """ PhotoKit PHAsset representation """

    def __init__(self, manager, phasset):
        """ Return a PhotoAsset object
        
        Args:
            manager = ImageManager object
            phasset: a PHAsset object
            uuid: UUID of the asset
        """
        self._manager = manager
        self._phasset = phasset

    @property
    def phasset(self):
        """ Return PHAsset instance """
        return self._phasset

    @property
    def uuid(self):
        """ Return local identifier (UUID) of PHAsset """
        return self._phasset.localIdentifier()

    @property
    def isphoto(self):
        """ Return True if asset is photo (image), otherwise False """
        return self.media_type == Photos.PHAssetMediaTypeImage

    @property
    def ismovie(self):
        """ Return True if asset is movie (video), otherwise False """
        return self.media_type == Photos.PHAssetMediaTypeVideo

    @property
    def isaudio(self):
        """ Return True if asset is audio, otherwise False """
        return self.media_type == Photos.PHAssetMediaTypeAudio

    @property
    def original_filename(self):
        """ Return original filename asset was imported with """
        resources = self._resources()
        for resource in resources:
            if (
                self.isphoto
                and resource.type() == Photos.PHAssetResourceTypePhoto
                or not self.isphoto
                and resource.type() == Photos.PHAssetResourceTypeVideo
            ):
                return resource.originalFilename()
        return None

    @property
    def hasadjustments(self):
        """ Check to see if a PHAsset has adjustment data associated with it
            Returns False if no adjustments, True if any adjustments """

        # reference: https://developer.apple.com/documentation/photokit/phassetresource/1623988-assetresourcesforasset?language=objc

        adjustment_resources = Photos.PHAssetResource.assetResourcesForAsset_(
            self.phasset
        )
        return any(
            (
                adjustment_resources.objectAtIndex_(idx).type()
                == Photos.PHAssetResourceTypeAdjustmentData
            )
            for idx in range(adjustment_resources.count())
        )

    @property
    def media_type(self):
        """ media type such as image or video """
        return self.phasset.mediaType()

    @property
    def media_subtypes(self):
        """ media subtype """
        return self.phasset.mediaSubtypes()

    @property
    def panorama(self):
        """ return True if asset is panorama, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypePhotoPanorama)

    @property
    def hdr(self):
        """ return True if asset is HDR, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypePhotoHDR)

    @property
    def screenshot(self):
        """ return True if asset is screenshot, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypePhotoScreenshot)

    @property
    def live(self):
        """ return True if asset is live, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypePhotoLive)

    @property
    def streamed(self):
        """ return True if asset is streamed video, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypeVideoStreamed)

    @property
    def slow_mo(self):
        """ return True if asset is slow motion (high frame rate) video, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypeVideoHighFrameRate)

    @property
    def time_lapse(self):
        """ return True if asset is time lapse video, otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypeVideoTimelapse)

    @property
    def portrait(self):
        """ return True if asset is portrait (depth effect), otherwise False """
        return bool(self.media_subtypes & Photos.PHAssetMediaSubtypePhotoDepthEffect)

    @property
    def burstid(self):
        """ return burstIdentifier of image if image is burst photo otherwise None """
        return self.phasset.burstIdentifier()

    @property
    def burst(self):
        """ return True if image is burst otherwise False """
        return bool(self.burstid)

    @property
    def source_type(self):
        """ the means by which the asset entered the user's library """
        return self.phasset.sourceType()

    @property
    def pixel_width(self):
        """ width in pixels """
        return self.phasset.pixelWidth()

    @property
    def pixel_height(self):
        """ height in pixels """
        return self.phasset.pixelHeight()

    @property
    def date(self):
        """ date asset was created """
        return self.phasset.creationDate()

    @property
    def date_modified(self):
        """ date asset was modified """
        return self.phasset.modificationDate()

    @property
    def location(self):
        """ location of the asset """
        return self.phasset.location()

    @property
    def duration(self):
        """ duration of the asset """
        return self.phasset.duration()

    @property
    def favorite(self):
        """ True if asset is favorite, otherwise False """
        return self.phasset.isFavorite()

    @property
    def hidden(self):
        """ True if asset is hidden, otherwise False """
        return self.phasset.isHidden()

    def metadata(self, version=PHOTOS_VERSION_CURRENT):
        """ Return dict of asset metadata
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        return imagedata.metadata

    def uti(self, version=PHOTOS_VERSION_CURRENT):
        """ Return UTI of asset
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        return imagedata.uti

    def url(self, version=PHOTOS_VERSION_CURRENT):
        """ Return URL of asset
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        return str(imagedata.info["PHImageFileURLKey"])

    def path(self, version=PHOTOS_VERSION_CURRENT):
        """ Return path of asset
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        url = imagedata.info["PHImageFileURLKey"]
        return url.fileSystemRepresentation().decode("utf-8")

    def orientation(self, version=PHOTOS_VERSION_CURRENT):
        """ Return orientation of asset
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        return imagedata.orientation

    @property
    def degraded(self, version=PHOTOS_VERSION_CURRENT):
        """ Return True if asset is degraded version 
        
        Args:
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
        """
        imagedata = self._request_image_data(version=version)
        return imagedata.info["PHImageResultIsDegradedKey"]

    def export(
        self, dest, filename=None, version=PHOTOS_VERSION_CURRENT, overwrite=False
    ):
        """ Export image to path

        Args:
            dest: str, path to destination directory
            filename: str, optional name of exported file; if not provided, defaults to asset's original filename
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
            overwrite: bool, if True, overwrites destination file if it already exists; default is False

        Returns:
            List of path to exported image(s)

        Raises:
            ValueError if dest is not a valid directory
        """

        # if self.live:
        #     raise NotImplementedError("Live photos not implemented yet")

        with objc.autorelease_pool():
            filename = (
                pathlib.Path(filename)
                if filename
                else pathlib.Path(self.original_filename)
            )

            dest = pathlib.Path(dest)
            if not dest.is_dir():
                raise ValueError("dest must be a valid directory: {dest}")

            output_file = None
            if self.isphoto:
                imagedata = self._request_image_data(version=version)
                if not imagedata.image_data:
                    raise PhotoKitExportError("Could not get image data")

                ext = get_preferred_uti_extension(imagedata.uti)

                output_file = dest / f"{filename.stem}.{ext}"

                if not overwrite:
                    output_file = pathlib.Path(increment_filename(output_file))

                with open(output_file, "wb") as fd:
                    fd.write(imagedata.image_data)
                    del imagedata
            elif self.ismovie:
                videodata = self._request_video_data(version=version)
                if videodata.asset is None:
                    raise PhotoKitExportError("Could not get video for asset")

                url = videodata.asset.URL()
                path = pathlib.Path(NSURL_to_path(url))
                if not path.is_file():
                    raise FileNotFoundError("Could not get path to video file")
                ext = path.suffix
                output_file = dest / f"{filename.stem}{ext}"

                if not overwrite:
                    output_file = pathlib.Path(increment_filename(output_file))

                FileUtil.copy(path, output_file)

            return [str(output_file)]

    def _request_image_data(self, version=PHOTOS_VERSION_ORIGINAL):
        """ Request image data and metadata for self._phasset 
            
        Args:
            version: which version to request
                     PHOTOS_VERSION_ORIGINAL (default), request original highest fidelity version 
                     PHOTOS_VERSION_CURRENT, request current version with all edits
                     PHOTOS_VERSION_UNADJUSTED, request highest quality unadjusted version
        
        Returns:
            ImageData instance

        Raises:
            ValueError if passed invalid value for version
        """

        # reference: https://developer.apple.com/documentation/photokit/phimagemanager/3237282-requestimagedataandorientationfo?language=objc

        with objc.autorelease_pool():
            if version not in [
                PHOTOS_VERSION_CURRENT,
                PHOTOS_VERSION_ORIGINAL,
                PHOTOS_VERSION_UNADJUSTED,
            ]:
                raise ValueError("Invalid value for version")

            # pylint: disable=no-member
            options_request = Photos.PHImageRequestOptions.alloc().init()
            options_request.setNetworkAccessAllowed_(True)
            options_request.setSynchronous_(True)
            options_request.setVersion_(version)
            options_request.setDeliveryMode_(
                Photos.PHImageRequestOptionsDeliveryModeHighQualityFormat
            )
            requestdata = ImageData()
            event = threading.Event()

            def handler(imageData, dataUTI, orientation, info):
                """ result handler for requestImageDataAndOrientationForAsset_options_resultHandler_ 
                    all returned by the request is set as properties of nonlocal data (Fetchdata object) """

                nonlocal requestdata

                options = {}
                # pylint: disable=no-member
                options[Quartz.kCGImageSourceShouldCache] = Foundation.kCFBooleanFalse
                imgSrc = Quartz.CGImageSourceCreateWithData(imageData, options)
                requestdata.metadata = Quartz.CGImageSourceCopyPropertiesAtIndex(
                    imgSrc, 0, options
                )
                requestdata.uti = dataUTI
                requestdata.orientation = orientation
                requestdata.info = info
                requestdata.image_data = imageData

                event.set()

            self._manager.requestImageDataAndOrientationForAsset_options_resultHandler_(
                self.phasset, options_request, handler
            )
            event.wait()
            # options_request.dealloc()

            # not sure why this is needed -- some weird ref count thing maybe
            # if I don't do this, memory leaks
            data = copy.copy(requestdata)
            del requestdata
            return data

    def _make_result_handle_(self, data):
        """ Make handler function and threading event to use with 
            requestImageDataAndOrientationForAsset_options_resultHandler_ 
            data: Fetchdata class to hold resulting metadata 
            returns: handler function, threading.Event() instance 
            Following call to requestImageDataAndOrientationForAsset_options_resultHandler_, 
            data will hold data from the fetch """

        event = threading.Event()

        def handler(imageData, dataUTI, orientation, info):
            """ result handler for requestImageDataAndOrientationForAsset_options_resultHandler_ 
                all returned by the request is set as properties of nonlocal data (Fetchdata object) """

            nonlocal data

            options = {}
            # pylint: disable=no-member
            options[Quartz.kCGImageSourceShouldCache] = Foundation.kCFBooleanFalse
            imgSrc = Quartz.CGImageSourceCreateWithData(imageData, options)
            data.metadata = Quartz.CGImageSourceCopyPropertiesAtIndex(
                imgSrc, 0, options
            )
            data.uti = dataUTI
            data.orientation = orientation
            data.info = info
            data.image_data = imageData

            event.set()

        return handler, event

    def _resources(self):
        """ Return list of PHAssetResource for object """
        resources = Photos.PHAssetResource.assetResourcesForAsset_(self.phasset)
        return [resources.objectAtIndex_(idx) for idx in range(resources.count())]


class SlowMoVideoExporter(NSObject):
    def initWithAVAsset_path_(self, avasset, path):
        """ init helper class for exporting slow-mo video

        Args:
            avasset: AVAsset
            path: python str; path to export to
        """
        self = objc.super(SlowMoVideoExporter, self).init()
        if self is None:
            return None
        self.avasset = avasset
        self.url = path_to_NSURL(path)
        self.nc = NSNotificationCenter.defaultCenter()
        return self

    def exportSlowMoVideo(self):
        """ export slow-mo video with AVAssetExportSession
        
        Returns:
            path to exported file
        """

        with objc.autorelease_pool():
            exporter = AVFoundation.AVAssetExportSession.alloc().initWithAsset_presetName_(
                self.avasset, AVFoundation.AVAssetExportPresetHighestQuality
            )
            exporter.setOutputURL_(self.url)
            exporter.setOutputFileType_(AVFoundation.AVFileTypeQuickTimeMovie)
            exporter.setShouldOptimizeForNetworkUse_(True)

            self.done = False

            def handler():
                """ result handler for exportAsynchronouslyWithCompletionHandler """
                self.done = True

            exporter.exportAsynchronouslyWithCompletionHandler_(handler)
            # wait for export to complete
            # would be more elegant to use a dispatch queue, notification, or thread event to wait
            # but I can't figure out how to make that work and this does work
            while True:
                status = exporter.status()
                if status == AVFoundation.AVAssetExportSessionStatusCompleted:
                    break
                elif status not in (
                    AVFoundation.AVAssetExportSessionStatusWaiting,
                    AVFoundation.AVAssetExportSessionStatusExporting,
                ):
                    raise PhotoKitExportError(
                        f"Error encountered during exportAsynchronouslyWithCompletionHandler: status = {status}"
                    )
                time.sleep(MIN_SLEEP)

            exported_path = NSURL_to_path(exporter.outputURL())
            # exporter.dealloc()
            return exported_path

    def __del__(self):
        self.avasset = None
        self.url.dealloc()
        self.url = None
        self.done = None
        self.nc = None
        # super(NSObject, self).dealloc()


class VideoAsset(PhotoAsset):
    """ PhotoKit PHAsset representation of video asset """

    # TODO: doesn't work for slow-mo videos
    # see https://stackoverflow.com/questions/26152396/how-to-access-nsdata-nsurl-of-slow-motion-videos-using-photokit
    # https://developer.apple.com/documentation/photokit/phimagemanager/1616935-requestavassetforvideo?language=objc
    # https://developer.apple.com/documentation/photokit/phimagemanager/1616981-requestexportsessionforvideo?language=objc
    # above 10.15 only
    def export(
        self, dest, filename=None, version=PHOTOS_VERSION_CURRENT, overwrite=False
    ):
        """ Export video to path

        Args:
            dest: str, path to destination directory
            filename: str, optional name of exported file; if not provided, defaults to asset's original filename
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
            overwrite: bool, if True, overwrites destination file if it already exists; default is False

        Returns:
            List of path to exported image(s)

        Raises:
            ValueError if dest is not a valid directory
        """

        with objc.autorelease_pool():
            if self.slow_mo and version == PHOTOS_VERSION_CURRENT:
                return [
                    self._export_slow_mo(
                        dest, filename=filename, version=version, overwrite=overwrite
                    )
                ]

            filename = (
                pathlib.Path(filename)
                if filename
                else pathlib.Path(self.original_filename)
            )

            dest = pathlib.Path(dest)
            if not dest.is_dir():
                raise ValueError("dest must be a valid directory: {dest}")

            output_file = None
            videodata = self._request_video_data(version=version)
            if videodata.asset is None:
                raise PhotoKitExportError("Could not get video for asset")

            url = videodata.asset.URL()
            path = pathlib.Path(NSURL_to_path(url))
            del videodata
            if not path.is_file():
                raise FileNotFoundError("Could not get path to video file")
            ext = path.suffix
            output_file = dest / f"{filename.stem}{ext}"

            if not overwrite:
                output_file = pathlib.Path(increment_filename(output_file))

            FileUtil.copy(path, output_file)

            return [str(output_file)]

    def _export_slow_mo(
        self, dest, filename=None, version=PHOTOS_VERSION_CURRENT, overwrite=False
    ):
        """ Export slow-motion video to path

        Args:
            dest: str, path to destination directory
            filename: str, optional name of exported file; if not provided, defaults to asset's original filename
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
            overwrite: bool, if True, overwrites destination file if it already exists; default is False

        Returns:
            Path to exported image

        Raises:
            ValueError if dest is not a valid directory
        """
        with objc.autorelease_pool():
            if not self.slow_mo:
                raise PhotoKitMediaTypeError("Not a slow-mo video")

            videodata = self._request_video_data(version=version)
            if (
                not isinstance(videodata.asset, AVFoundation.AVComposition)
                or len(videodata.asset.tracks()) != 2
            ):
                raise PhotoKitMediaTypeError("Does not appear to be slow-mo video")

            filename = (
                pathlib.Path(filename)
                if filename
                else pathlib.Path(self.original_filename)
            )

            dest = pathlib.Path(dest)
            if not dest.is_dir():
                raise ValueError("dest must be a valid directory: {dest}")

            output_file = dest / f"{filename.stem}.mov"

            if not overwrite:
                output_file = pathlib.Path(increment_filename(output_file))

            exporter = SlowMoVideoExporter.alloc().initWithAVAsset_path_(
                videodata.asset, output_file
            )
            video = exporter.exportSlowMoVideo()
            # exporter.dealloc()
            return video

    # todo: rewrite this with NotificationCenter and App event loop?
    def _request_video_data(self, version=PHOTOS_VERSION_ORIGINAL):
        """ Request video data for self._phasset 
            
        Args:
            version: which version to request
                     PHOTOS_VERSION_ORIGINAL (default), request original highest fidelity version 
                     PHOTOS_VERSION_CURRENT, request current version with all edits
                     PHOTOS_VERSION_UNADJUSTED, request highest quality unadjusted version
        
        Raises:
            ValueError if passed invalid value for version
        """
        with objc.autorelease_pool():
            if version not in [
                PHOTOS_VERSION_CURRENT,
                PHOTOS_VERSION_ORIGINAL,
                PHOTOS_VERSION_UNADJUSTED,
            ]:
                raise ValueError("Invalid value for version")

            options_request = Photos.PHVideoRequestOptions.alloc().init()
            options_request.setNetworkAccessAllowed_(True)
            options_request.setVersion_(version)
            options_request.setDeliveryMode_(
                Photos.PHVideoRequestOptionsDeliveryModeHighQualityFormat
            )
            requestdata = AVAssetData()
            event = threading.Event()

            def handler(asset, audiomix, info):
                """ result handler for requestAVAssetForVideo:asset options:options resultHandler """
                nonlocal requestdata

                requestdata.asset = asset
                requestdata.audiomix = audiomix
                requestdata.info = info

                event.set()

            self._manager.requestAVAssetForVideo_options_resultHandler_(
                self.phasset, options_request, handler
            )
            event.wait()

            # not sure why this is needed -- some weird ref count thing maybe
            # if I don't do this, memory leaks
            data = copy.copy(requestdata)
            del requestdata
            return data


class LivePhotoRequest(NSObject):
    """ Manage requests for live photo assets
        See: https://developer.apple.com/documentation/photokit/phimagemanager/1616984-requestlivephotoforasset?language=objc
    """

    def initWithManager_Asset_(self, manager, asset):
        self = objc.super(LivePhotoRequest, self).init()
        if self is None:
            return None
        self.manager = manager
        self.asset = asset
        self.nc = NSNotificationCenter.defaultCenter()
        return self

    def requestLivePhotoResources(self, version=PHOTOS_VERSION_CURRENT):
        """ return the photos and video components of a live video as [PHAssetResource] """

        with objc.autorelease_pool():
            options = Photos.PHLivePhotoRequestOptions.alloc().init()
            options.setNetworkAccessAllowed_(True)
            options.setVersion_(version)
            options.setDeliveryMode_(
                Photos.PHVideoRequestOptionsDeliveryModeHighQualityFormat
            )
            delegate = PhotoKitNotificationDelegate.alloc().init()

            self.nc.addObserver_selector_name_object_(
                delegate, "liveNotification:", None, None
            )

            self.live_photo = None

            def handler(result, info):
                """ result handler for requestLivePhotoForAsset:targetSize:contentMode:options:resultHandler: """
                if not info["PHImageResultIsDegradedKey"]:
                    self.live_photo = result
                    self.info = info
                    self.nc.postNotificationName_object_(
                        PHOTOKIT_NOTIFICATION_FINISHED_REQUEST, self
                    )

            try:
                self.manager.requestLivePhotoForAsset_targetSize_contentMode_options_resultHandler_(
                    self.asset,
                    Photos.PHImageManagerMaximumSize,
                    Photos.PHImageContentModeDefault,
                    options,
                    handler,
                )
                AppHelper.runConsoleEventLoop(installInterrupt=True)
            except KeyboardInterrupt:
                AppHelper.stopEventLoop()
            finally:
                pass

            asset_resources = Photos.PHAssetResource.assetResourcesForLivePhoto_(
                self.live_photo
            )

            # not sure why this is needed -- some weird ref count thing maybe
            # if I don't do this, memory leaks
            data = copy.copy(asset_resources)
            del asset_resources
            return data

    def __del__(self):
        self.manager = None
        self.asset = None
        self.nc = None
        self.live_photo = None
        self.info = None
        # super(NSObject, self).dealloc()


class LivePhotoAsset(PhotoAsset):
    """ Represents a live photo """

    def export(
        self,
        dest,
        filename=None,
        version=PHOTOS_VERSION_CURRENT,
        overwrite=False,
        photo=True,
        video=True,
    ):
        """ Export image to path

        Args:
            dest: str, path to destination directory
            filename: str, optional name of exported file; if not provided, defaults to asset's original filename
            version: which version of image (PHOTOS_VERSION_ORIGINAL or PHOTOS_VERSION_CURRENT)
            overwrite: bool, if True, overwrites destination file if it already exists; default is False
            photo: bool, if True, export photo component of live photo
            video: bool, if True, export live video component of live photo

        Returns:
            list of [path to exported image and/or video]

        Raises:
            ValueError if dest is not a valid directory
            PhotoKitExportError if error during export
        """

        with objc.autorelease_pool():
            filename = (
                pathlib.Path(filename)
                if filename
                else pathlib.Path(self.original_filename)
            )

            dest = pathlib.Path(dest)
            if not dest.is_dir():
                raise ValueError("dest must be a valid directory: {dest}")

            request = LivePhotoRequest.alloc().initWithManager_Asset_(
                self._manager, self.phasset
            )
            resources = request.requestLivePhotoResources(version=version)

            video_resource = None
            photo_resource = None
            for resource in resources:
                if resource.type() == Photos.PHAssetResourceTypePairedVideo:
                    video_resource = resource
                elif resource.type() == Photos.PHAssetMediaTypeImage:
                    photo_resource = resource

            if not video_resource or not photo_resource:
                raise PhotoKitExportError(
                    "Did not find photo/video resources for live photo"
                )

            photo_ext = get_preferred_uti_extension(
                photo_resource.uniformTypeIdentifier()
            )
            photo_output_file = dest / f"{filename.stem}.{photo_ext}"
            video_ext = get_preferred_uti_extension(
                video_resource.uniformTypeIdentifier()
            )
            video_output_file = dest / f"{filename.stem}.{video_ext}"

            if not overwrite:
                photo_output_file = pathlib.Path(increment_filename(photo_output_file))
                video_output_file = pathlib.Path(increment_filename(video_output_file))

            # def handler(error):
            #     if error:
            #         raise PhotoKitExportError(f"writeDataForAssetResource error: {error}")

            # resource_manager = Photos.PHAssetResourceManager.defaultManager()
            # options = Photos.PHAssetResourceRequestOptions.alloc().init()
            # options.setNetworkAccessAllowed_(True)
            # exported = []
            # Note: Tried writeDataForAssetResource_toFile_options_completionHandler_ which works
            # but sets quarantine flag and for reasons I can't determine (maybe quarantine flag)
            # causes pathlib.Path().is_file() to fail in tests

            # if photo:
            #     photo_output_url = path_to_NSURL(photo_output_file)
            #     resource_manager.writeDataForAssetResource_toFile_options_completionHandler_(
            #         photo_resource, photo_output_url, options, handler
            #     )
            #     exported.append(str(photo_output_file))

            # if video:
            #     video_output_url = path_to_NSURL(video_output_file)
            #     resource_manager.writeDataForAssetResource_toFile_options_completionHandler_(
            #         video_resource, video_output_url, options, handler
            #     )
            #     exported.append(str(video_output_file))

            # def completion_handler(error):
            #     if error:
            #         raise PhotoKitExportError(f"writeDataForAssetResource error: {error}")

            # would be nice to be able to usewriteDataForAssetResource_toFile_options_completionHandler_
            # but it sets quarantine flags that cause issues so instead, request the data and write the files directly

            exported = []
            if photo:
                data = self._request_resource_data(photo_resource)
                # image_data = self.request_image_data(version=version)
                with open(photo_output_file, "wb") as fd:
                    fd.write(data)
                exported.append(str(photo_output_file))
                del data
            if video:
                data = self._request_resource_data(video_resource)
                with open(video_output_file, "wb") as fd:
                    fd.write(data)
                exported.append(str(video_output_file))
                del data

            request.dealloc()
            return exported

    def _request_resource_data(self, resource):
        """ Request asset resource data (either photo or video component)
            
        Args:
            resource: PHAssetResource to request
        
        Raises:
        """

        with objc.autorelease_pool():
            resource_manager = Photos.PHAssetResourceManager.defaultManager()
            options = Photos.PHAssetResourceRequestOptions.alloc().init()
            options.setNetworkAccessAllowed_(True)

            requestdata = PHAssetResourceData()
            event = threading.Event()

            def handler(data):
                """ result handler for requestImageDataAndOrientationForAsset_options_resultHandler_ 
                    all returned by the request is set as properties of nonlocal data (Fetchdata object) """

                nonlocal requestdata

                requestdata.data += data

            def completion_handler(error):
                if error:
                    raise PhotoKitExportError(
                        "Error requesting data for asset resource"
                    )
                event.set()

            resource_manager.requestDataForAssetResource_options_dataReceivedHandler_completionHandler_(
                resource, options, handler, completion_handler
            )

            event.wait()

            # not sure why this is needed -- some weird ref count thing maybe
            # if I don't do this, memory leaks
            data = copy.copy(requestdata.data)
            del requestdata
            return data

    # def request_image_data(self, version=PHOTOS_VERSION_CURRENT):
    #     # Returns an NSImage which isn't overly useful
    #     # https://developer.apple.com/documentation/photokit/phimagemanager/1616964-requestimageforasset?language=objc

    #     # requestImageForAsset:targetSize:contentMode:options:resultHandler:

    #     options = Photos.PHImageRequestOptions.alloc().init()
    #     options.setVersion_(version)
    #     options.setNetworkAccessAllowed_(True)
    #     options.setSynchronous_(True)
    #     options.setDeliveryMode_(
    #         Photos.PHImageRequestOptionsDeliveryModeHighQualityFormat
    #     )

    #     event = threading.Event()
    #     image_data = ImageData()

    #     def handler(result, info):
    #         nonlocal image_data
    #         if not info["PHImageResultIsDegradedKey"]:
    #             image_data.image_data = result
    #             image_data.info = info
    #             event.set()

    #     self._manager.requestImageForAsset_targetSize_contentMode_options_resultHandler_(
    #         self._phasset,
    #         Photos.PHImageManagerMaximumSize,
    #         Photos.PHImageContentModeDefault,
    #         options,
    #         handler,
    #     )
    #     event.wait()
    #     options.dealloc()
    #     return image_data


class PhotoLibrary:
    """ Interface to PhotoKit PHImageManager and PHPhotoLibrary """

    def __init__(self):
        """ Initialize ImageManager instance.  Requests authorization to use the 
        Photos library if authorization has not already been granted.
        
        Raises:
            PhotoKitAuthError if unable to authorize access to PhotoKit
        """
        # # pylint: disable=no-member
        # options = Photos.PHContentEditingInputRequestOptions.alloc().init()
        # options.setNetworkAccessAllowed_(network_access)

        # check authorization status
        auth_status = self.request_authorization()
        if auth_status != Photos.PHAuthorizationStatusAuthorized:
            raise PhotoKitAuthError(
                f"Could not get authorizaton to use Photos: auth_status = {auth_status}"
            )

        # get image manager and request options
        self._phimagemanager = Photos.PHCachingImageManager.defaultManager()

    def request_authorization(self):
        """ Request authorization to user's Photos Library

        Returns:
            authorization status
        """

        self.auth_status = request_photokit_authorization()
        return self.auth_status

    def fetch_uuid_list(self, uuid_list):
        """ fetch PHAssets with uuids in uuid_list

        Args:
            uuid_list: list of str (UUID of image assets to fetch)

        Returns:
            list of PhotoAsset objects

        Raises:
            PhotoKitFetchFailed if fetch failed
        """

        # pylint: disable=no-member
        with objc.autorelease_pool():
            fetch_options = Photos.PHFetchOptions.alloc().init()
            fetch_result = Photos.PHAsset.fetchAssetsWithLocalIdentifiers_options_(
                uuid_list, fetch_options
            )
            if fetch_result and fetch_result.count() >= 1:
                return [
                    self._asset_factory(fetch_result.objectAtIndex_(idx))
                    for idx in range(fetch_result.count())
                ]
            else:
                raise PhotoKitFetchFailed(
                    f"Fetch did not return result for uuid_list {uuid_list}"
                )

    def fetch_uuid(self, uuid):
        """ fetch PHAsset with uuid = uuid

        Args:
            uuid: str; UUID of image asset to fetch

        Returns:
            PhotoAsset object

        Raises:
            PhotoKitFetchFailed if fetch failed
        """
        try:
            result = self.fetch_uuid_list([uuid])
            return result[0]
        except:
            raise PhotoKitFetchFailed(f"Fetch did not return result for uuid {uuid}")

    def fetch_burst_uuid(self, burstid, all=False):
        """ fetch PhotoAssets with burst ID = burstid 
        
        Args:
            burstid: str, burst UUID
            all: return all burst assets; if False returns only those selected by the user

        Returns:
            list of PhotoAsset objects

        Raises:
            PhotoKitFetchFailed if fetch failed
        """

        # pylint: disable=no-member
        fetch_options = Photos.PHFetchOptions.alloc().init()
        fetch_options.setIncludeAllBurstAssets_(all)
        fetch_results = Photos.PHAsset.fetchAssetsWithBurstIdentifier_options_(
            burstid, fetch_options
        )
        if fetch_results and fetch_results.count() >= 1:
            return [
                self._asset_factory(fetch_results.objectAtIndex_(idx))
                for idx in range(fetch_results.count())
            ]
        else:
            raise PhotoKitFetchFailed(
                f"Fetch did not return result for burstid {burstid}"
            )

    def _asset_factory(self, phasset):
        """ creates a PhotoAsset, VideoAsset, or LivePhotoAsset

        Args:
            phasset: PHAsset object 
        
        Returns:
            PhotoAsset, VideoAsset, or LivePhotoAsset depending on type of PHAsset
        """

        if not isinstance(phasset, Photos.PHAsset):
            raise TypeError("phasset must be type PHAsset")

        media_type = phasset.mediaType()
        media_subtypes = phasset.mediaSubtypes()

        if media_subtypes & Photos.PHAssetMediaSubtypePhotoLive:
            return LivePhotoAsset(self._phimagemanager, phasset)
        elif media_type == Photos.PHAssetMediaTypeImage:
            return PhotoAsset(self._phimagemanager, phasset)
        elif media_type == Photos.PHAssetMediaTypeVideo:
            return VideoAsset(self._phimagemanager, phasset)
        else:
            raise PhotoKitMediaTypeError(f"Unknown media type: {media_type}")
