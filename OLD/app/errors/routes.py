from flask import render_template
from . import errors
from . import errors_logger
from app.queries import DatabaseError


@errors.app_errorhandler(404)
def page_not_found(e):
    errors_logger.error('Page not found: %s', (e))
    return render_template('404.html'), 404


@errors.app_errorhandler(500)
def internal_server_error(e):
    errors_logger.error('Internal server error: %s', (e))
    return render_template('500.html'), 500


@errors.app_errorhandler(DatabaseError)
def handle_database_error(e):
    errors_logger.error('Database error: %s', (e))
    return render_template('500.html'), 500
