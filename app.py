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
    participants = sql_statements.get_all_participants()
    return render_template('index.html', participants=participants)


@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        sql_statements.add_name(name)
        return redirect(url_for('index'))
    return render_template('add_member.html')


# Route for admin to start a new round
@app.route('/start_new_run')
def start_new_run():
    # Fetch past assignments from the database
    past_receiver = logic.fetch_past_receiver(sql_statements)

    # Generate new Secret Santa assignments
    new_receiver = logic.generate_secret_santa(past_receiver)

    # Store the new assignments in the database
    logic.store_new_receiver(new_receiver, sql_statements)

    return render_template('result.html', assignments=new_receiver)


if __name__ == '__main__':
    app.run(debug=True)
