import os
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

# Logging setup
_app_logger = logging.getLogger(__name__)
_app_logger.info('Logging setup complete')

app = Flask(__name__)

_flask_logger = logging.getLogger('flask')

# Use Flask's instance_path to get the correct path to the database file
db_path = os.path.join(app.instance_path, 'secret_santa.db')

# Initialize SQLStatements with the correct path
sql_statements = sql.SqlStatements(db_path)

# Ensure tables are created when the app starts
sql_statements.create_tables()

# Check if an admin user exists; if not, create one
if sql_statements.get_participants_count() == 0:  # No participants exist
    admin_name = "admin"  # You can choose to set this as a constant
    admin_password = "admin123"  # Default password, change this as needed
    sql_statements.add_participant(admin_name, admin_password, role="admin")
    _app_logger.info(f'Admin user created with username: {admin_name}')


@app.route('/')
def index():
    """
    Render the homepage that displays the list of all participants.

    Fetches all participants from the database and renders the index.html template to display them.

    Returns:
        str: The rendered HTML content for the homepage.
    """
    participants = sql_statements.get_all_participants()

    if participants is None:  # Fallback in case no participants exist
        participants = []

    return render_template('index.html', participants=participants)


def login_required(role=None):
    """
    A decorator to ensure that the user is logged in and has the appropriate role.

    Parameters:
        role (Optional[str]): The role required to access the route. If None, any logged-in user can access.

    Returns:
        function: The wrapped function that checks the user's login status and role before proceeding.
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle the login functionality.

    If the request method is POST, it checks the provided credentials (name and password). If the credentials
    are valid, the user is logged in and their role is stored in the session.

    Returns:
        str: If GET, renders the login page. If POST and the credentials are valid, redirects to the homepage.
             Otherwise, shows a login failure message and redisplays the login form.
    """
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        # Verify credentials
        if sql_statements.verify_participant(name, password):
            session['user'] = name
            session['role'] = sql_statements.get_role(name)  # Fetch and store the user's role
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your name and password.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Log the user out by clearing their session data.

    Removes the 'user' and 'role' keys from the session and redirects to the login page.

    Returns:
        redirect: Redirects the user to the login page after logging them out.
    """
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    """
    Display the admin dashboard.

    This route is only accessible to users with the 'admin' role. If the user is not an admin, they will receive
    a 403 unauthorized response.

    Returns:
        str: The rendered content for the admin dashboard or a 403 error if unauthorized.
    """
    return "Admin Dashboard"


@app.route('/admin/manage_participants')
@login_required(role='admin')
def manage_participants():
    """
    Render the 'Manage Participants' page for administrators.

    This route allows an admin to add, edit, or remove participants from the system. The page displays all participants
    for easy management.

    Returns:
        str: The rendered HTML content for managing participants.
    """
    participants = sql_statements.get_all_participants()
    return render_template('manage_participants.html', participants=participants)


@app.route('/edit_participant/<int:id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_participant(id):
    """
    Handle editing a participant's details.

    If the request method is POST, it updates the participant's name and password in the database.
    If the request method is GET, it retrieves the participant's details for pre-filling the form.

    Parameters:
        id (int): The ID of the participant to be edited.

    Returns:
        str: The rendered HTML content for editing the participant.
    """
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        sql_statements.remove_participant(id)  # Remove existing participant
        sql_statements.add_participant(name, password)  # Add updated participant
        flash(f'Participant "{name}" updated successfully.')  # Show success message
        return redirect(url_for('manage_participants'))

    # GET request: Fetch current participant details
    participant = sql_statements.get_person_id_by_name(id)
    return render_template('edit_participant.html', participant=participant)


@app.route('/add_participant', methods=['GET', 'POST'])
@login_required(role='admin')  # Ensure only admin can add participants
def add_participant():
    """
    Handle the 'Add Participant' form.

    Allows users to add a new participant to the database via a form. If the request method is POST,
    the function extracts the participant's name and password from the form and adds it to the database,
    then redirects to the index page.

    Returns:
        str: If GET, renders the 'add_participant.html' form. If POST, redirects to the homepage.
    """
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']  # Get the password from the form
        sql_statements.add_participant(name, password)  # Pass the password to the method
        flash(f'Participant "{name}" added successfully.')  # Show success message
        return redirect(url_for('index'))
    return render_template('add_participant.html')


@app.route('/remove_participant/<int:person_id>', methods=['POST'])
def remove_participant(person_id):
    """
    Remove a participant from the participants list.

    This function deletes a participant from the database by their ID.

    Parameters:
        person_id (int): The ID of the participant to be removed.

    Returns:
        redirect: Redirects to the home page after removing the participant.
    """
    sql_statements.remove_participant(person_id)
    return redirect(url_for('index'))


@app.route('/add_receiver/<int:person_id>', methods=['POST'])
def add_receiver(person_id):
    """
    Add a past receiver for a specific participant.

    This function adds a past receiver to the database for a given participant.

    Parameters:
        person_id (int): The ID of the participant for whom to add a past receiver.

    Returns:
        redirect: Redirects to the scoreboard after adding the receiver.
    """
    receiver_name = request.form['receiver_name']
    sql_statements.add_receiver(person_id, receiver_name)
    return redirect(url_for('scoreboard'))


@app.route('/remove_receiver/<int:person_id>/<string:receiver_name>', methods=['POST'])
def remove_receiver(person_id, receiver_name):
    """
    Remove a past receiver for a specific participant.

    This function removes a specific past receiver from the database for a given participant.

    Parameters:
        person_id (int): The ID of the participant from whom to remove a past receiver.
        receiver_name (str): The name of the receiver to remove.

    Returns:
        redirect: Redirects to the scoreboard after removing the receiver.
    """
    sql_statements.remove_receiver(person_id, receiver_name)
    return redirect(url_for('scoreboard'))


@app.route('/scoreboard')
def scoreboard():
    """
    Display the scoreboard with all past participants and their receivers.

    This function fetches all participants and their past receivers, then renders the scoreboard.
    If there are no participants, an empty scoreboard will be shown.

    Returns:
        str: The rendered HTML content of the scoreboard.
    """
    participants = sql_statements.get_all_participants() or []

    # Create past_receivers only if participants exist
    past_receivers = {}
    if participants:
        past_receivers = {
            name: sql_statements.get_past_receivers_for_participant(person_id) or []
            for person_id, name in participants
        }

    # Create a dictionary mapping names to their IDs for form actions
    participants_ids = {name: person_id for person_id, name in participants} if participants else {}

    return render_template('scoreboard.html', participants=past_receivers, participants_ids=participants_ids)


@app.route('/start_new_run')
def start_new_run():
    """
    Start a new Secret Santa round.

    This function fetches the past Secret Santa assignments from the database, generates new assignments,
    stores the new assignments in the database, and renders the result page to display the new pairings.

    Returns:
        str: The rendered HTML content displaying the new Secret Santa assignments.
    """
    # Fetch past assignments from the database
    past_receiver = logic.fetch_past_receiver(sql_statements)

    # Generate new Secret Santa assignments
    new_receiver = logic.generate_secret_santa(past_receiver)

    # Store the new assignments in the database
    logic.store_new_receiver(new_receiver, sql_statements)

    # Render the result page with the new assignments
    return render_template('result.html', assignments=new_receiver)


if __name__ == '__main__':
    app.run(debug=True)
