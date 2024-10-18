import os
import logging
from app.extensions import db
from app.models import Participant
from sqlalchemy.exc import SQLAlchemyError

def initialize_admin(app):
    """Check if an admin user exists; if not, create one."""
    app_logger = logging.getLogger('app')
    with app.app_context():
        try:
            # Check if admin exists
            admin_exists = db.session.query(Participant).filter_by(admin=True).first() is not None
            
            if not admin_exists:
                admin_name = os.environ.get('ADMIN_NAME', 'santa')
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                
                # Create admin user
                from app.queries import add_participant
                add_participant(admin_name, admin_password, 'admin')
                
                app_logger.info('Admin user created.')
            else:
                app_logger.info('Admin user already exists.')
        except SQLAlchemyError as e:
            app_logger.error(f'Error checking or creating admin user: {str(e)}')
        except Exception as e:
            app_logger.error(f'Unexpected error during admin initialization: {str(e)}')
