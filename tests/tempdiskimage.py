""" Create a temporary disk image on MacOS """

import pathlib
import platform
import subprocess
import tempfile
import time


class TempDiskImage:
    """ Create and mount a temporary disk image """

    def __init__(self, size=100, prefix=None):
        """ Create and mount a temporary disk image.
        
        Args:
            size: int; size in MB of disk image, default = 100
            prefix: str; optional prefix to prepend to name of the temporary disk image
            name: str; name of the mounted volume, default = "TemporaryDiskImage"

        Raises:
            TypeError if size is not int
            RunTimeError if not on MacOS
        """
        if type(size) != int:
            raise TypeError("size must be int")

        system = platform.system()
        if system != "Darwin":
            raise RuntimeError("TempDiskImage only runs on MacOS")

        self._tempdir = tempfile.TemporaryDirectory()
        # hacky mktemp: this could create a race condition but unlikely given it's created in a TemporaryDirectory
        prefix = "TemporaryDiskImage" if prefix is None else prefix
        volume_name = f"{prefix}_{str(time.time()).replace('.','_')}_{str(time.perf_counter()).replace('.','_')}"
        image_name = f"{volume_name}.dmg"
        image_path = pathlib.Path(self._tempdir.name) / image_name
        hdiutil = subprocess.run(
            [
                "/usr/bin/hdiutil",
                "create",
                "-size",
                f"{size}m",
                "-fs",
                "HFS+",
                "-volname",
                volume_name,
                image_path,
            ],
            check=True,
            text=True,
            capture_output=True,
        )

        if "created" not in hdiutil.stdout:
            raise OSError(f"Could not create DMG {image_path}")

        self.path = image_path
        self._mount_point, self.name = self._mount_image(self.path)

    def _mount_image(self, image_path):
        """ mount a DMG file and return path, returns (mount_point, path) """
        hdiutil = subprocess.run(
            ["/usr/bin/hdiutil", "attach", image_path],
            check=True,
            text=True,
            capture_output=True,
        )
        mount_point, path = None, None
        for line in hdiutil.stdout.split("\n"):
            line = line.strip()
            if "Apple_HFS" not in line:
                continue
            output = line.split()
            if len(output) < 3:
                raise ValueError(f"Error mounting disk image {image_path}")
            mount_point = output[0]
            path = output[2]
            break
        return (mount_point, path)

    def unmount(self):
        try:
            if self._mount_point:
                hdiutil = subprocess.run(
                    ["/usr/bin/hdiutil", "detach", self._mount_point],
                    check=True,
                    text=True,
                    capture_output=True,
                )
                self._mount_point = None
        except AttributeError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.unmount()
        if exc_type:
            return False


if __name__ == "__main__":
    # Create a temporary disk image, 50mb in size
    img = TempDiskImage(size=50, prefix="MyDiskImage")
    # Be sure to unmount it, image will be cleaned up automatically
    img.unmount()

    # Or use it as a context handler
    # Default values are 100mb and prefix = "TemporaryDiskImage"
    with TempDiskImage() as img:
        print(f"image: {img.path}")
        print(f"mounted at: {img.name}")
