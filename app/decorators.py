from functools import wraps
from flask import session, redirect, url_for, flash
from typing import Optional
import logging

# Get the logger
_app_logger = logging.getLogger(__name__)

def login_required(role: Optional[str] = None):
    """
    Decorator to ensure that the user is logged in and has the appropriate role.

    Parameters:
        role (Optional[str]): The required role to access the route.

    Returns:
        function: The decorated view function.
    """
    def decorator(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if role and session.get('role') != role:
                _app_logger.warning(f'Unauthorized access attempt by user "{session.get("user")}".')
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.login'))
            return fn(*args, **kwargs)
        return decorated_view
    return decorator

