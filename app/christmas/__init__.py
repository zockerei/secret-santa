from flask import Blueprint

christmas = Blueprint('christmas', __name__, template_folder='templates', static_folder='static')
