from flask import Blueprint
import logging

participant = Blueprint('participant', __name__, template_folder='templates')

participant_logger = logging.getLogger('app.participant')

from . import routes
