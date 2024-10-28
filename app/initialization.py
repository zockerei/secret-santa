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
            admin_exists = db.session.query(Participant).filter_by(is_admin=True).first() is not None
            
            if not admin_exists:
                admin_name = os.environ.get('ADMIN_NAME')
                admin_password = os.environ.get('ADMIN_PASSWORD')
                
                # Create admin user
                new_admin = Participant(name=admin_name, is_admin=True)
                new_admin.set_password(admin_password)
                db.session.add(new_admin)
                db.session.commit()
                
                app_logger.info('Admin user created.')
            else:
                app_logger.info('Admin user already exists.')
        except SQLAlchemyError as e:
            db.session.rollback()
            app_logger.error(f'Error checking or creating admin user: {str(e)}')
        except Exception as e:
            app_logger.error(f'Unexpected error during admin initialization: {str(e)}')
