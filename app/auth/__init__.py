from flask import Blueprint
import logging

auth = Blueprint('auth', __name__)

# Create a logger for the auth blueprint
auth_logger = logging.getLogger('app.auth')

from . import routes
