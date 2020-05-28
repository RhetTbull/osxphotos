import os
import pytest
from click.testing import CliRunner

from osxphotos.exiftool import get_exiftool_path

CLI_PHOTOS_DB = "tests/Test-10.15.1.photoslibrary"
LIVE_PHOTOS_DB = "tests/Test-Cloud-10.15.1.photoslibrary"
RAW_PHOTOS_DB = "tests/Test-RAW-10.15.1.photoslibrary"
PLACES_PHOTOS_DB = "tests/Test-Places-Catalina-10_15_1.photoslibrary"
PLACES_PHOTOS_DB_13 = "tests/Test-Places-High-Sierra-10.13.6.photoslibrary"
PHOTOS_DB_15_4 = "tests/Test-10.15.4.photoslibrary"
PHOTOS_DB_14_6 = "tests/Test-10.14.6.photoslibrary"

CLI_OUTPUT_NO_SUBCOMMAND = [
    "Options:",
    "--db <Photos database path>  Specify Photos database path. Path to Photos",
    "library/database can be specified using either",
    "--db or directly as PHOTOS_LIBRARY positional",
    "argument.",
    "--json                       Print output in JSON format.",
    "-v, --version                Show the version and exit.",
    "-h, --help                   Show this message and exit.",
    "Commands:",
    "  albums    Print out albums found in the Photos library.",
    "  dump      Print list of all photos & associated info from the Photos",
    "  export    Export photos from the Photos database.",
    "  help      Print help; for help on commands: help <command>.",
    "  info      Print out descriptive info of the Photos library database.",
    "  keywords  Print out keywords found in the Photos library.",
    "  list      Print list of Photos libraries found on the system.",
    "  persons   Print out persons (faces) found in the Photos library.",
    "  places    Print out places found in the Photos library.",
    "  query     Query the Photos database using 1 or more search options; if",
]

CLI_OUTPUT_QUERY_UUID = '[{"uuid": "D79B8D77-BFFC-460B-9312-034F2877D35B", "filename": "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "original_filename": "Pumkins2.jpg", "date": "2018-09-28T16:07:07-04:00", "description": "Girl holding pumpkin", "title": "I found one!", "keywords": ["Kids"], "albums": ["Pumpkin Farm", "Test Album", "Multi Keyword"], "persons": ["Katie"], "path": "/tests/Test-10.15.1.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": null, "longitude": null, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null}]'

CLI_EXPORT_FILENAMES = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_FILENAMES_CURRENT = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C.jpeg",
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.cr2",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.jpeg",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4.jpeg",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.cr2",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.jpeg",
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068.dng",
    "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30_edited.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_edited.jpeg",
    "F12384F6-CD17-4151-ACBA-AE0E3688539E.jpeg",
]


CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1 = [
    "2019/April/wedding.jpg",
    "2019/July/Tulips.jpg",
    "2018/October/St James Park.jpg",
    "2018/September/Pumpkins3.jpg",
    "2018/September/Pumkins2.jpg",
    "2018/September/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_LOCALE = [
    "2019/September/IMG_9975.JPEG",
    "2020/Februar/IMG_1064.JPEG",
    "2016/März/IMG_3984.JPEG",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM1 = [
    "Multi Keyword/wedding.jpg",
    "_/Tulips.jpg",
    "_/St James Park.jpg",
    "Pumpkin Farm/Pumpkins3.jpg",
    "Pumpkin Farm/Pumkins2.jpg",
    "Pumpkin Farm/Pumkins1.jpg",
    "Test Album/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM2 = [
    "Multi Keyword/wedding.jpg",
    "NOALBUM/Tulips.jpg",
    "NOALBUM/St James Park.jpg",
    "Pumpkin Farm/Pumpkins3.jpg",
    "Pumpkin Farm/Pumkins2.jpg",
    "Pumpkin Farm/Pumkins1.jpg",
    "Test Album/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES2 = [
    "St James's Park, Great Britain, Westminster, England, United Kingdom/St James Park.jpg",
    "_/Pumpkins3.jpg",
    "_/Pumkins2.jpg",
    "_/Pumkins1.jpg",
    "_/Tulips.jpg",
    "_/wedding.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES3 = [
    "2019/{foo}/wedding.jpg",
    "2019/{foo}/Tulips.jpg",
    "2018/{foo}/St James Park.jpg",
    "2018/{foo}/Pumpkins3.jpg",
    "2018/{foo}/Pumkins2.jpg",
    "2018/{foo}/Pumkins1.jpg",
]

CLI_EXPORT_UUID = "D79B8D77-BFFC-460B-9312-034F2877D35B"

CLI_EXPORT_UUID_FILENAME = "Pumkins2.jpg"

CLI_EXPORT_BY_DATE = ["2018/09/28/Pumpkins3.jpg", "2018/09/28/Pumkins1.jpg"]

CLI_EXPORT_SIDECAR_FILENAMES = ["Pumkins2.jpg", "Pumkins2.json", "Pumkins2.xmp"]

CLI_EXPORT_LIVE = [
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.jpeg",
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.mov",
]

CLI_EXPORT_LIVE_ORIGINAL = ["IMG_0728.JPG", "IMG_0728.mov"]

CLI_EXPORT_RAW = ["441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2"]
CLI_EXPORT_RAW_ORIGINAL = ["IMG_0476_2.CR2"]
CLI_EXPORT_RAW_EDITED = [
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2",
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C_edited.jpeg",
]
CLI_EXPORT_RAW_EDITED_ORIGINAL = ["IMG_0476_2.CR2", "IMG_0476_2_edited.jpeg"]

CLI_PLACES_JSON = """{"places": {"_UNKNOWN_": 1, "Maui, Wailea, Hawai'i, United States": 1, "Washington, District of Columbia, United States": 1}}"""

CLI_EXIFTOOL = {
    "D79B8D77-BFFC-460B-9312-034F2877D35B": {
        "File:FileName": "Pumkins2.jpg",
        "IPTC:Keywords": "Kids",
        "XMP:TagsList": "Kids",
        "XMP:Title": "I found one!",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:PersonInImage": "Katie",
        "XMP:Subject": ["Kids", "Katie"],
    }
}
# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool = get_exiftool_path()
except:
    exiftool = None


def test_osxphotos():
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])
    output = result.output
    assert result.exit_code == 0
    for line in CLI_OUTPUT_NO_SUBCOMMAND:
        assert line in output


