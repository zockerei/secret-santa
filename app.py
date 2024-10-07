import os
import secrets
from functools import wraps
import yaml
from flask import Flask, session, redirect, url_for, request, render_template, flash
import logic
import logging.config
import sql

# Logging setup
with open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'logging',
            'logging_config.yaml'
        ), 'r') as config_file:
    logging_config = yaml.safe_load(config_file.read())
    logging.config.dictConfig(logging_config)

_app_logger = logging.getLogger(__name__)
_app_logger.info('Logging setup complete')

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

_flask_logger = logging.getLogger('flask')

# Use Flask's instance_path to get the correct path to the database file
db_path = os.path.join(app.instance_path, 'secret_santa.db')

# Initialize SQLStatements with the correct path
sql_statements = sql.SqlStatements(db_path)

# Ensure tables are created when the app starts
sql_statements.create_tables()

# Check if an admin user exists; if not, create one
if sql_statements.get_participants_count() == 0:
    admin_name = "santa"
    admin_password = "admin123"  # Default password, change this as needed
    sql_statements.add_participant(admin_name, admin_password, role="admin")
    _app_logger.info(f'Admin user created with username: {admin_name}')


@app.route('/')
def home():
    """
    Redirect to the login page.
    """
    return redirect(url_for('login'))


@app.route('/login', methods=['GET'])
def login():
    """
    Render the login page.
    """
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('participant_dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def handle_login():
    """
    Handle login functionality.
    """
    name = request.form['name']
    password = request.form['password']

    # Verify credentials
    if sql_statements.verify_participant(name, password):
        session['user'] = name
        session['role'] = sql_statements.get_role(name)  # Fetch and store the user's role
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('participant_dashboard'))
    else:
        flash('Login failed. Check your name and password.')
        return redirect(url_for('login'))


def login_required(role=None):
    """
    A decorator to ensure that the user is logged in and has the appropriate role.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return "Unauthorized", 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


@app.route('/logout', methods=['POST'])
def logout():
    """
    Log the user out by clearing their session data.
    """
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    """
    Display the admin dashboard.
    """
    participants = sql_statements.get_all_participants()
    participants_ids = {participant[1]: participant[0] for participant in participants}  # Map names to IDs
    scoreboard = {
        participant[1]: sql_statements.get_receivers_for_participant(participant[0]) or []
        for participant in participants
    }
    return render_template('admin_dashboard.html', participants=participants, participants_ids=participants_ids, scoreboard=scoreboard)


@app.route('/participant_dashboard')
@login_required(role='participant')
def participant_dashboard():
    """
    Display the participant dashboard.
    """
    user = session['user']
    participant_id = sql_statements.get_participant_id(user)  # Method to fetch ID based on username
    past_receivers = sql_statements.get_receivers_for_participant(participant_id)  # Fetch all past receivers

    return render_template('participant_dashboard.html', past_receivers=past_receivers)


@app.route('/add_participant', methods=['POST'])
@login_required(role='admin')
def add_participant():
    """
    Handle adding a new participant.
    """
    name = request.form['name']
    password = request.form['password']
    try:
        sql_statements.add_participant(name, password)  # Attempt to add the new participant
        flash(f'Participant "{name}" added successfully.')
    except ValueError as e:
        flash(str(e))  # Show the error message to the user
    return redirect(url_for('admin_dashboard'))  # Redirect back to admin dashboard


@app.route('/edit_participant/<int:id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_participant(id):
    """
    Handle editing a participant's details.
    """
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']  # Assuming you allow changing roles
        sql_statements.update_participant(id, name, password, role)
        flash(f'Participant "{name}" updated successfully.')
        return redirect(url_for('admin_dashboard'))
    else:
        participant = sql_statements.get_participant_by_id(id)
        return render_template('edit_participant.html', participant=participant)


@app.route('/remove_participant/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def remove_participant(person_id):
    """
    Remove a participant from the participants list.
    """
    sql_statements.remove_participant(person_id)
    flash('Participant removed successfully.')
    return redirect(url_for('admin_dashboard'))


@app.route('/add_receiver/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def add_receiver(person_id):
    """
    Add a past receiver for a specific participant, along with the year.
    """
    receiver_name = request.form['receiver_name']
    year = request.form['year']  # Capture the year from the form
    sql_statements.add_receiver(person_id, receiver_name, year)  # Pass year to SQL function
    flash(f'Receiver "{receiver_name}" added for year {year}.')
    return redirect(url_for('admin_dashboard'))


@app.route('/remove_receiver/<int:person_id>/<string:receiver_name>/<int:year>', methods=['POST'])
@login_required(role='admin')
def remove_receiver(person_id, receiver_name, year):
    """
    Remove a past receiver for a specific participant, based on the year.
    """
    sql_statements.remove_receiver(person_id, receiver_name, year)  # Pass year to SQL function
    flash(f'Receiver "{receiver_name}" for year {year} removed successfully.')
    return redirect(url_for('admin_dashboard'))


@app.route('/start_new_run', methods=['POST'])
@login_required(role='admin')
def start_new_run():
    """
    Start a new Secret Santa round.
    """
    year = request.form['year']  # Capture the year from the form
    past_receiver = logic.fetch_past_receiver(sql_statements)
    new_receiver = logic.generate_secret_santa(past_receiver)

    # Store the new receivers along with the year
    logic.store_new_receiver(new_receiver, sql_statements, year)  # Pass year to storage function

    return render_template('admin_dashboard.html', assignments=new_receiver)


if __name__ == '__main__':
    app.run(debug=True)
