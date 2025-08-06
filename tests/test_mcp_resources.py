import pytest
from unittest.mock import Mock, patch, mock_open
from osxphotos.mcp_server import resources

@pytest.fixture
def mock_db():
    """Fixture to create a mock PhotosDB object."""
    db = Mock()
    db.library_path = "/tmp/photos"
    db.db_path = "/tmp/photos/db"
    db.db_version = "6.0"
    
    photo1 = Mock()
    photo1.uuid = "photo1_uuid"
    photo1.asdict.return_value = {"uuid": "photo1_uuid", "title": "Photo 1"}
    photo1.path_derivatives = ["/tmp/thumb.jpg"]
    
    album1 = Mock()
    album1.uuid = "album1_uuid"
    album1.title = "Test Album 1"
    album1.photos = [photo1]

    db.photos.return_value = [photo1]
    db.albums = [album1]
    db.get_album.return_value = album1
    db.get_photo.return_value = photo1

    return db

def test_library_default(mock_db):
    """Test the library_default resource."""
    with patch("osxphotos.mcp_server.resources.PhotosDB", return_value=mock_db):
        data = resources.library_default()
        assert data["library_path"] == "/tmp/photos"
        assert data["counts"]["photos"] == 1

def test_album_json(mock_db):
    """Test the album_json resource."""
    with patch("osxphotos.mcp_server.resources.PhotosDB", return_value=mock_db):
        data = resources.album_json(uuid="album1_uuid")
        assert data["uuid"] == "album1_uuid"
        assert data["photo_uuids"][0] == "photo1_uuid"

def test_photo_json(mock_db):
    """Test the photo_json resource."""
    with patch("osxphotos.mcp_server.resources.PhotosDB", return_value=mock_db):
        data = resources.photo_json(uuid="photo1_uuid")
        assert data["uuid"] == "photo1_uuid"

def test_photo_thumb(mock_db):
    """Test the photo_thumb resource."""
    with patch("osxphotos.mcp_server.resources.PhotosDB", return_value=mock_db):
        with patch("builtins.open", mock_open(read_data=b"imagedata")):
            with patch("os.path.exists", return_value=True):
                image = resources.photo_thumb(uuid="photo1_uuid")
                assert image.data == b"imagedata"