def test_osxphotos_help_1():
    # test help command no topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help"])
    output = result.output
    assert result.exit_code == 0
    for line in CLI_OUTPUT_NO_SUBCOMMAND:
        assert line in output


def test_osxphotos_help_2():
    # test help command valid topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help", "persons"])
    output = result.output
    assert result.exit_code == 0
    assert "Print out persons (faces) found in the Photos library." in result.output


def test_osxphotos_help_3():
    # test help command invalid topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help", "foo"])
    output = result.output
    assert result.exit_code == 0
    assert "Invalid command: foo" in result.output


def test_query_uuid():
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            # "./tests/Test-10.15.1.photoslibrary",
            "--uuid",
            "D79B8D77-BFFC-460B-9312-034F2877D35B",
        ],
    )
    assert result.exit_code == 0

    json_expected = json.loads(CLI_OUTPUT_QUERY_UUID)[0]
    json_got = json.loads(result.output)[0]

    assert list(json_expected.keys()).sort() == list(json_got.keys()).sort()

    # check values expected vs got
    # path needs special handling as path is set to full path which will differ system to system
    for key_ in json_expected:
        assert key_ in json_got
        if key_ != "path":
            assert json_expected[key_] == json_got[key_]
        else:
            assert json_expected[key_] in json_got[key_]


def test_export():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_as_hardlink():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--export-as-hardlink", "-V"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_as_hardlink_samefile():
    # test that --export-as-hardlink actually creates a hardlink
    # src and dest should be same file
    import os
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                f"--uuid={CLI_EXPORT_UUID}",
                "--export-as-hardlink",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists(CLI_EXPORT_UUID_FILENAME)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_using_hardlinks_incompat_options():
    # test that error shown if --export-as-hardlink used with --exiftool
    import os
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                f"--uuid={CLI_EXPORT_UUID}",
                "--export-as-hardlink",
                "--exiftool",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert "Incompatible export options" in result.output


def test_export_current_name():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_4), ".", "--current-name", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CURRENT)


def test_export_skip_edited():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--skip-edited", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert "St James Park_edited.jpeg" not in files


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_4),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert sorted(files) == sorted([CLI_EXIFTOOL[uuid]["File:FileName"]])

            exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).as_dict()
            for key in CLI_EXIFTOOL[uuid]:
                assert exif[key] == CLI_EXIFTOOL[uuid][key]


def test_query_date():
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--from-date=2018-09-28",
            "--to-date=2018-09-28T23:00:00",
        ],
    )
    assert result.exit_code == 0
    import logging

    logging.warning(result.output)

    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_export_sidecar():
    import glob
    import os
    import os.path
    import osxphotos

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_FILENAMES)


def test_export_live():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, LIVE_PHOTOS_DB), ".", "--live", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_LIVE_ORIGINAL)


