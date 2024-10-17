from flask import Flask, redirect, url_for
from config.config import DevelopmentConfig
from app.models import Participant
from app.extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)

    # Initialize SQLAlchemy with the app
    db.init_app(app)

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

    # Root route redirecting to login
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
