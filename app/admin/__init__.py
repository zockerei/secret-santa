from flask import Blueprint
import logging

admin = Blueprint('admin', __name__, template_folder='templates')

admin_logger = logging.getLogger('app.admin')

from . import routes
