from app import db
from app.models import Participant, Message, Assignment
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import exists
from typing import Optional, List, Dict, Any
import logging

queries_logger = logging.getLogger('app.queries')

class DatabaseError(Exception):
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

def add_participant(name: str, password: str, role: str = "participant"):
    try:
        queries_logger.debug(f"Attempting to add participant: {name} with role: {role}")
        new_participant = Participant(name=name, is_admin=(role == 'admin'))
        new_participant.set_password(password)
        db.session.add(new_participant)
        db.session.commit()
        queries_logger.info(f"Participant {name} added successfully.")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to add participant {name}: {e}")
        raise DatabaseError("Failed to add participant", e)

def remove_participant(participant_id: int):
    try:
        queries_logger.debug(f"Attempting to remove participant with ID: {participant_id}")
        participant = Participant.query.get(participant_id)
        if participant:
            db.session.delete(participant)
            db.session.commit()
            queries_logger.info(f"Participant with ID {participant_id} removed successfully.")
        else:
            queries_logger.warning(f"Participant with ID {participant_id} not found.")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to remove participant with ID {participant_id}: {e}")
        raise DatabaseError("Failed to remove participant", e)

def add_or_assign_receiver(giver_id: int, receiver_id: int, year: int, message_id: Optional[int] = None):
    try:
        queries_logger.debug(f"Attempting to assign receiver {receiver_id} to giver {giver_id} for year {year}")
        if db.session.query(exists().where(Assignment.receiver_id == receiver_id).where(Assignment.year == year)).scalar():
            queries_logger.warning(f"Receiver {receiver_id} is already assigned for year {year}")
            raise DatabaseError(f"Receiver {receiver_id} is already assigned for year {year}")
        new_assignment = Assignment(giver_id=giver_id, receiver_id=receiver_id, message_id=message_id, year=year)
        db.session.add(new_assignment)
        db.session.commit()
        queries_logger.info(f"Receiver {receiver_id} assigned to giver {giver_id} for year {year}")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to assign receiver {receiver_id} to giver {giver_id} for year {year}: {e}")
        raise DatabaseError("Failed to create assignment", e)

def remove_receiver(person_id: int, receiver_name: str, year: int):
    try:
        queries_logger.debug(f"Attempting to remove receiver {receiver_name} for participant {person_id} in year {year}")
        receiver = Participant.query.filter_by(name=receiver_name).first()
        if receiver:
            Assignment.query.filter_by(giver_id=person_id, receiver_id=receiver.id, year=year).delete()
            db.session.commit()
            queries_logger.info(f"Receiver {receiver_name} removed for participant {person_id} in year {year}")
        else:
            queries_logger.warning(f"Receiver {receiver_name} not found for participant {person_id} in year {year}")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to remove receiver {receiver_name} for participant {person_id} in year {year}: {e}")
        raise DatabaseError("Failed to remove receiver", e)

def verify_participant(name: str, password: str) -> Optional[Participant]:
    try:
        queries_logger.debug(f"Attempting to verify participant: {name}")
        participant = Participant.query.filter_by(name=name).first()
        if participant and participant.check_password(password):
            queries_logger.info(f"Participant {name} verified successfully.")
            return participant
        queries_logger.warning(f"Verification failed for participant: {name}")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to verify participant {name}: {e}")
        raise DatabaseError("Failed to verify participant", e)

