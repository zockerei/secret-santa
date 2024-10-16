from datetime import datetime
import os
import secrets
from functools import wraps
import yaml
from flask import Flask, session, redirect, url_for, request, render_template, flash
import logging.config
from typing import Optional
import logic
import sql
from sql import DatabaseError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Use Flask's configuration system
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    DATABASE=os.path.join(app.instance_path, 'secret_santa.db')
)

# Logging Setup
def setup_logging():
    """
    Configure logging for the Flask application using a YAML configuration file.
    """
    logging_config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'logging',
        'logging_config.yaml'
    )
    with open(logging_config_path, 'r') as config_file:
        logging_config = yaml.safe_load(config_file.read())
        logging.config.dictConfig(logging_config)


setup_logging()

# Get loggers
_app_logger = logging.getLogger(__name__)
_app_logger.info('Logging setup complete')

_flask_logger = logging.getLogger('flask')

# Database Setup
db_path = os.path.join(app.instance_path, 'secret_santa.db')

# Ensure the instance path exists
os.makedirs(app.instance_path, exist_ok=True)

# Initialize SQLStatements
sql_statements = sql.SqlStatements(db_path)

try:
    # Ensure tables are created when the app starts
    sql_statements.create_tables()
    _app_logger.info('Database tables ensured.')
except DatabaseError as database_error:
    _app_logger.error(f'Error ensuring database tables: {database_error}')

# Check if an admin user exists; if not, create one
try:
    if not sql_statements.admin_exists():
        admin_name = os.environ.get('ADMIN_NAME', 'santa')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        sql_statements.add_participant(admin_name, admin_password, 'admin')
        _app_logger.info('Admin user created.')
    else:
        _app_logger.info('Admin user already exists.')
except DatabaseError as database_error:
    _app_logger.error(f'Error checking or creating admin user: {database_error}')



# Helper Decorator for Role-Based Access Control
def login_required(role: Optional[str] = None):  # Changed role type to str
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
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                _app_logger.warning(f'Unauthorized access attempt by user "{session.get("user")}".')
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('login'))
            return fn(*args, **kwargs)

        return decorated_view

    return decorator


# Routes

@app.route('/')
def home():
    """Redirect to the login page."""
    return redirect(url_for('login'))


