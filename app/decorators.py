from functools import wraps
from flask import session, redirect, url_for, flash, request
from typing import Optional
import logging

# Use the specific logger for the decorators
decorators_logger = logging.getLogger('app.decorators')


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
            # Log attempt to access protected route
            endpoint = request.endpoint
            decorators_logger.debug(f'Accessing protected route: {endpoint}')

            if 'user' not in session:
                decorators_logger.warning(
                    f'Unauthenticated access attempt to {endpoint} '
                    f'from IP: {request.remote_addr}'
                )
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            current_user = session.get('user')
            current_role = session.get('role')

            if role and current_role != role:
                decorators_logger.warning(
                    f'Unauthorized access attempt to {endpoint} by user "{current_user}" '
                    f'(has role: {current_role}, required role: {role}) '
                    f'from IP: {request.remote_addr}'
                )
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.login'))

            decorators_logger.info(
                f'User "{current_user}" ({current_role}) successfully accessed {endpoint}'
            )
            return fn(*args, **kwargs)
        return decorated_view
    return decorator
