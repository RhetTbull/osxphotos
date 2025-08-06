import pytest
from unittest.mock import Mock, patch
from osxphotos.mcp_server import tools_readonly, tools_write
from osxphotos.mcp_server.schemas import QueryOptionsLike, PhotoInfoExportOptions

@pytest.fixture
def mock_db():
    """Fixture to create a mock PhotosDB object."""
    db = Mock()
    
    # Mock album_info
    album1 = Mock()
    album1.uuid = "album1_uuid"
    album1.title = "Test Album 1"
    album2 = Mock()
    album2.uuid = "album2_uuid"
    album2.title = "Another Album"
    db.album_info = [album1, album2]

    # Mock photos
    photo1 = Mock()
    photo1.uuid = "photo1_uuid"
    photo1.path = "/tmp/photo1.jpg"
    photo1.asdict.return_value = {"uuid": "photo1_uuid", "title": "Photo 1"}
    photo1.export.return_value = ["/tmp/photo1.jpg"]
    db.photos.return_value = [photo1]
    db.get_photo.return_value = photo1

    return db

def test_list_albums(mock_db):
    """Test the list_albums tool."""
    with patch("osxphotos.mcp_server.tools_readonly.PhotosDB", return_value=mock_db):
        albums = tools_readonly.list_albums()
        assert len(albums) == 2
        assert albums[0]["title"] == "Test Album 1"

def test_search_photos(mock_db):
    """Test the search_photos tool."""
    with patch("osxphotos.mcp_server.tools_readonly.PhotosDB", return_value=mock_db):
        query = QueryOptionsLike(keywords=["test"])
        photo_uuids = tools_readonly.search_photos(q=query)
        assert len(photo_uuids) == 1
        assert photo_uuids[0] == "photo1_uuid"

def test_photo_info(mock_db):
    """Test the photo_info tool."""
    with patch("osxphotos.mcp_server.tools_readonly.PhotosDB", return_value=mock_db):
        info = tools_readonly.photo_info(uuid="photo1_uuid")
        assert info["uuid"] == "photo1_uuid"
        assert info["title"] == "Photo 1"

def test_export_photos(mock_db):
    """Test the export_photos tool."""
    with patch("osxphotos.mcp_server.tools_write.PhotosDB", return_value=mock_db), \
         patch("osxphotos.mcp_server.tools_write.write_enabled", return_value=True):
        
        ctx = Mock()
        options = PhotoInfoExportOptions(dest="/tmp")
        result = tools_write.export_photos(uuids=["photo1_uuid"], options=options, ctx=ctx)

        assert result["exported"] == ["/tmp/photo1.jpg"]
        assert not result["errors"]
        mock_db.get_photo.return_value.export.assert_called_once()

def test_add_keywords():
    """Test the add_keywords tool."""
    with patch("osxphotos.mcp_server.tools_write.photoscript.Photo") as MockPhoto, \
         patch("osxphotos.mcp_server.tools_write.write_enabled", return_value=True):
        
        mock_photo_instance = MockPhoto.return_value
        mock_photo_instance.keywords = ["existing"]
        
        ctx = Mock()
        result = tools_write.add_keywords(uuids=["photo1_uuid"], keywords=["new"], ctx=ctx)

        assert result["success"] == 1
        assert not result["errors"]
        assert set(mock_photo_instance.keywords) == {"existing", "new"}

def test_create_album():
    """Test the create_album tool."""
    with patch("osxphotos.mcp_server.tools_write.photoscript.PhotosLibrary") as MockLibrary, \
         patch("osxphotos.mcp_server.tools_write.write_enabled", return_value=True):
        
        mock_library_instance = MockLibrary.return_value
        mock_album = Mock()
        mock_album.uuid = "album1_uuid"
        mock_album.title = "New Album"
        mock_library_instance.create_album.return_value = mock_album
        
        ctx = Mock()
        result = tools_write.create_album(title="New Album", ctx=ctx)

        assert result["uuid"] == "album1_uuid"
        assert result["title"] == "New Album"

def test_add_to_album():
    """Test the add_to_album tool."""
    with patch("osxphotos.mcp_server.tools_write.photoscript.Album") as MockAlbum, \
         patch("osxphotos.mcp_server.tools_write.photoscript.Photo") as MockPhoto, \
         patch("osxphotos.mcp_server.tools_write.write_enabled", return_value=True):
        
        mock_album_instance = MockAlbum.return_value
        
        ctx = Mock()
        result = tools_write.add_to_album(album_uuid="album1_uuid", uuids=["photo1_uuid"], ctx=ctx)

        assert result["success"]
        mock_album_instance.add.assert_called_once()

def test_write_exif(mock_db):
    """Test the write_exif tool."""
    with patch("osxphotos.mcp_server.tools_write.PhotosDB", return_value=mock_db), \
         patch("osxphotos.mcp_server.tools_write.ExifTool") as MockExifTool, \
         patch("osxphotos.mcp_server.tools_write.write_enabled", return_value=True):
        
        mock_exiftool_instance = MockExifTool.return_value.__enter__.return_value
        
        ctx = Mock()
        result = tools_write.write_exif(uuids=["photo1_uuid"], fields={"EXIF:Make": "Apple"}, ctx=ctx)

        assert result["success"] == 1
        assert not result["errors"]
        mock_exiftool_instance.set_value.assert_called_once_with("EXIF:Make", "Apple")
