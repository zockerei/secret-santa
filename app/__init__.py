from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import DevelopmentConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Import and register blueprints
from .auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint, url_prefix='/auth')

from .admin import admin as admin_blueprint
app.register_blueprint(admin_blueprint, url_prefix='/admin')

from .participant import participant as participant_blueprint
app.register_blueprint(participant_blueprint, url_prefix='/participant')

# Setup error handlers
from .errors.errors import errors as errors_blueprint
app.register_blueprint(errors_blueprint)
