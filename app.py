import os
import yaml
from flask import Flask, render_template, request, redirect, url_for
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


@app.route('/')
def index():
    """
    Render the homepage that displays the list of all participants.

    Fetches all participants from the database and renders the index.html template to display them.

    Returns:
        str: The rendered HTML content for the homepage.
    """
    participants = sql_statements.get_all_participants()
    return render_template('index.html', participants=participants)


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


@app.route('/scoreboard')
def scoreboard():
    """
    View to display the scoreboard of all participants and their past receivers.

    Fetches all participants and their past receivers from the database and renders the scoreboard.html
    template to display the data.

    Returns:
        str: The rendered HTML content displaying the scoreboard of participants and their past receivers.
    """
    participants = sql_statements.get_all_participants()
    scoreboard_data = {}

    for person_id, name in participants:
        receivers = sql_statements.get_past_receivers_for_person(person_id)
        scoreboard_data[name] = receivers

    return render_template('scoreboard.html', scoreboard=scoreboard_data)


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
