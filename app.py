import os
import secrets
import yaml
from flask import Flask, redirect, url_for
import logging.config
from dotenv import load_dotenv
from app import db
from app.queries import add_participant, admin_exists

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Use Flask's configuration system
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///secret_santa.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Logging Setup
def setup_logging():
    """
    Configure logging for the Flask application using a YAML configuration file.
    """
    logging_config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'logging',
        'logging_config.yaml'
    )
    with open(logging_config_path, 'r') as config_file:
        logging_config = yaml.safe_load(config_file.read())
        logging.config.dictConfig(logging_config)

setup_logging()

# Get loggers
_app_logger = logging.getLogger(__name__)
_app_logger.info('Logging setup complete')

_flask_logger = logging.getLogger('flask')

# Initialize SQLAlchemy
db.init_app(app)

def initialize_admin():
    """Check if an admin user exists; if not, create one."""
    with app.app_context():
        try:
            if not admin_exists():
                admin_name = os.environ.get('ADMIN_NAME', 'santa')
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                add_participant(admin_name, admin_password, 'admin')
                _app_logger.info('Admin user created.')
            else:
                _app_logger.info('Admin user already exists.')
        except Exception as e:
            _app_logger.error(f'Error checking or creating admin user: {e}')

# Call the admin initialization function
initialize_admin()

# Routes
@app.route('/')
def home():
    """Redirect to the login page."""
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)
