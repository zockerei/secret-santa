from flask import Blueprint
import logging

christmas = Blueprint('christmas', __name__, template_folder='templates')

from . import routes
