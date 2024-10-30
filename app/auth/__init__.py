from flask import Blueprint
import logging

auth = Blueprint('auth', __name__, template_folder='templates')

auth_logger = logging.getLogger('app.auth')
