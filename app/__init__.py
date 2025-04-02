from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
import os

db = SQLAlchemy()

def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config is None:
        # Configure SQLite database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    else:
        app.config.update(test_config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Create API
    api = Api(app, version='1.0', title='File Storage API',
             description='A simple Dropbox-like API service',
             doc='/docs')

    # Import and register blueprints/namespaces
    from app.routes import files_ns
    api.add_namespace(files_ns)

    # Ensure database and tables exist
    with app.app_context():
        if not os.path.exists(os.path.join(os.getcwd(), 'instance')):
            os.makedirs(os.path.join(os.getcwd(), 'instance'), exist_ok=True)
        
        # This will create the database file and tables if they don't exist
        db.create_all()

        # Verify the file table exists and has the correct schema
        inspector = db.inspect(db.engine)
        if 'file' not in inspector.get_table_names():
            db.create_all()
        else:
            # Check if file_metadata column exists
            columns = [col['name'] for col in inspector.get_columns('file')]
            if 'file_metadata' not in columns:
                # If table exists but missing file_metadata, drop and recreate
                db.drop_all()
                db.create_all()

    return app 