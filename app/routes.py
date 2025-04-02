import os
from flask import request, send_file, current_app
from flask_restx import Namespace, Resource, fields
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound
from app.models import File
from app import db
from datetime import datetime

files_ns = Namespace('files', description='File operations')

# API Models for documentation
file_model = files_ns.model('File', {
    'id': fields.String(readonly=True, description='The file identifier (UUID)'),
    'filename': fields.String(description='Display name for the file'),
    'original_filename': fields.String(readonly=True, description='Original uploaded filename'),
    'file_type': fields.String(readonly=True, description='The file type'),
    'size': fields.Integer(readonly=True, description='The file size in bytes'),
    'version': fields.Integer(readonly=True, description='File version number'),
    'parent_id': fields.String(readonly=True, description='ID of the previous version'),
    'is_latest': fields.Boolean(readonly=True, description='Whether this is the latest version'),
    'description': fields.String(description='File description', required=False),
    'tags': fields.List(fields.String, description='List of tags', required=False),
    'created_at': fields.DateTime(readonly=True, description='Creation timestamp'),
    'updated_at': fields.DateTime(readonly=True, description='Last update timestamp'),
    'deleted_at': fields.DateTime(readonly=True, description='Deletion timestamp')
})

error_model = files_ns.model('Error', {
    'message': fields.String(required=True, description='Error message'),
    'error_code': fields.String(required=True, description='Error code')
})

