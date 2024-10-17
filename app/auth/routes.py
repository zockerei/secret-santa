from flask import render_template, redirect, url_for, flash, request, session
from . import auth
from . import auth_logger
from app.queries import verify_participant, get_role
from app.decorators import login_required

@auth.route('/login', methods=['GET'])
def login():
    """Render the login page."""
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('participant_dashboard'))
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def handle_login():
    """Handle login functionality."""
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not password:
        flash('Please enter both name and password.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        # Verify the participant's credentials
        if verify_participant(name, password):
            # Retrieve the participant's role
            role = get_role(name)
            if role is None:
                flash('User role not found. Contact administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Store user information in session
            session['user'] = name
            session['role'] = role
            
            # Redirect based on role
            return redirect(url_for(f'{role}_dashboard'))
        else:
            flash('Login failed. Check your name and password.', 'danger')
            return redirect(url_for('auth.login'))
    except Exception as e:
        auth_logger.error(f'Error during login for user "{name}": {e}')
        flash('An error occurred during login. Please try again later.', 'danger')
        return redirect(url_for('auth.login'))

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log the user out by clearing their session data."""
    user = session.pop('user', None)
    session.pop('role', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
