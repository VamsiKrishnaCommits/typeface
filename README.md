A Flask-based RESTful API for file management with versioning support, built using Flask-RESTX.

## Overview

This project is a robust file management system that provides versioned file storage with a RESTful API interface. It's designed to handle file operations with proper versioning control, similar to how version control systems manage documents.

### Tech Stack
- **Backend Framework**: Flask with Flask-RESTX for API development
- **Database**: SQLite with SQLAlchemy ORM
- **API Documentation**: Swagger UI (automatically generated via Flask-RESTX)
- **Containerization**: Docker and Docker Compose
- **Storage**: Local filesystem (with a structured upload directory)

### Key Capabilities
- Upload and manage files with automatic versioning
- Track file metadata (size, type, timestamps)
- Maintain version history with parent-child relationships
- Soft delete functionality for safe file removal
- RESTful API with comprehensive Swagger documentation
- Containerized deployment for easy setup

### Quick Start
1. **Using Docker** (Recommended):
   ```bash
   docker-compose up --build
   ```
   Access at: http://127.0.0.1:8000

2. **Native Installation**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python run.py
   ```
   Access at: http://127.0.0.1:5000

### API Documentation
- Swagger UI is available at `/docs` endpoint
- Interactive documentation with try-it-out functionality
- Complete API specifications and request/response examples

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── uploads/
├── requirements.txt
├── run.py
└── README.md
```

## Features

- File upload and retrieval
- File versioning
- Metadata management
- Soft delete functionality

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