def test_export_skip_live():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, LIVE_PHOTOS_DB), ".", "--skip-live", "-V"]
        )
        files = glob.glob("*")
        assert "img_0728.mov" not in [f.lower() for f in files]


def test_export_raw():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, RAW_PHOTOS_DB),
                ".",
                "--current-name",
                "--skip-edited",
                "-V",
            ],
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW)


# TODO: Update this once RAW db is added
# def test_skip_raw():
#     import glob
#     import os
#     import os.path
#     import osxphotos
#     from osxphotos.__main__ import export

#     runner = CliRunner()
#     cwd = os.getcwd()
#     # pylint: disable=not-context-manager
#     with runner.isolated_filesystem():
#         result = runner.invoke(
#             export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--skip-raw", "-V"]
#         )
#         files = glob.glob("*")
#         for rawname in CLI_EXPORT_RAW:
#             assert rawname.lower() not in [f.lower() for f in files]


def test_export_raw_original():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--skip-edited", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_ORIGINAL)


def test_export_raw_edited():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--current-name", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_EDITED)


def test_export_raw_edited_original():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "-V"])
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_EDITED_ORIGINAL)


def test_export_directory_template_1():
    # test export using directory template
    import glob
    import locale
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_2():
    # test export using directory template with missing substitution value
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{place.name}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES2:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_3():
    # test export using directory template with unmatched substituion value
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{foo}",
            ],
        )
        assert result.exit_code == 2
        assert "Error: Invalid substitution in template" in result.output


def test_export_directory_template_album_1():
    # test export using directory template with multiple albums
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--directory", "{album}"],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM1:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_album_2():
    # test export using directory template with multiple albums
    # specify default value
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{album,NOALBUM}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM2:
            assert os.path.isfile(os.path.join(workdir, filepath))


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_LOCALE" not in os.environ,
    reason="Skip if running in Github actions",
)
def test_export_directory_template_locale():
    # test export using directory template in user locale non-US
    import os
    import glob
    import locale
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # set locale environment
        os.environ["LANG"] = "de_DE.UTF-8"
        os.environ["LC_COLLATE"] = "de_DE.UTF-8"
        os.environ["LC_CTYPE"] = "de_DE.UTF-8"
        os.environ["LC_MESSAGES"] = "de_DE.UTF-8"
        os.environ["LC_MONETARY"] = "de_DE.UTF-8"
        os.environ["LC_NUMERIC"] = "de_DE.UTF-8"
        os.environ["LC_TIME"] = "de_DE.UTF-8"
        locale.setlocale(locale.LC_ALL, "")
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PLACES_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_LOCALE:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_places():
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import places

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(places, [os.path.join(cwd, PLACES_PHOTOS_DB), "--json"])
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert json_got == json.loads(CLI_PLACES_JSON)


def test_place_13():
    # test --place on 10.13
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB_13), "--json", "--place", "Adelaide"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "2L6X2hv3ROWRSCU3WRRAGQ"


def test_no_place_13():
    # test --no-place on 10.13
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PLACES_PHOTOS_DB_13), "--json", "--no-place"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "pERZk5T1Sb+XcKDFRCsGpA"


def test_place_15_1():
    # test --place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--place", "Washington"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "128FB4C6-0B16-4E7D-9108-FB2E90DA1546"


def test_place_15_2():
    # test --place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--place", "United States"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        uuid = [json_got[x]["uuid"] for x in (0, 1)]
        assert "128FB4C6-0B16-4E7D-9108-FB2E90DA1546" in uuid
        assert "FF7AFE2C-49B0-4C9B-B0D7-7E1F8B8F2F0C" in uuid


def test_no_place_15():
    # test --no-place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--no-place"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "A9B73E13-A6F2-4915-8D67-7213B39BAE9F"


def test_no_folder_1_15():
    # test --folder on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PHOTOS_DB_15_4), "--json", "--folder", "Folder1"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        for item in json_got:
            assert item["uuid"] in [
                "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
                "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
            ]
            assert item["albums"] == ["AlbumInFolder"]


def test_no_folder_2_15():
    # test --folder with --uuid on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                os.path.join(cwd, PHOTOS_DB_15_4),
                "--json",
                "--folder",
                "Folder1",
                "--uuid",
                "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        for item in json_got:
            assert item["uuid"] == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"
            assert item["albums"] == ["AlbumInFolder"]


def test_no_folder_1_14():
    # test --folder on 10.14
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PHOTOS_DB_14_6), "--json", "--folder", "Folder1"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "15uNd7%8RguTEgNPKHfTWw"


