from flask import render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required
from . import auth
from . import auth_logger
from app.queries import verify_participant, get_participant_by_id

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        if not name or not password:
            flash('Please enter both name and password.', 'warning')
            return redirect(url_for('auth.login'))

        try:
            if verify_participant(name, password):
                user = get_participant_by_id(name)
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for(f'{user.role}_dashboard'))
            else:
                flash('Login failed. Check your name and password.', 'danger')
        except Exception as e:
            auth_logger.error(f'Error during login for user "{name}": {e}')
            flash('An error occurred during login. Please try again later.', 'danger')

    return render_template('login.html')

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@login_manager.user_loader
def load_user(user_id):
    return get_participant_by_id(user_id)
