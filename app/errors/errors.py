from flask import Blueprint, render_template, flash, redirect, url_for
from app import _app_logger

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def page_not_found(e):
    _app_logger.error(f'Page not found: {e}')
    return render_template('404.html'), 404

@errors.app_errorhandler(500)
def internal_server_error(e):
    _app_logger.error(f'Internal server error: {e}')
    return render_template('500.html'), 500

@errors.app_errorhandler(Exception)
def handle_database_error(e):
    _app_logger.error(f'Database error: {e}')
    flash('A database error occurred. Please try again later.', 'danger')
    return redirect(url_for('auth.login'))
