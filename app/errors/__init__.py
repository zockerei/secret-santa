from flask import Blueprint
import logging

errors = Blueprint('errors', __name__)

# Create a logger for the errors blueprint
errors_logger = logging.getLogger('app.errors')

from . import routes
