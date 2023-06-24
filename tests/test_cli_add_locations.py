"""Test osxphotos add-locations command"""

import pytest
from click.testing import CliRunner

from osxphotos.platform import is_macos

if is_macos:
    import photoscript

    from osxphotos.cli.add_locations import add_locations
else:
    pytest.skip(allow_module_level=True)

UUID_TEST_PHOTO_1 = "F12384F6-CD17-4151-ACBA-AE0E3688539E"  # Pumkins1.jpg
UUID_TEST_PHOTO_LOCATION = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
TEST_LOCATION = (41.26067, -95.94056)  # Omaha, NE


@pytest.mark.test_add_locations
def test_add_locations():
    """Test add-locations command"""

    with CliRunner().isolated_filesystem():
        # need to clear location data from test photo
        test_photo = photoscript.Photo(UUID_TEST_PHOTO_1)
        test_photo.location = None
        source_photo = photoscript.Photo(UUID_TEST_PHOTO_LOCATION)
        source_photo.location = TEST_LOCATION

        # now run add-locations
        result = CliRunner().invoke(
            add_locations,
            [
                "--window",
                "2 hours",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        # should find 3 matching locations: Pumkins1.jpg, Pumpkins3.jpg, Pumpkins4.jpg
        assert "found location: 3" in result.output

        # verify location not really added
        assert test_photo.location == (None, None)

        # run again without dry-run
        result = CliRunner().invoke(
            add_locations,
            [
                "--window",
                "2 hours",
            ],
        )
        assert result.exit_code == 0
        # should find 3 matching locations: Pumkins1.jpg, Pumpkins3.jpg, Pumpkins4.jpg
        assert "found location: 3" in result.output
        assert test_photo.location == TEST_LOCATION
