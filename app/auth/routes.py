from flask import render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required
from . import auth
from . import auth_logger
from app.queries import verify_participant, get_role


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        if not name or not password:
            auth_logger.warning("Login attempt with missing credentials")
            flash('Ungültiger Name oder Passwort.', 'danger')
            return render_template('login.html')

        auth_logger.info(f"Login attempt for user: {name}")
        participant = verify_participant(name, password)
        
        if participant:
            login_user(participant)
            role = get_role(name)
            auth_logger.debug(f"Retrieved role for user {name}: {role}")
            
            session['user'] = name
            session['role'] = role
            
            auth_logger.info(f"User {name} logged in successfully with role {role}")
            
            if role == 'admin':
                auth_logger.debug(f'Redirecting admin user {name} to admin dashboard')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                auth_logger.debug(f'Redirecting participant {name} to participant dashboard')
                return redirect(url_for('participant.participant_dashboard'))
        else:
            auth_logger.warning(f"Failed login attempt for user: {name} (invalid credentials)")
            flash('Ungültiger Name oder Passwort.', 'danger')
            
    auth_logger.debug("Displaying login page")
    return render_template('login.html')


@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    user = session.get('user')
    role = session.get('role')
    
    if user:
        auth_logger.info(f"User {user} ({role}) logged out")
    else:
        auth_logger.warning("Logout called with no user in session")
    
    session.clear()
    logout_user()
    
    flash('Sie wurden abgemeldet.', 'success')
    auth_logger.debug("Redirecting to login page after logout")
    return redirect(url_for('auth.login'))