@app.route('/login', methods=['GET'])
def login():
    """Render the login page."""
    if 'user' in session:
        if session.get('admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('participant_dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def handle_login():
    """Handle login functionality."""
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not password:
        flash('Please enter both name and password.', 'warning')
        return redirect(url_for('login'))

    try:
        # Verify the participant's credentials
        if sql_statements.verify_participant(name, password):
            # Retrieve the participant's role
            role = sql_statements.get_role(name)
            if role is None:
                flash('User role not found. Contact administrator.', 'danger')
                _app_logger.error(f'User "{name}" has no role assigned.')
                return redirect(url_for('login'))
            
            # Store user information in session
            session['user'] = name
            session['role'] = role
            _app_logger.info(f'User "{name}" logged in as "{role}".')
            
            # Redirect based on role
            return redirect(url_for(f'{role}_dashboard'))
        else:
            flash('Login failed. Check your name and password.', 'danger')
            return redirect(url_for('login'))
    except DatabaseError as db_err:
        flash('An error occurred during login. Please try again later.', 'danger')
        _app_logger.error(f'Login error for user "{name}": {db_err}')
        return redirect(url_for('login'))


@app.route('/logout', methods=['POST'])
@login_required()
def logout():
    """Log the user out by clearing their session data."""
    user = session.pop('user', None)
    _app_logger.info(f'User "{user}" logged out.')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    """Display the admin dashboard."""
    try:
        participants = sql_statements.get_all_participants()
        scoreboard = {}
        if participants:
            for participant in participants:
                person_id = participant['id']
                participant_name = participant['name']
                receivers = sql_statements.get_receivers_for_participant(person_id)
                scoreboard[participant_name] = receivers if receivers else []
        return render_template(
            'admin_dashboard.html',
            participants=participants,
            scoreboard=scoreboard
        )
    except DatabaseError as db_err:
        flash('Failed to load admin dashboard. Please try again later.', 'danger')
        _app_logger.error(f'Error loading admin dashboard: {db_err}')
        return redirect(url_for('login'))


@app.route('/participant_dashboard')
@login_required(role='participant')
def participant_dashboard():
    """Display the participant dashboard with past receivers and the current year's receiver."""
    user = session.get('user')
    try:
        # Get participant ID
        participant_id = sql_statements.get_participant_id(user)
        if participant_id is None:
            flash('Participant not found. Contact administrator.', 'danger')
            _app_logger.error(f'Participant "{user}" not found in the database.')
            return redirect(url_for('logout'))

        # Fetch past receivers and current year receiver
        past_receivers = sql_statements.get_receivers_for_participant(participant_id) or []
        current_year = datetime.now().year
        current_receiver = next((r for r in past_receivers if r['year'] == current_year), None)

        # Fetch the messages written for the next receiver (pending messages)
        pending_messages = sql_statements.get_messages_for_participant(participant_id)

        return render_template(
            'participant_dashboard.html',
            past_receivers=past_receivers,
            current_receiver=current_receiver,
            current_year=current_year,
            pending_messages=pending_messages
        )
    except DatabaseError as db_err:
        flash('Failed to load participant dashboard. Please try again later.', 'danger')
        _app_logger.error(f'Error loading participant dashboard for user "{user}": {db_err}')
        return redirect(url_for('logout'))



@app.route('/add_message', methods=['POST'])
@login_required(role='participant')
def add_message():
    """Handle message submission for a participant."""
    user = session.get('user')
    message_text = request.form.get('message_text')

    if not message_text:
        flash('Message text cannot be empty.', 'danger')
        return redirect(url_for('participant_dashboard'))

    try:
        participant_id = sql_statements.get_participant_id(user)
        if participant_id is None:
            flash('Participant not found. Contact administrator.', 'danger')
            return redirect(url_for('logout'))

        # Insert the message into the database with receiver_id as NULL for now
        sql_statements.add_message(participant_id, message_text)
        flash('Message added successfully!', 'success')
        return redirect(url_for('participant_dashboard'))

    except DatabaseError as db_err:
        flash('Failed to add message. Please try again later.', 'danger')
        _app_logger.error(f'Error adding message for user "{user}": {db_err}')
        return redirect(url_for('participant_dashboard'))


@app.route('/add_participant', methods=['POST'])
@login_required(role='admin')
def add_new_participant():
    """Handle adding a new participant."""
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not password:
        flash('All fields are required to add a participant.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        sql_statements.add_participant(name, password)
        _app_logger.info(f'Added new participant "{name}".')
        flash(f'Participant "{name}" added successfully.', 'success')
    except ValueError as verr:
        flash(str(verr), 'warning')
        _app_logger.warning(f'Attempted to add duplicate participant "{name}": {verr}')
    except DatabaseError as db_err:
        flash('Failed to add participant. Please try again later.', 'danger')
        _app_logger.error(f'Error adding participant "{name}": {db_err}')

    return redirect(url_for('admin_dashboard'))


# Centralize error handling
@app.errorhandler(DatabaseError)
def handle_database_error(e):
    _app_logger.error(f'Database error: {e}')
    flash('A database error occurred. Please try again later.', 'danger')
    return redirect(url_for('login'))


# Helper function to fetch participant details
def get_participant_details(participant_id):
    try:
        return sql_statements.get_participant_by_id(participant_id)
    except DatabaseError as db_err:
        _app_logger.error(f'Error fetching participant ID "{participant_id}": {db_err}')
        return None


# Use helper function in routes
@app.route('/edit_participant/<int:participant_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_participant(participant_id):
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        if not name:
            flash('Name is required to update a participant.', 'warning')
            return redirect(url_for('edit_participant', participant_id=participant_id))

        try:
            if password:
                sql_statements.update_participant(participant_id, name, password)
            else:
                # If no password is provided, update only the name
                sql_statements.update_participant_name(participant_id, name)
            _app_logger.info(f'Participant ID "{participant_id}" updated to name "{name}".')
            flash(f'Participant "{name}" updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except DatabaseError as db_err:
            flash('Failed to update participant. Please try again later.', 'danger')
            _app_logger.error(f'Error updating participant ID "{participant_id}": {db_err}')
            return redirect(url_for('admin_dashboard'))
    else:
        participant = sql_statements.get_participant_by_id(participant_id)
        if participant is None:
            flash('Participant not found.', 'warning')
            return redirect(url_for('admin_dashboard'))
        return render_template('edit_participant.html', participant=participant)


@app.route('/remove_participant/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def remove_participant(person_id):
    """Remove a participant from the participants list."""
    try:
        sql_statements.remove_participant(person_id)
        _app_logger.info(f'Participant ID "{person_id}" removed.')
        flash('Participant removed successfully.', 'success')
    except DatabaseError as db_err:
        flash('Failed to remove participant. Please try again later.', 'danger')
        _app_logger.error(f'Error removing participant ID "{person_id}": {db_err}')
    return redirect(url_for('admin_dashboard'))


@app.route('/add_receiver/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def add_receiver(person_id):
    """Add a past receiver for a specific participant, along with the year."""
    receiver_name = request.form.get('receiver_name', '').strip()
    year_str = request.form.get('year', '').strip()

    if not receiver_name or not year_str:
        flash('Receiver name and year are required.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        year = int(year_str)
    except ValueError:
        flash('Year must be a valid integer.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        # Fetch the receiver_id using the receiver_name
        receiver_id = sql_statements.get_participant_id(receiver_name)
        if receiver_id is None:
            flash(f'Receiver "{receiver_name}" not found.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Prevent self-assignment
        participant = sql_statements.get_participant_by_id(person_id)
        if participant and participant['name'].lower() == receiver_name.lower():
            flash('A participant cannot be their own past receiver.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Check for duplicate receiver for the given year
        if sql_statements.check_duplicate_receiver(person_id, year):
            flash(f'Error: A receiver for year {year} is already assigned.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Add the receiver
        sql_statements.add_receiver(person_id, receiver_id, year)
        _app_logger.info(f'Added receiver "{receiver_name}" for participant ID "{person_id}" in year {year}.')
        flash(f'Receiver "{receiver_name}" added for year {year}.', 'success')
    except DatabaseError as db_err:
        flash('Failed to add receiver. Please try again later.', 'danger')
        _app_logger.error(f'Error adding receiver "{receiver_name}" for participant ID "{person_id}": {db_err}')

    return redirect(url_for('admin_dashboard'))


@app.route('/remove_receiver/<int:person_id>/<string:receiver_name>/<int:year>', methods=['POST'])
@login_required(role='admin')
def remove_receiver(person_id, receiver_name, year):
    """Remove a past receiver for a specific participant, based on the year."""
    try:
        sql_statements.remove_receiver(person_id, receiver_name=receiver_name, year=year)
        _app_logger.info(f'Removed receiver "{receiver_name}" for participant ID "{person_id}" in year {year}.')
        flash(f'Receiver "{receiver_name}" for year {year} removed successfully.', 'success')
    except DatabaseError as db_err:
        flash('Failed to remove receiver. Please try again later.', 'danger')
        _app_logger.error(f'Error removing receiver "{receiver_name}" for participant ID "{person_id}": {db_err}')

    return redirect(url_for('admin_dashboard'))


@app.route('/start_new_run', methods=['POST'])
@login_required(role='admin')
def start_new_run():
    """Start a new Secret Santa round."""
    year_str = request.form.get('year', '').strip()

    if not year_str:
        flash('Year is required to start a new run.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        year = int(year_str)
    except ValueError:
        flash('Year must be a valid integer.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        participants = sql_statements.get_all_participants() or []
        non_admin_participants = [p for p in participants if p['role'] != 'admin']  # Use 'admin' string directly

        if not non_admin_participants:
            flash('No participants available to start a new run.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Check if any participant already has a receiver for the year
        for participant in non_admin_participants:
            person_id = participant['id']
            if sql_statements.check_duplicate_receiver(person_id, year):
                flash(f"Participant '{participant['name']}' already has a receiver for the year {year}.", "warning")
                _app_logger.warning(f"Participant '{participant['name']}' already has a receiver for year {year}.")
                return redirect(url_for('admin_dashboard'))

        # Fetch past receivers and generate new assignments using the 'logic' module
        past_receiver = logic.fetch_past_receiver(sql_statements)
        new_receiver = logic.generate_secret_santa(past_receiver)
        logic.store_new_receiver(new_receiver, sql_statements, year)

        _app_logger.info(f'Secret Santa round started for year {year}.')
        flash('New Secret Santa round started successfully.', 'success')
    except DatabaseError as db_err:
        flash('Failed to start a new run. Please try again later.', 'danger')
        _app_logger.error(f'Error starting new Secret Santa run for year {year}: {db_err}')
    except Exception as e:
        flash('An unexpected error occurred. Please try again later.', 'danger')
        _app_logger.error(f'Unexpected error during new run for year {year}: {e}')

    return redirect(url_for('admin_dashboard'))


# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    """Render a custom 404 error page."""
    _app_logger.error(f'Internal server error: {e}')
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Render a custom 500 error page."""
    _app_logger.error(f'Internal server error: {e}')
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
