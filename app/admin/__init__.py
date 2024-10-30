from flask import Blueprint
import logging

admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

admin_logger = logging.getLogger('app.admin')
