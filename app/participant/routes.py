from flask import render_template, redirect, url_for, flash, request, session, jsonify
from . import participant, participant_logger
from app.decorators import login_required
from datetime import datetime
import app.queries as sql_statements

@participant.route('/participant')
@login_required(role='participant')
def participant_dashboard():
    """Display the participant dashboard with past receivers and the current year's receiver."""
    user = session.get('user')
    participant_logger.info(f'User "{user}" accessed the dashboard.')

    # Get participant ID
    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Participant not found. Contact administrator.', 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    # Fetch past receivers and current year receiver
    past_receivers = sql_statements.get_receivers_for_participant(participant_id) or []
    current_year = datetime.now().year
    current_receiver = next((r for r in past_receivers if r['year'] == current_year), None)

    # Fetch the messages written for the next receiver (pending messages)
    pending_messages = sql_statements.get_messages_for_participant(participant_id, current_year)

    # Fetch the message from the current receiver
    current_receiver_message = None
    if current_receiver:
        current_receiver_id = sql_statements.get_participant_id(current_receiver['receiver_name'])
        if current_receiver_id:
            message = sql_statements.get_message_for_year(current_receiver_id, current_year)
            if message:
                current_receiver_message = message['message']

    participant_logger.info(f'Dashboard data prepared for user "{user}".')
    return render_template(
        'participant_dashboard.html',
        past_receivers=past_receivers,
        current_receiver=current_receiver,
        current_year=current_year,
        pending_messages=pending_messages,
        current_receiver_message=current_receiver_message
    )

@participant.route('/add_message', methods=['POST'])
@login_required(role='participant')
def add_message():
    """Handle message submission for a participant."""
    user = session.get('user')
    message_text = request.form.get('message_text')
    current_year = datetime.now().year

    if not message_text:
        flash('Message text cannot be empty.', 'danger')
        participant_logger.warning(f'User "{user}" attempted to add an empty message.')
        return redirect(url_for('participant.participant_dashboard'))

    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Participant not found. Contact administrator.', 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    # Check if a message already exists for this year
    existing_message = sql_statements.get_message_for_year(participant_id, current_year)
    if existing_message:
        flash('You have already written a message for this year. You can edit the existing message instead.', 'warning')
        participant_logger.info(f'User "{user}" attempted to add a duplicate message for the year {current_year}.')
        return redirect(url_for('participant.participant_dashboard'))

    # Insert the message into the database with the current year
    sql_statements.add_message(participant_id, message_text, current_year)
    flash('Message added successfully!', 'success')
    participant_logger.info(f'Message added for user "{user}" for the year {current_year}.')
    return redirect(url_for('participant.participant_dashboard'))

@participant.route('/edit_message/<int:message_id>', methods=['GET', 'POST'])
@login_required(role='participant')
def edit_message(message_id):
    user = session.get('user')
    participant_logger.info(f'User "{user}" accessed edit message page for message ID {message_id}.')

    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Participant not found. Contact administrator.', 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    message = sql_statements.get_message_by_id(message_id, participant_id)
    if message is None:
        flash('Message not found or you do not have permission to edit it.', 'danger')
        participant_logger.warning(f'User "{user}" attempted to edit a non-existent or unauthorized message ID {message_id}.')
        return redirect(url_for('participant.participant_dashboard'))

    if request.method == 'POST':
        new_message_text = request.form.get('message_text')
        if new_message_text:
            sql_statements.update_message(message_id, new_message_text)
            flash('Message updated successfully!', 'success')
            participant_logger.info(f'Message ID {message_id} updated by user "{user}".')
            return redirect(url_for('participant.participant_dashboard'))
        else:
            flash('Message text cannot be empty.', 'danger')
            participant_logger.warning(f'User "{user}" attempted to update message ID {message_id} with empty text.')

    return render_template('edit_message.html', message=message)

@participant.route('/delete_message/<int:message_id>', methods=['POST'])
@login_required(role='participant')
def delete_message(message_id):
    user = session.get('user')
    participant_logger.info(f'User "{user}" attempted to delete message ID {message_id}.')

    participant_id = sql_statements.get_participant_id(user)
    if participant_id is None:
        flash('Participant not found. Contact administrator.', 'danger')
        participant_logger.error(f'Participant "{user}" not found in the database.')
        return redirect(url_for('auth.logout'))

    message = sql_statements.get_message_by_id(message_id, participant_id)
    if message is None:
        flash('Message not found or you do not have permission to delete it.', 'danger')
        participant_logger.warning(f'User "{user}" attempted to delete a non-existent or unauthorized message ID {message_id}.')
        return redirect(url_for('participant.participant_dashboard'))

    sql_statements.delete_message(message_id)
    flash('Message deleted successfully!', 'success')
    participant_logger.info(f'Message ID {message_id} deleted by user "{user}".')
    return redirect(url_for('participant.participant_dashboard'))

@participant.route('/view_message/<int:receiver_id>/<int:year>')
@login_required(role='participant')
def view_message(receiver_id, year):
    user = session.get('user')
    participant_logger.info(f'User "{user}" requested to view message for receiver ID {receiver_id} for the year {year}.')

    message = sql_statements.get_message_for_year(receiver_id, year)
    if message:
        participant_logger.info(f'Message for receiver ID {receiver_id} for the year {year} sent to user "{user}".')
        return jsonify({'message': message['message']})
    else:
        participant_logger.warning(f'No message found for receiver ID {receiver_id} for the year {year} for user "{user}".')
        return jsonify({'message': None})
