from flask import Blueprint
import logging

admin = Blueprint('admin', __name__)

# Create a logger for the admin blueprint
admin_logger = logging.getLogger('app.admin')

from . import routes
