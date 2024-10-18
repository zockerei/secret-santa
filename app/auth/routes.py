from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required
from . import auth
from . import auth_logger
from app.queries import verify_participant, get_role

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        auth_logger.info(f"Login attempt for user: {name}")
        participant = verify_participant(name, password)
        if participant:
            login_user(participant)
            role = get_role(name)
            session['user'] = name
            session['role'] = role
            auth_logger.info(f"User {name} logged in with role {role}")
            if role == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            else:
                return redirect(url_for('participant.participant_dashboard'))
        else:
            auth_logger.warning(f"Failed login attempt for user: {name}")
            flash('Invalid name or password.', 'danger')
    return render_template('login.html')

@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    auth_logger.info(f"User {session.get('user')} logged out")
    session.clear()
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
