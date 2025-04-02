from datetime import datetime
import uuid
from app import db
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
import json

class JSONType(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

class File(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # File information
    filename = db.Column(db.String(255), nullable=False)  # Display name for the file
    original_filename = db.Column(db.String(255), nullable=False)  # Original uploaded filename
    file_type = db.Column(db.String(100))
    size = db.Column(db.Integer)
    storage_path = db.Column(db.String(500), nullable=False)
    
    # Version control
    version = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.String(36), db.ForeignKey('file.id'), nullable=True)
    is_latest = db.Column(db.Boolean, default=True)
    
    # Additional metadata
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'size': self.size,
            'version': self.version,
            'parent_id': self.parent_id,
            'is_latest': self.is_latest,
            'description': self.description,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        } 