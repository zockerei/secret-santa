from flask import render_template, flash, redirect, url_for
from . import errors
from . import errors_logger

@errors.app_errorhandler(404)
def page_not_found(e):
    errors_logger.error('Page not found: %s', (e))
    return render_template('404.html'), 404

@errors.app_errorhandler(500)
def internal_server_error(e):
    errors_logger.error('Internal server error: %s', (e))
    return render_template('500.html'), 500

@errors.app_errorhandler(Exception)
def handle_database_error(e):
    errors_logger.error('Unhandled exception: %s', (e))
    flash('A database error occurred. Please try again later.', 'danger')
    return redirect(url_for('auth.login'))