@files_ns.route('')
class FileList(Resource):
    @files_ns.marshal_list_with(file_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def get(self):
        """List all files (excluding deleted ones)"""
        try:
            files = File.query.filter_by(deleted_at=None, is_latest=True).all()
            return [file.to_dict() for file in files]
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR')

    @files_ns.expect(files_ns.parser()
        .add_argument('file', location='files', type='FileStorage', required=True, help='File to upload')
        .add_argument('filename', location='form', type=str, required=False, help='Custom filename (optional)')
        .add_argument('description', location='form', type=str, required=False, help='File description (optional)')
        .add_argument('tags', location='form', type=str, required=False, help='Comma-separated tags (optional)'))
    @files_ns.marshal_with(file_model)
    @files_ns.response(400, 'Bad request', error_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def post(self):
        """Upload a new file"""
        try:
            if 'file' not in request.files:
                raise BadRequest('No file provided')
            
            file = request.files['file']
            if file.filename == '':
                raise BadRequest('No selected file')

            # Get original filename and secure it
            original_filename = secure_filename(file.filename)
            
            # Use custom filename if provided, otherwise use original
            display_filename = secure_filename(request.form.get('filename', original_filename))
            
            # Generate unique filename for storage
            base, ext = os.path.splitext(original_filename)
            storage_filename = f"{str(datetime.utcnow().timestamp())}{ext}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], storage_filename)

            # Save file to disk
            try:
                file.save(file_path)
            except Exception as e:
                raise Exception(f"Failed to save file: {str(e)}")
            
            # Create database entry
            file_entry = File(
                filename=display_filename,
                original_filename=original_filename,
                file_type=file.content_type,
                size=os.path.getsize(file_path),
                storage_path=file_path,
                description=request.form.get('description', None),
                tags=request.form.get('tags', None)
            )
            
            db.session.add(file_entry)
            db.session.commit()
            
            return file_entry.to_dict()

        except BadRequest as e:
            files_ns.abort(400, message=str(e), error_code='BAD_REQUEST')
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR')

@files_ns.route('/<string:id>')
@files_ns.param('id', 'The file identifier (UUID)')
class FileResource(Resource):
    @files_ns.response(200, 'Success', file_model)
    @files_ns.response(404, 'File not found', error_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def get(self, id):
        """Get a file by ID"""
        try:
            file = File.query.filter_by(id=id, deleted_at=None).first()
            if not file:
                raise NotFound(f"File with id {id} not found")

            try:
                return send_file(
                    file.storage_path,
                    download_name=file.filename,
                    mimetype=file.file_type
                )
            except Exception as e:
                raise Exception(f"Failed to read file: {str(e)}")

        except NotFound as e:
            files_ns.abort(404, message=str(e), error_code='NOT_FOUND')
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR')

    @files_ns.expect(files_ns.parser()
        .add_argument('file', location='files', type='FileStorage', required=False, help='New file version to upload (optional)')
        .add_argument('filename', location='form', type=str, required=False, help='New display name for the file (optional)')
        .add_argument('description', location='form', type=str, required=False, help='New file description (optional)')
        .add_argument('tags', location='form', type=str, required=False, help='New comma-separated tags (optional)'))
    @files_ns.marshal_with(file_model)
    @files_ns.response(404, 'File not found', error_model)
    @files_ns.response(400, 'Bad request', error_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def put(self, id):
        """Update a file and/or its metadata"""
        try:
            current_file = File.query.filter_by(id=id, deleted_at=None).first()
            if not current_file:
                raise NotFound(f"File with id {id} not found")

            # If a new file is being uploaded, create a new version
            if 'file' in request.files and request.files['file'].filename:
                file = request.files['file']
                
                # Generate new storage path
                base, ext = os.path.splitext(secure_filename(file.filename))
                storage_filename = f"{str(datetime.utcnow().timestamp())}{ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], storage_filename)
                
                try:
                    file.save(file_path)
                except Exception as e:
                    raise Exception(f"Failed to save new file: {str(e)}")

                # Mark current version as not latest
                current_file.is_latest = False
                
                # Create new version
                new_file = File(
                    filename=request.form.get('filename', current_file.filename),
                    original_filename=secure_filename(file.filename),
                    file_type=file.content_type,
                    size=os.path.getsize(file_path),
                    storage_path=file_path,
                    version=current_file.version + 1,
                    parent_id=current_file.id,
                    description=request.form.get('description', current_file.description),
                    tags=request.form.get('tags', current_file.tags)
                )
                
                db.session.add(new_file)
                db.session.commit()
                return new_file.to_dict()
            
            # If no new file, just update metadata
            if 'filename' in request.form:
                current_file.filename = request.form['filename']
            if 'description' in request.form:
                current_file.description = request.form['description']
            if 'tags' in request.form:
                current_file.tags = request.form['tags']
            
            db.session.commit()
            return current_file.to_dict()

        except NotFound as e:
            files_ns.abort(404, message=str(e), error_code='NOT_FOUND')
        except BadRequest as e:
            files_ns.abort(400, message=str(e), error_code='BAD_REQUEST')
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR')

    @files_ns.response(200, 'File deleted successfully')
    @files_ns.response(404, 'File not found', error_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def delete(self, id):
        """Soft delete a file"""
        try:
            file = File.query.filter_by(id=id, deleted_at=None).first()
            if not file:
                raise NotFound(f"File with id {id} not found")
            
            # Soft delete by setting deleted_at timestamp
            file.deleted_at = datetime.utcnow()
            db.session.commit()
            
            return {'message': 'File deleted successfully'}

        except NotFound as e:
            files_ns.abort(404, message=str(e), error_code='NOT_FOUND')
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR')

@files_ns.route('/<string:id>/versions')
@files_ns.param('id', 'The file identifier (UUID)')
class FileVersions(Resource):
    @files_ns.marshal_list_with(file_model)
    @files_ns.response(404, 'File not found', error_model)
    @files_ns.response(500, 'Internal server error', error_model)
    def get(self, id):
        """Get all versions of a file"""
        try:
            # Get the latest version first
            latest = File.query.filter_by(id=id, deleted_at=None).first()
            if not latest:
                raise NotFound(f"File with id {id} not found")

            # Get all versions by following parent_id chain
            versions = [latest]
            current = latest
            while current.parent_id:
                current = File.query.get(current.parent_id)
                if current and not current.deleted_at:
                    versions.append(current)

            return versions

        except NotFound as e:
            files_ns.abort(404, message=str(e), error_code='NOT_FOUND')
        except Exception as e:
            files_ns.abort(500, message=str(e), error_code='INTERNAL_SERVER_ERROR') 