import os
import logging.config
from dotenv import load_dotenv
from flask_login import LoginManager
from app import create_app, db
from app.queries import add_participant, admin_exists, get_participant_by_id

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = create_app()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# User loader function
@login_manager.user_loader
def load_user(user_id):
    return get_participant_by_id(user_id)

# Get loggers
app_logger = logging.getLogger('app')
app_logger.info('Logging setup complete')
flask_logger = logging.getLogger('flask')

def initialize_admin():
    """Check if an admin user exists; if not, create one."""
    with app.app_context():
        try:
            if not admin_exists():
                admin_name = os.environ.get('ADMIN_NAME', 'santa')
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                add_participant(admin_name, admin_password, 'admin')
                app_logger.info('Admin user created.')
            else:
                app_logger.info('Admin user already exists.')
        except Exception as e:
            app_logger.error(f'Error checking or creating admin user: {e}')

# Call the admin initialization function
initialize_admin()

if __name__ == '__main__':
    app.run(debug=True)