def get_messages_for_participant(participant_id: int, year: int) -> List[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching messages for participant ID {participant_id} in year {year}")
        messages = Message.query.filter_by(participant_id=participant_id, year=year).all()
        queries_logger.info(f"Fetched {len(messages)} messages for participant ID {participant_id} in year {year}")
        return [{'id': msg.id, 'message': msg.message, 'year': msg.year} for msg in messages]
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch messages for participant ID {participant_id} in year {year}: {e}")
        raise DatabaseError("Failed to fetch messages", e)

def get_role(name: str) -> Optional[str]:
    try:
        queries_logger.debug(f"Fetching role for participant: {name}")
        participant = Participant.query.filter_by(name=name).first()
        if participant:
            role = 'admin' if participant.is_admin else 'participant'
            queries_logger.info(f"Role for participant {name}: {role}")
            return role
        queries_logger.warning(f"Participant {name} not found for role fetching")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch role for participant {name}: {e}")
        raise DatabaseError("Failed to fetch role", e)

def get_all_participants() -> List[Dict[str, Any]]:
    try:
        queries_logger.debug("Fetching all non-admin participants")
        participants = Participant.query.filter_by(is_admin=False).all()
        queries_logger.info(f"Fetched {len(participants)} non-admin participants")
        return [{'id': p.id, 'name': p.name} for p in participants]
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch participants: {e}")
        raise DatabaseError("Failed to fetch participants", e)

def get_assignments_for_giver(giver_id: int) -> List[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching assignments for giver ID {giver_id}")
        assignments = db.session.query(Assignment).options(
            joinedload(Assignment.receiver)
        ).filter(Assignment.giver_id == giver_id).all()
        queries_logger.info(f"Fetched {len(assignments)} assignments for giver ID {giver_id}")
        return [{'receiver_id': a.receiver_id, 'receiver_name': a.receiver.name, 'year': a.year} for a in assignments]
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch assignments for giver ID {giver_id}: {e}")
        raise DatabaseError("Failed to fetch assignments", e)

def get_participants_count() -> int:
    try:
        queries_logger.debug("Counting all participants")
        count = Participant.query.count()
        queries_logger.info(f"Total participants count: {count}")
        return count
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to get participants count: {e}")
        raise DatabaseError("Failed to get participants count", e)

def get_current_receiver(giver_id: int, year: int) -> Optional[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching current receiver for giver ID {giver_id} in year {year}")
        assignment = Assignment.query.options(
            joinedload(Assignment.receiver)
        ).filter_by(giver_id=giver_id, year=year).first()
        if assignment:
            queries_logger.info(f"Current receiver for giver ID {giver_id} in year {year}: {assignment.receiver.name}")
            return {'id': assignment.receiver.id, 'name': assignment.receiver.name, 'message_id': assignment.message_id}
        queries_logger.warning(f"No current receiver found for giver ID {giver_id} in year {year}")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch current receiver for giver ID {giver_id} in year {year}: {e}")
        raise DatabaseError("Failed to fetch current receiver", e)

def get_participant_id(name: str) -> Optional[int]:
    try:
        queries_logger.debug(f"Fetching participant ID for name: {name}")
        participant = Participant.query.filter_by(name=name).first()
        if participant:
            queries_logger.info(f"Participant ID for {name}: {participant.id}")
            return participant.id
        queries_logger.warning(f"Participant {name} not found for ID fetching")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch participant ID for {name}: {e}")
        raise DatabaseError("Failed to fetch participant ID", e)

def get_participant_by_id(person_id: int) -> Optional[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching participant by ID: {person_id}")
        participant = Participant.query.get(person_id)
        if participant:
            queries_logger.info(f"Fetched participant with ID {person_id}: {participant.name}")
            return {'id': participant.id, 'name': participant.name, 'admin': participant.is_admin}
        queries_logger.warning(f"Participant with ID {person_id} not found")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch participant with ID {person_id}: {e}")
        raise DatabaseError("Failed to fetch participant", e)

def update_participant(participant_id: int, name: str, password: str):
    try:
        queries_logger.debug(f"Updating participant ID {participant_id} with new name and password")
        participant = Participant.query.get(participant_id)
        if participant:
            participant.name = name
            participant.set_password(password)
            db.session.commit()
            queries_logger.info(f"Participant ID {participant_id} updated successfully")
        else:
            queries_logger.warning(f"Participant ID {participant_id} not found for update")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to update participant ID {participant_id}: {e}")
        raise DatabaseError("Failed to update participant", e)

def admin_exists() -> bool:
    try:
        queries_logger.debug("Checking if any admin exists")
        exists = db.session.query(exists().where(Participant.is_admin == True)).scalar()
        queries_logger.info(f"Admin exists: {exists}")
        return exists
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to check for admin existence: {e}")
        raise DatabaseError("Failed to check for admin", e)

def update_participant_name(participant_id: int, name: str):
    try:
        queries_logger.debug(f"Updating name for participant ID {participant_id}")
        participant = Participant.query.get(participant_id)
        if participant:
            participant.name = name
            db.session.commit()
            queries_logger.info(f"Participant ID {participant_id} name updated to {name}")
        else:
            queries_logger.warning(f"Participant ID {participant_id} not found for name update")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to update name for participant ID {participant_id}: {e}")
        raise DatabaseError("Failed to update participant name", e)

def get_message_by_id(message_id: int, participant_id: int) -> Optional[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching message ID {message_id} for participant ID {participant_id}")
        message = Message.query.filter_by(id=message_id, participant_id=participant_id).first()
        if message:
            queries_logger.info(f"Fetched message ID {message_id} for participant ID {participant_id}")
            return {'id': message.id, 'message': message.message, 'year': message.year}
        queries_logger.warning(f"Message ID {message_id} not found for participant ID {participant_id}")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch message ID {message_id} for participant ID {participant_id}: {e}")
        raise DatabaseError("Failed to fetch message", e)

def update_message(message_id: int, new_message_text: str):
    try:
        queries_logger.debug(f"Updating message ID {message_id}")
        message = Message.query.get(message_id)
        if message:
            message.message = new_message_text
            db.session.commit()
            queries_logger.info(f"Message ID {message_id} updated successfully")
        else:
            queries_logger.warning(f"Message ID {message_id} not found for update")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to update message ID {message_id}: {e}")
        raise DatabaseError("Failed to update message", e)

def delete_message(message_id: int):
    try:
        queries_logger.debug(f"Deleting message ID {message_id}")
        message = Message.query.get(message_id)
        if message:
            db.session.delete(message)
            db.session.commit()
            queries_logger.info(f"Message ID {message_id} deleted successfully")
        else:
            queries_logger.warning(f"Message ID {message_id} not found for deletion")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to delete message ID {message_id}: {e}")
        raise DatabaseError("Failed to delete message", e)

def get_message_for_year(participant_id: int, year: int) -> Optional[Dict[str, Any]]:
    try:
        queries_logger.debug(f"Fetching message for participant ID {participant_id} in year {year}")
        message = Message.query.filter_by(participant_id=participant_id, year=year).first()
        if message:
            queries_logger.info(f"Fetched message for participant ID {participant_id} in year {year}")
            return {'id': message.id, 'message': message.message, 'year': message.year}
        queries_logger.warning(f"No message found for participant ID {participant_id} in year {year}")
        return None
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to fetch message for participant ID {participant_id} in year {year}: {e}")
        raise DatabaseError("Failed to fetch message for year", e)

def is_duplicate_assignment(giver_id: int, year: int) -> bool:
    try:
        queries_logger.debug(f"Checking for duplicate assignment for giver ID {giver_id} in year {year}")
        duplicate_exists = db.session.query(
            db.session.query(Assignment).filter_by(giver_id=giver_id, year=year).exists()
        ).scalar()
        if duplicate_exists:
            queries_logger.info(f"Duplicate assignment found for giver ID {giver_id} in year {year}")
        else:
            queries_logger.info(f"No duplicate assignment found for giver ID {giver_id} in year {year}")
        return duplicate_exists
    except SQLAlchemyError as e:
        queries_logger.error(f"Failed to check for duplicate assignment for giver ID {giver_id} in year {year}: {e}")
        raise DatabaseError("Failed to check for duplicate assignment", e)

def add_message(participant_id: int, message_text: str, year: int):
    try:
        queries_logger.debug(f"Attempting to add message for participant ID {participant_id} for year {year}")
        new_message = Message(participant_id=participant_id, message=message_text, year=year)
        db.session.add(new_message)
        db.session.commit()
        queries_logger.info(f"Message added for participant ID {participant_id} for year {year}")
    except SQLAlchemyError as e:
        db.session.rollback()
        queries_logger.error(f"Failed to add message for participant ID {participant_id} for year {year}: {e}")
        raise DatabaseError("Failed to add message", e)
