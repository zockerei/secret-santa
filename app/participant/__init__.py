from flask import Blueprint
import logging

participant = Blueprint('participant', __name__, template_folder='templates', static_folder='static')

participant_logger = logging.getLogger('app.participant')
