from flask import render_template, redirect, url_for, flash, request
from . import admin
from . import admin_logger
from app.decorators import login_required
import app.queries as sql_statements
import app.logic as logic


@admin.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    """Display the admin dashboard."""
    participants = sql_statements.get_all_participants()
    return render_template(
        'admin_dashboard.html',
        participants=participants,
    )


@admin.route('/remove_assignment/<int:giver_id>/<int:receiver_id>/<int:year>', methods=['POST'])
@login_required(role='admin')
def remove_assignment(giver_id, receiver_id, year):
    """Remove a past assignment for a specific participant, based on the year."""
    sql_statements.remove_receiver(giver_id, receiver_id, year)
    admin_logger.info(f'Removed assignment for giver ID "{giver_id}" and receiver ID "{receiver_id}" in year {year}.')
    flash(f'Assignment for year {year} removed successfully.', 'success')
    return redirect(url_for('admin.scoreboard'))


@admin.route('/add_participant', methods=['POST'])
@login_required(role='admin')
def add_new_participant():
    """Handle adding a new participant."""
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not password:
        flash('All fields are required to add a participant.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    sql_statements.add_participant(name, password, 'participant')
    admin_logger.info(f'Added new participant "{name}".')
    flash(f'Participant "{name}" added successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin.route('/edit_participant/<int:participant_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_participant(participant_id):
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        if not name:
            flash('Name is required to update a participant.', 'warning')
            return redirect(url_for('admin.edit_participant', participant_id=participant_id))

        if password:
            sql_statements.update_participant(participant_id, name, password)
        else:
            sql_statements.update_participant_name(participant_id, name)
        admin_logger.info(f'Participant ID "{participant_id}" updated to name "{name}".')
        flash(f'Participant "{name}" updated successfully.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        participant = sql_statements.get_participant_by_id(participant_id)
        if participant is None:
            flash('Participant not found.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))
        return render_template('edit_participant.html', participant=participant)


@admin.route('/remove_participant/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def remove_participant(person_id):
    """Remove a participant from the participants list."""
    sql_statements.remove_participant(person_id)
    admin_logger.info(f'Participant ID "{person_id}" removed.')
    flash('Participant removed successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin.route('/add_receiver/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def add_receiver(person_id):
    """Add a past receiver for a specific participant, along with the year."""
    receiver_name = request.form.get('receiver_name', '').strip()
    year_str = request.form.get('year', '').strip()

    if not receiver_name or not year_str:
        flash('Receiver name and year are required.', 'warning')
        return redirect(url_for('admin.scoreboard'))

    try:
        year = int(year_str)
    except ValueError:
        flash('Year must be a valid integer.', 'warning')
        return redirect(url_for('admin.scoreboard'))

    receiver_id = sql_statements.get_participant_id(receiver_name)
    if receiver_id is None:
        flash(f'Receiver "{receiver_name}" not found.', 'warning')
        return redirect(url_for('admin.scoreboard'))

    participant = sql_statements.get_participant_by_id(person_id)
    if participant and participant['name'].lower() == receiver_name.lower():
        flash('A participant cannot be their own past receiver.', 'warning')
        return redirect(url_for('admin.scoreboard'))

    if sql_statements.is_duplicate_assignment(person_id, year):
        flash(f'Error: A receiver for year {year} is already assigned.', 'warning')
        return redirect(url_for('admin.scoreboard'))

    sql_statements.add_or_assign_receiver(person_id, receiver_id, year)
    admin_logger.info(f'Added receiver "{receiver_name}" for participant ID "{person_id}" in year {year}.')
    flash(f'Receiver "{receiver_name}" added for year {year}.', 'success')
    return redirect(url_for('admin.scoreboard'))


@admin.route('/remove_receiver/<int:person_id>/<string:receiver_name>/<int:year>', methods=['POST'])
@login_required(role='admin')
def remove_receiver(person_id, receiver_name, year):
    """Remove a past receiver for a specific participant, based on the year."""
    sql_statements.remove_receiver(person_id, receiver_name, year)
    admin_logger.info(f'Removed receiver "{receiver_name}" for participant ID "{person_id}" in year {year}.')
    flash(f'Receiver "{receiver_name}" for year {year} removed successfully.', 'success')
    return redirect(url_for('admin.scoreboard'))


@admin.route('/start_new_run', methods=['POST'])
@login_required(role='admin')
def start_new_run():
    """Start a new Secret Santa round."""
    year_str = request.form.get('year', '').strip()

    if not year_str:
        flash('Year is required to start a new run.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        year = int(year_str)
    except ValueError:
        flash('Year must be a valid integer.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    participants = sql_statements.get_all_participants() or []

    if not participants:
        flash('No participants available to start a new run.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    for participant in participants:
        person_id = participant['id']
        current_receiver = sql_statements.get_current_receiver(person_id, year)
        if current_receiver:
            flash(f"Participant '{participant['name']}' already has a receiver for the year {year}.", "warning")
            admin_logger.warning(f"Participant '{participant['name']}' already has a receiver for year {year}.")
            return redirect(url_for('admin.admin_dashboard'))

    new_assignments = logic.generate_secret_santa(participants, sql_statements)

    for giver_id, receiver_id in new_assignments:
        message = sql_statements.get_message_for_year(giver_id, year)
        message_id = message['id'] if message else None
        # Use add_or_assign_receiver instead of assign_receiver
        sql_statements.add_or_assign_receiver(giver_id, receiver_id, year, message_id)

    admin_logger.info(f'Secret Santa round started for year {year}.')
    flash('New Secret Santa round started successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin.route('/scoreboard')
@login_required(role='admin')
def scoreboard():
    """Display the scoreboard page."""
    participants = sql_statements.get_all_participants()
    scoreboard = {}
    if participants:
        for participant in participants:
            person_id = participant['id']
            participant_name = participant['name']

            # Get all receivers (including both past receivers and assignments)
            all_receivers = sql_statements.get_assignments_for_giver(person_id)

            # Sort by year in descending order
            all_receivers.sort(key=lambda x: x['year'], reverse=True)

            scoreboard[participant_name] = {
                'participant_id': person_id,
                'all_receivers': all_receivers
            }
    return render_template('scoreboard.html', scoreboard=scoreboard)


@admin.route('/edit_admin', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_admin():
    """Handle editing admin details."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        admin_id = request.form.get('admin_id')

        if not name:
            flash('Name is required.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        if password:
            sql_statements.update_participant(admin_id, name, password)
        else:
            sql_statements.update_participant_name(admin_id, name)
            
        admin_logger.info('Admin details updated.')
        flash('Admin details updated successfully.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        # Get the admin user using the queries module
        admin = sql_statements.get_admin()  # We need to add this function
        return render_template('edit_admin.html', admin=admin)
