from flask import Blueprint
import logging

participant = Blueprint('participant', __name__)

# Create a logger for the participant blueprint
participant_logger = logging.getLogger('app.participant')

from . import routes
