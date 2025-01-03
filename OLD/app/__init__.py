from flask import Flask, redirect, url_for
from config import DevelopmentConfig, TestingConfig, ProductionConfig
from app.models import Participant
from app.extensions import db, login_manager, migrate
from config import setup_logging
from app.initialization import initialize_admin
import os
import logging

app_logger = logging.getLogger('app')


def create_app():
    setup_logging(default_path=os.path.join(os.path.dirname(__file__), '..', 'config', 'logging_config.yaml'))

    app = Flask(__name__)
    app_logger.info('Flask app created.')

    # Determine the configuration mode
    config_mode = os.getenv('FLASK_ENV').lower()

    if config_mode == 'development':
        app.config.from_object(DevelopmentConfig)
    elif config_mode == 'testing':
        app.config.from_object(TestingConfig)
    elif config_mode == 'production':
        app.config.from_object(ProductionConfig)
    else:
        raise ValueError(f"Invalid FLASK_ENV value: {config_mode}")

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Initialize Flask-Migrate with the app and db
    migrate.init_app(app, db)

    # Move db.create_all() inside an app context
    with app.app_context():
        db.create_all()

    initialize_admin(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Define the user_loader function
    @login_manager.user_loader
    def load_user(user_id):
        return Participant.query.get(int(user_id))

    # Import and register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .participant import participant as participant_blueprint
    app.register_blueprint(participant_blueprint, url_prefix='/participant')

    from .errors import errors as errors_blueprint
    app.register_blueprint(errors_blueprint, url_prefix='/errors')

    from .christmas import christmas as christmas_blueprint
    app.register_blueprint(christmas_blueprint, url_prefix='/christmas')

    # Root route redirecting to login
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
