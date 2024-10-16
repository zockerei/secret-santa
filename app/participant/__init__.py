from flask import Blueprint

participant = Blueprint('participant', __name__)

from . import routes
