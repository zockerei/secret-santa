from flask import render_template, redirect, url_for, flash, request
from . import admin
from . import admin_logger
from app.auth.routes import login_required
import app.logic as logic

@admin.route('/admin_dashboard')
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
        admin_logger.error(f'Error loading admin dashboard: {db_err}')
        return redirect(url_for('login'))

@admin.route('/add_participant', methods=['POST'])
@login_required(role='admin')
def add_new_participant():
    """Handle adding a new participant."""
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()

    if not name or not password:
        flash('All fields are required to add a participant.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        sql_statements.add_participant(name, password, 'participant')
        admin_logger.info(f'Added new participant "{name}".')
        flash(f'Participant "{name}" added successfully.', 'success')
    except Exception as e:
        flash('Failed to add participant. Please try again later.', 'danger')
        admin_logger.error(f'Error adding participant "{name}": {e}')

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

        try:
            if password:
                sql_statements.update_participant(participant_id, name, password)
            else:
                # If no password is provided, update only the name
                sql_statements.update_participant_name(participant_id, name)
            _app_logger.info(f'Participant ID "{participant_id}" updated to name "{name}".')
            flash(f'Participant "{name}" updated successfully.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except DatabaseError as db_err:
            flash('Failed to update participant. Please try again later.', 'danger')
            _app_logger.error(f'Error updating participant ID "{participant_id}": {db_err}')
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
    try:
        sql_statements.remove_participant(person_id)
        _app_logger.info(f'Participant ID "{person_id}" removed.')
        flash('Participant removed successfully.', 'success')
    except DatabaseError as db_err:
        flash('Failed to remove participant. Please try again later.', 'danger')
        _app_logger.error(f'Error removing participant ID "{person_id}": {db_err}')
    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/add_receiver/<int:person_id>', methods=['POST'])
@login_required(role='admin')
def add_receiver(person_id):
    """Add a past receiver for a specific participant, along with the year."""
    receiver_name = request.form.get('receiver_name', '').strip()
    year_str = request.form.get('year', '').strip()

    if not receiver_name or not year_str:
        flash('Receiver name and year are required.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        year = int(year_str)
    except ValueError:
        flash('Year must be a valid integer.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        # Fetch the receiver_id using the receiver_name
        receiver_id = sql_statements.get_participant_id(receiver_name)
        if receiver_id is None:
            flash(f'Receiver "{receiver_name}" not found.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        # Prevent self-assignment
        participant = sql_statements.get_participant_by_id(person_id)
        if participant and participant['name'].lower() == receiver_name.lower():
            flash('A participant cannot be their own past receiver.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        # Check for duplicate receiver for the given year
        if sql_statements.check_duplicate_receiver(person_id, year):
            flash(f'Error: A receiver for year {year} is already assigned.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        # Add the receiver
        sql_statements.add_receiver(person_id, receiver_id, year)
        _app_logger.info(f'Added receiver "{receiver_name}" for participant ID "{person_id}" in year {year}.')
        flash(f'Receiver "{receiver_name}" added for year {year}.', 'success')
    except DatabaseError as db_err:
        flash('Failed to add receiver. Please try again later.', 'danger')
        _app_logger.error(f'Error adding receiver "{receiver_name}" for participant ID "{person_id}": {db_err}')

    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/remove_receiver/<int:person_id>/<string:receiver_name>/<int:year>', methods=['POST'])
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

    return redirect(url_for('admin.admin_dashboard'))

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

    try:
        participants = sql_statements.get_all_participants() or []

        if not participants:
            flash('No participants available to start a new run.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        # Check if any participant already has a receiver for the year
        for participant in participants:
            person_id = participant['id']
            current_receiver = sql_statements.get_current_receiver(person_id, year)
            if current_receiver:
                flash(f"Participant '{participant['name']}' already has a receiver for the year {year}.", "warning")
                _app_logger.warning(f"Participant '{participant['name']}' already has a receiver for year {year}.")
                return redirect(url_for('admin.admin_dashboard'))

        # Generate new assignments using the updated 'logic' module
        new_assignments = logic.generate_secret_santa(participants, sql_statements)
        
        # Store new assignments
        for giver_id, receiver_id in new_assignments:
            # Get the message for the giver, if it exists
            message = sql_statements.get_message_for_year(giver_id, year)
            message_id = message['id'] if message else None
            
            # Assign the receiver and link the message if it exists
            sql_statements.assign_receiver(giver_id, receiver_id, message_id, year)

        _app_logger.info(f'Secret Santa round started for year {year}.')
        flash('New Secret Santa round started successfully.', 'success')
    except DatabaseError as db_err:
        flash('Failed to start a new run. Please try again later.', 'danger')
        _app_logger.error(f'Error starting new Secret Santa run for year {year}: {db_err}')
    except Exception as e:
        flash('An unexpected error occurred. Please try again later.', 'danger')
        _app_logger.error(f'Unexpected error during new run for year {year}: {e}')

    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/create_event', methods=['GET', 'POST'])
@login_required(role='admin')
def create_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        try:
            sql_statements.create_event(event_name, event_date)
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except DatabaseError as e:
            flash(f'Error creating event: {str(e)}', 'error')
    return render_template('admin/create_event.html')

@admin.route('/admin/manage_participants')
@login_required(role='admin')
def manage_participants():
    try:
        participants = sql_statements.get_all_participants()
        return render_template('admin/manage_participants.html', participants=participants)
    except DatabaseError as e:
        flash(f'Error fetching participants: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/admin/delete_participant/<int:participant_id>', methods=['POST'])
@login_required(role='admin')
def delete_participant(participant_id):
    try:
        sql_statements.delete_participant(participant_id)
        flash('Participant deleted successfully!', 'success')
    except DatabaseError as e:
        flash(f'Error deleting participant: {str(e)}', 'error')
    return redirect(url_for('admin.manage_participants'))

@admin.route('/admin/assign_santas', methods=['POST'])
@login_required(role='admin')
def assign_santas():
    try:
        sql_statements.assign_secret_santas()
        flash('Secret Santas assigned successfully!', 'success')
    except DatabaseError as e:
        flash(f'Error assigning Secret Santas: {str(e)}', 'error')
    return redirect(url_for('admin.dashboard'))
