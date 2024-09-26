from flask import Flask, render_template, request, redirect, url_for
import main
import sql

app = Flask(__name__)
sql_statements = sql.SqlStatements()


@app.route('/')
def index():
    participants = sql_statements.get_all_participants()
    return render_template('templates/index.html', participants=participants)


@app.route('/add_member', methods=['POST'])
def add_member():
    name = request.form['name']
    sql_statements.add_name(name)
    return redirect(url_for('index'))


@app.route('/start_new_run')
def start_new_run():
    # Fetch past assignments from the database
    past_receiver = main.fetch_past_receiver()

    # Generate new Secret Santa assignments
    new_receiver = main.generate_secret_santa(past_receiver)

    # Store the new assignments in the database
    main.store_new_receiver(new_receiver)

    return render_template('templates/result.html', assignments=new_receiver)


if __name__ == '__main__':
    app.run(debug=True)
