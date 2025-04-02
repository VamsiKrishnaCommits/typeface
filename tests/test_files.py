import os
import pytest
import tempfile
import json
import uuid
from app import create_app, db
from app.models import File

@pytest.fixture
def app():
    # Create a temporary file to use as our database
    db_fd, db_path = tempfile.mkstemp()
    # Create a temporary directory for file uploads
    upload_dir = tempfile.mkdtemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': upload_dir
    })

    with app.app_context():
        db.create_all()

    yield app

    # Clean up temporary files
    os.close(db_fd)
    os.unlink(db_path)
    for root, dirs, files in os.walk(upload_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
    os.rmdir(upload_dir)

@pytest.fixture
def client(app):
    return app.test_client()

def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/files')
    assert rv.status_code == 200
    assert rv.json == []

def test_upload_file_with_metadata(client):
    """Test uploading a file with metadata."""
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt'),
        'filename': 'custom_name.txt',
        'description': 'Test file description',
        'tags': 'test,example'
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.json['filename'] == 'custom_name.txt'
    assert response.json['original_filename'] == 'test.txt'
    assert response.json['description'] == 'Test file description'
    assert response.json['tags'] == 'test,example'
    assert response.json['version'] == 1
    assert response.json['is_latest'] == True
    assert response.json['parent_id'] is None
    assert uuid.UUID(response.json['id'])  # Verify UUID format

def test_upload_file_without_metadata(client):
    """Test uploading a file without optional fields."""
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt')
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.json['filename'] == 'test.txt'  # Uses original filename
    assert response.json['original_filename'] == 'test.txt'
    assert response.json['description'] is None
    assert response.json['tags'] is None
    assert response.json['version'] == 1
    assert response.json['is_latest'] == True
    assert response.json['parent_id'] is None
    assert uuid.UUID(response.json['id'])

def test_get_file(client):
    """Test retrieving a file."""
    # First upload a file
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt'),
        'description': 'Test file'
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    file_id = response.json['id']

    # Then retrieve it
    response = client.get(f'/files/{file_id}')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/plain'
    assert response.headers['Content-Disposition'] == 'attachment; filename=test.txt'

def test_get_nonexistent_file(client):
    """Test retrieving a non-existent file."""
    response = client.get(f'/files/{str(uuid.uuid4())}')
    assert response.status_code == 404
    assert 'not found' in response.json['message']

def test_update_file_metadata_only(client):
    """Test updating only file metadata."""
    # First upload a file
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt'),
        'description': 'Initial description'
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    file_id = response.json['id']
    initial_version = response.json['version']

    # Then update metadata only
    update_data = {
        'filename': 'updated_name.txt',
        'description': 'Updated description',
        'tags': 'new,tags'
    }
    response = client.put(f'/files/{file_id}', data=update_data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.json['filename'] == 'updated_name.txt'
    assert response.json['description'] == 'Updated description'
    assert response.json['tags'] == 'new,tags'
    assert response.json['version'] == initial_version  # Version shouldn't change for metadata updates
    assert response.json['is_latest'] == True

def test_update_file_creates_new_version(client):
    """Test that uploading a new file creates a new version."""
    # First upload a file
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt'),
        'description': 'Initial version'
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    file_id = response.json['id']
    initial_version = response.json['version']

    # Then update with new file
    update_data = {
        'file': (tempfile.NamedTemporaryFile(), 'updated.txt'),
        'description': 'Updated version'
    }
    response = client.put(f'/files/{file_id}', data=update_data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.json['version'] == initial_version + 1
    assert response.json['parent_id'] == file_id
    assert response.json['is_latest'] == True
    
    # Check that old version exists but is not latest
    response = client.get('/files')
    assert len(response.json) == 1  # Only latest version in listing
    
    # Get all versions
    response = client.get(f'/files/{file_id}/versions')
    assert response.status_code == 200
    assert len(response.json) == 2
    versions = sorted(response.json, key=lambda x: x['version'])
    assert versions[0]['version'] == 1
    assert versions[0]['is_latest'] == False
    assert versions[1]['version'] == 2
    assert versions[1]['is_latest'] == True

def test_delete_file(client):
    """Test soft deleting a file."""
    # First upload a file
    data = {
        'file': (tempfile.NamedTemporaryFile(), 'test.txt')
    }
    response = client.post('/files', data=data, content_type='multipart/form-data')
    file_id = response.json['id']

    # Then delete it
    response = client.delete(f'/files/{file_id}')
    assert response.status_code == 200
    assert response.json['message'] == 'File deleted successfully'

    # Verify it's not in the listing
    response = client.get('/files')
    assert len(response.json) == 0

    # Verify direct access returns 404
    response = client.get(f'/files/{file_id}')
    assert response.status_code == 404

def test_delete_nonexistent_file(client):
    """Test deleting a non-existent file."""
    response = client.delete(f'/files/{str(uuid.uuid4())}')
    assert response.status_code == 404
    assert 'not found' in response.json['message']

def test_get_versions_nonexistent_file(client):
    """Test getting versions of a non-existent file."""
    response = client.get(f'/files/{str(uuid.uuid4())}/versions')
    assert response.status_code == 404
    assert 'not found' in response.json['message'] 