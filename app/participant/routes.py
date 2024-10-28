from flask import render_template, redirect, url_for, flash, request, session
from . import participant, participant_logger
from app.decorators import login_required
from datetime import datetime
import app.queries as sql_statements


@participant.route('/participant_dashboard')
@login_required(role='participant')
def participant_dashboard():
    """Display the participant dashboard with past receivers and the current year's receiver."""
    user = session.get('user')
    participant_logger.info(f'User "{user}" accessed the dashboard.')

    # Get participant ID and data
    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Teilnehmer nicht gefunden.' 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    # Get the full participant data
    participant_data = sql_statements.get_participant_by_id(participant_id)

    # Fetch past receivers and current year receiver
    past_receivers = sql_statements.get_assignments_for_giver(participant_id) or []
    current_year = datetime.now().year
    current_receiver = next((r for r in past_receivers if r['year'] == current_year), None)

    # Fetch the messages written for the next receiver (pending messages)
    pending_messages = sql_statements.get_messages_for_participant(participant_id, current_year)

    # Fetch the message from the current receiver
    current_receiver_message = None
    if current_receiver:
        message = sql_statements.get_message_for_year(current_receiver['receiver_id'], current_year)
        if message:
            current_receiver_message = message['message']

    participant_logger.info(f'Dashboard data prepared for user "{user}".')
    return render_template(
        'participant_dashboard.html',
        participant=participant_data,
        past_receivers=past_receivers,
        current_receiver=current_receiver,
        current_year=current_year,
        pending_messages=pending_messages,
        current_receiver_message=current_receiver_message
    )


@participant.route('/manage_message', methods=['POST'])
@login_required(role='participant')
def manage_message():
    """Handle all message operations (add, edit, delete) for a participant."""
    user = session.get('user')
    message_text = request.form.get('message_text')
    message_id = request.form.get('message_id')
    action = request.form.get('action', 'save')  # 'save' or 'delete'
    current_year = datetime.now().year

    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Teilnehmer nicht gefunden.', 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    if action == 'delete':
        if message_id:
            sql_statements.delete_message(message_id)
            flash('Nachricht erfolgreich gelöscht!', 'success')
            participant_logger.info(f'Message ID {message_id} deleted by user "{user}".')
        else:
            participant_logger.warning(f'User "{user}" attempted to delete message without message_id')
            flash('Keine Nachricht zum Löschen gefunden.', 'danger')
    else:  # save action
        if not message_text:
            participant_logger.warning(f'User "{user}" attempted to save empty message')
            flash('Die Nachricht darf nicht leer sein.', 'danger')
            return redirect(url_for('participant.participant_dashboard'))

        if message_id:  # Update existing message
            sql_statements.update_message(message_id, message_text)
            flash('Nachricht erfolgreich aktualisiert!', 'success')
            participant_logger.info(f'Message ID {message_id} updated by user "{user}".')
        else:  # Add new message
            # Check for existing message this year
            existing_message = sql_statements.get_message_for_year(participant_id, current_year)
            if existing_message:
                participant_logger.warning(f'User "{user}" attempted to add second message for year {current_year}')
                flash('Du hast bereits eine Nachricht für dieses Jahr geschrieben.', 'warning')
                return redirect(url_for('participant.participant_dashboard'))
            
            sql_statements.add_message(participant_id, message_text, current_year)
            flash('Nachricht erfolgreich hinzugefügt!', 'success')
            participant_logger.info(f'New message added for user "{user}" for year {current_year}.')

    return redirect(url_for('participant.participant_dashboard'))


@participant.route('/edit_participant/<int:participant_id>', methods=['GET', 'POST'])
@login_required(role='participant')
def edit_participant(participant_id):
    user = session.get('user')

    # Verify this participant is editing their own data
    user_id = sql_statements.get_participant_id(user)
    if participant_id != user_id:
        participant_logger.warning(f'User "{user}" attempted to edit participant {participant_id} (unauthorized)')
        flash('Du kannst nur deine eigenen Informationen bearbeiten.', 'danger')
        return redirect(url_for('participant.participant_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        if not name:
            participant_logger.warning(f'User "{user}" attempted to update profile with empty name')
            flash('Der Name ist erforderlich, um Ihre Informationen zu aktualisieren.', 'warning')
            return redirect(url_for('participant.participant_dashboard'))

        if password:
            sql_statements.update_participant(participant_id, name, password)
            participant_logger.info(f'User "{user}" updated their name and password')
        else:
            sql_statements.update_participant_name(participant_id, name)
            participant_logger.info(f'User "{user}" updated their name to "{name}"')

        # Update the session with the new name if it changed
        session['user'] = name
        
        flash(f'Profil wurde erfolgreich aktualisiert.', 'success')
        return redirect(url_for('participant.participant_dashboard'))
    
    participant_logger.debug(f'User "{user}" accessed edit profile page')
    return redirect(url_for('participant.participant_dashboard'))
