import os
import logging
from app.queries import add_participant, admin_exists

def initialize_admin(app):
    """Check if an admin user exists; if not, create one."""
    app_logger = logging.getLogger('app')
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