def test_export_sidecar_keyword_template():
    import json
    import glob
    import os
    import os.path
    import osxphotos

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                "--keyword-template",
                "{folder_album}",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_FILENAMES)

        json_expected = json.loads(
            """
        [{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:Title": "I found one!",
        "XMP:TagsList": ["Kids", "Multi Keyword", "Test Album", "Pumpkin Farm"],
        "IPTC:Keywords": ["Kids", "Multi Keyword", "Test Album", "Pumpkin Farm"],
        "XMP:PersonInImage": ["Katie"],
        "XMP:Subject": ["Kids", "Katie"],
        "EXIF:DateTimeOriginal": "2018:09:28 16:07:07",
        "EXIF:OffsetTimeOriginal": "-04:00",
        "EXIF:ModifyDate": "2020:04:11 12:34:16"}]"""
        )[0]

        import logging

        json_file = open("Pumkins2.json", "r")
        json_got = json.load(json_file)[0]
        json_file.close()

        # some gymnastics to account for different sort order in different pythons
        for k, v in json_got.items():
            if type(v) in (list, tuple):
                assert sorted(json_expected[k]) == sorted(v)
            else:
                assert json_expected[k] == v

        for k, v in json_expected.items():
            if type(v) in (list, tuple):
                assert sorted(json_got[k]) == sorted(v)
            else:
                assert json_got[k] == v


def test_export_update_basic():
    """ test export then update """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)

        # update
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            "Exported: 0 photos, updated: 0 photos, skipped: 8 photos, updated EXIF data: 0 photos"
            in result.output
        )


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_exiftool():
    """ test export then update with exiftool """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)

        # update with exiftool
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            "Exported: 0 photos, updated: 8 photos, skipped: 0 photos, updated EXIF data: 8 photos"
            in result.output
        )


def test_export_update_hardlink():
    """ test export with hardlink then update """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-as-hardlink"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        # update, should replace the hardlink files with new copies
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            "Exported: 0 photos, updated: 8 photos, skipped: 0 photos, updated EXIF data: 0 photos"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_hardlink_exiftool():
    """ test export with hardlink then update with exiftool """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-as-hardlink"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        # update, should replace the hardlink files with new copies
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            "Exported: 0 photos, updated: 8 photos, skipped: 0 photos, updated EXIF data: 8 photos"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_update_edits():
    """ test export then update after removing and editing files """
    import glob
    import os
    import os.path
    import shutil

    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-by-date"]
        )
        assert result.exit_code == 0

        # change a couple of destination photos
        os.unlink(CLI_EXPORT_BY_DATE[1])
        shutil.copyfile(CLI_EXPORT_BY_DATE[0], CLI_EXPORT_BY_DATE[1])
        os.unlink(CLI_EXPORT_BY_DATE[0])

        # update
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--export-by-date"],
        )
        assert result.exit_code == 0
        assert (
            "Exported: 1 photo, updated: 1 photo, skipped: 6 photos, updated EXIF data: 0 photos"
            in result.output
        )


def test_export_update_no_db():
    """ test export then update after db has been deleted """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)
        os.unlink(OSXPHOTOS_EXPORT_DB)

        # update
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            "Exported: 0 photos, updated: 0 photos, skipped: 8 photos, updated EXIF data: 0 photos"
            in result.output
        )
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)


def test_export_then_hardlink():
    """ test export then hardlink """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--export-as-hardlink",
                "--overwrite",
            ],
        )
        assert result.exit_code == 0
        assert "Exported: 8 photos" in result.output
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_dry_run():
    """ test export with dry-run flag """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Exported: 8 photos" in result.output
        for filepath in CLI_EXPORT_FILENAMES:
            assert f"Exported {filepath}" in result.output
            assert not os.path.isfile(filepath)


def test_export_update_edits_dry_run():
    """ test export then update after removing and editing files with dry-run flag """
    import glob
    import os
    import os.path
    import shutil

    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-by-date"]
        )
        assert result.exit_code == 0

        # change a couple of destination photos
        os.unlink(CLI_EXPORT_BY_DATE[1])
        shutil.copyfile(CLI_EXPORT_BY_DATE[0], CLI_EXPORT_BY_DATE[1])
        os.unlink(CLI_EXPORT_BY_DATE[0])

        # update dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--update",
                "--export-by-date",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert (
            "Exported: 1 photo, updated: 1 photo, skipped: 6 photos, updated EXIF data: 0 photos"
            in result.output
        )

        # make sure file didn't really get copied
        assert not os.path.isfile(CLI_EXPORT_BY_DATE[0])


def test_export_directory_template_1_dry_run():
    """ test export using directory template with dry-run flag """
    import glob
    import locale
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Exported: 8 photos" in result.output
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1:
            assert f"Exported {filepath}" in result.output
            assert not os.path.isfile(os.path.join(workdir, filepath))
