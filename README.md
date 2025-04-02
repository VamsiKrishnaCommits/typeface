# File Management API

A Flask-based RESTful API for file management with versioning support, built using Flask-RESTX.

## Features

- File upload and retrieval
- File versioning
- Metadata management
- Soft delete functionality
- Comprehensive test suite

## Architecture

### Database Schema

The system uses SQLAlchemy with SQLite, with the following key fields in the `File` model:

- `id`: UUID primary key
- `filename`: Display name for the file
- `original_filename`: Name of the originally uploaded file
- `file_type`: MIME type of the file
- `size`: File size in bytes
- `storage_path`: Physical location of the file on disk
- `version`: Version number of the file
- `parent_id`: Reference to previous version (for versioning)
- `is_latest`: Boolean flag indicating if this is the latest version
- `description`: Optional file description
- `tags`: Optional comma-separated tags
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `deleted_at`: Soft deletion timestamp

### API Endpoints

#### GET /files
- Lists all non-deleted, latest versions of files
- Excludes older versions and soft-deleted files
- Returns array of file metadata

#### POST /files
- Uploads a new file
- Optional parameters:
  - `filename`: Custom display name (defaults to original filename)
  - `description`: File description
  - `tags`: Comma-separated tags
- Creates version 1 of the file
- Returns complete file metadata

#### GET /files/{id}
- Downloads a specific file
- Returns file content with appropriate Content-Type
- 404 if file is deleted or not found

#### PUT /files/{id}
- Updates a file and/or its metadata
- Behavior varies based on what's being updated:
  1. Metadata-only update:
     - Updates filename, description, or tags
     - Doesn't create new version
     - Preserves existing version number
  2. File content update:
     - Creates new version
     - Increments version number
     - Sets parent_id to previous version
     - Marks old version as not latest
     - Can optionally update metadata too

#### GET /files/{id}/versions
- Lists all versions of a specific file
- Returns array of file metadata sorted by version
- Includes both latest and previous versions
- Excludes deleted versions

#### DELETE /files/{id}
- Soft deletes a file by setting deleted_at timestamp
- File remains on disk but:
  - Won't appear in listings
  - Can't be downloaded
  - Can't be updated
- Returns success message

### Versioning System

The versioning system works as follows:

1. New uploads start at version 1
2. Metadata updates don't create new versions
3. File content updates:
   - Create new version with incremented number
   - Link versions via parent_id
   - Only latest version appears in main listing
   - All versions accessible via versions endpoint
4. Version chain allows full history tracking

### Soft Delete

The soft delete system:
1. Sets deleted_at timestamp instead of removing records
2. Preserves file on disk
3. Automatically excludes deleted files from:
   - Main listing
   - Downloads
   - Updates
   - Version listings
4. Maintains data integrity while allowing potential recovery

## Testing

The test suite (`tests/test_files.py`) provides comprehensive coverage:

### Test Categories

1. Basic Operations
   - `test_empty_db`: Verifies empty database state
   - `test_upload_file_with_metadata`: Tests full file upload with all fields
   - `test_upload_file_without_metadata`: Tests minimal file upload

2. File Retrieval
   - `test_get_file`: Tests file download and headers
   - `test_get_nonexistent_file`: Tests 404 handling

3. Metadata Management
   - `test_update_file_metadata_only`: Tests metadata updates
   - Verifies version number doesn't change

4. Versioning
   - `test_update_file_creates_new_version`: Tests version creation
   - Verifies version numbers, parent relationships
   - Tests version listing endpoint
   - Confirms only latest version appears in main listing

5. Deletion
   - `test_delete_file`: Tests soft delete functionality
   - `test_delete_nonexistent_file`: Tests deletion error handling

### Test Implementation

- Uses pytest fixtures for database and file system setup
- Creates temporary SQLite database for each test
- Creates temporary upload directory for files
- Cleans up all temporary files after tests
- Verifies both happy path and error conditions
- Tests all API endpoints and major features

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Setup

1. Clone the repository (if using Git):
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```


## Running the Application

1. Start the development server:
```bash
python run.py
```


The application will be available at `http://localhost:5000`

2. Access the Swagger UI:
   - Open your browser and navigate to `http://localhost:5000/docs`
   - You'll see the interactive API documentation

3. Run tests:
```bash
pytest tests/
```

4. Run tests with coverage report:
```bash
pytest --cov=app tests/
```



## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── tests/
│   └── test_files.py
├── uploads/
├── requirements.txt
├── run.py
└── README.md
```

## Storage

Files are stored in the local filesystem under the `uploads` directory. The SQLite database stores file metadata and paths. 