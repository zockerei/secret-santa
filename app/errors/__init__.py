from flask import Blueprint
import logging

errors = Blueprint('errors', __name__, template_folder='templates')

errors_logger = logging.getLogger('app.errors')
