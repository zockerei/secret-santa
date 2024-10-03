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
        if sql_statements.verify_member(name, password):
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


@app.route('/admin/manage_members')
@login_required(role='admin')
def manage_members():
    """
    Render the 'Manage Members' page for administrators.

    This route allows an admin to add, edit, or remove members from the system. The page displays all participants
    for easy management.

    Returns:
        str: The rendered HTML content for managing members.
    """
    participants = sql_statements.get_all_participants()
    return render_template('manage_members.html', participants=participants)


@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    """
    Handle the 'Add Member' form.

    Allows users to add a new member to the database via a form. If the request method is POST,
    the function extracts the member's name from the form and adds it to the database, then redirects to the index page.

    Returns:
        str: If GET, renders the 'add_member.html' form. If POST, redirects to the homepage.
    """
    if request.method == 'POST':
        name = request.form['name']
        sql_statements.add_member(name)
        return redirect(url_for('index'))
    return render_template('add_member.html')


@app.route('/remove_member/<int:person_id>', methods=['POST'])
def remove_member(person_id):
    """
    Remove a member from the participants list.

    This function deletes a member from the database by their ID.

    Parameters:
        person_id (int): The ID of the member to be removed.

    Returns:
        redirect: Redirects to the home page after removing the member.
    """
    sql_statements.remove_member(person_id)
    return redirect(url_for('index'))


@app.route('/add_receiver/<int:person_id>', methods=['POST'])
def add_receiver(person_id):
    """
    Add a past receiver for a specific person.

    This function adds a past receiver to the database for a given person.

    Parameters:
        person_id (int): The ID of the person for whom to add a past receiver.

    Returns:
        redirect: Redirects to the scoreboard after adding the receiver.
    """
    receiver_name = request.form['receiver_name']
    sql_statements.add_receiver(person_id, receiver_name)
    return redirect(url_for('scoreboard'))


@app.route('/remove_receiver/<int:person_id>/<string:receiver_name>', methods=['POST'])
def remove_receiver(person_id, receiver_name):
    """
    Remove a past receiver for a specific person.

    This function removes a specific past receiver from the database for a given person.

    Parameters:
        person_id (int): The ID of the person from whom to remove a past receiver.
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
            name: sql_statements.get_past_receivers_for_person(person_id) or []
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
