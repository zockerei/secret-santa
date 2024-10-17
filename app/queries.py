from app import db
from app.models import Participant, PastReceiver, Message, Assignment
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import exists

class DatabaseError(Exception):
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

def add_participant(name: str, password: str, role: str = "participant"):
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_participant = Participant(name=name, password=hashed, admin=(role == 'admin'))
        db.session.add(new_participant)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to add participant", e)

def remove_participant(participant_id: int):
    try:
        participant = Participant.query.get(participant_id)
        if participant:
            db.session.delete(participant)
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to remove participant", e)

def add_receiver(participant_id: int, receiver_id: int, year: int):
    try:
        if db.session.query(exists().where(PastReceiver.receiver_id == receiver_id).where(PastReceiver.year == year)).scalar():
            raise DatabaseError(f"Receiver {receiver_id} is already assigned for year {year}")
        new_receiver = PastReceiver(participant_id=participant_id, receiver_id=receiver_id, year=year)
        db.session.add(new_receiver)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to add receiver", e)

def add_message(participant_id: int, message_text: str, year: int):
    try:
        new_message = Message(participant_id=participant_id, message=message_text, year=year)
        db.session.add(new_message)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to add message", e)

def assign_receiver(giver_id: int, receiver_id: int, message_id: Optional[int], year: int):
    try:
        new_assignment = Assignment(giver_id=giver_id, receiver_id=receiver_id, message_id=message_id, year=year)
        db.session.add(new_assignment)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to create assignment", e)

def remove_receiver(person_id: int, receiver_name: str, year: int):
    try:
        receiver = Participant.query.filter_by(name=receiver_name).first()
        if receiver:
            PastReceiver.query.filter_by(participant_id=person_id, receiver_id=receiver.id, year=year).delete()
            Assignment.query.filter_by(giver_id=person_id, receiver_id=receiver.id, year=year).delete()
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to remove receiver", e)

def verify_participant(name: str, password: str) -> Optional[Participant]:
    try:
        participant = Participant.query.filter_by(name=name).first()
        if participant and bcrypt.checkpw(password.encode('utf-8'), participant.password.encode('utf-8')):
            return participant
        return None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to verify participant", e)

def is_participant(receiver_name: str, person_id: int) -> bool:
    try:
        return db.session.query(exists().where(Participant.name == receiver_name).where(Participant.id != person_id)).scalar()
    except SQLAlchemyError:
        return False

def check_duplicate_receiver(person_id: int, year: int) -> bool:
    try:
        return db.session.query(exists().where(PastReceiver.participant_id == person_id).where(PastReceiver.year == year)).scalar()
    except SQLAlchemyError:
        return False

def get_messages_for_participant(participant_id: int, year: int) -> List[Dict[str, Any]]:
    try:
        messages = Message.query.filter_by(participant_id=participant_id, year=year).all()
        return [{'id': msg.id, 'message': msg.message, 'year': msg.year} for msg in messages]
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch messages", e)

def get_role(name: str) -> Optional[str]:
    try:
        participant = Participant.query.filter_by(name=name).first()
        if participant:
            return 'admin' if participant.admin else 'participant'
        return None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch role", e)

def get_all_participants() -> List[Dict[str, Any]]:
    try:
        participants = Participant.query.filter_by(admin=False).all()
        return [{'id': p.id, 'name': p.name} for p in participants]
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch participants", e)

def get_receivers_for_participant(person_id: int) -> List[Dict[str, Any]]:
    try:
        receivers = db.session.query(PastReceiver).options(
            joinedload(PastReceiver.receiver)
        ).filter(PastReceiver.participant_id == person_id).all()
        return [{'receiver_id': r.receiver_id, 'receiver_name': r.receiver.name, 'year': r.year} for r in receivers]
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch receivers", e)

def get_participants_count() -> int:
    try:
        return Participant.query.count()
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to get participants count", e)

def get_current_receiver(giver_id: int, year: int) -> Optional[Dict[str, Any]]:
    try:
        assignment = Assignment.query.options(
            joinedload(Assignment.receiver)
        ).filter_by(giver_id=giver_id, year=year).first()
        if assignment:
            return {'id': assignment.receiver.id, 'name': assignment.receiver.name, 'message_id': assignment.message_id}
        return None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch current receiver", e)

def get_participant_id(name: str) -> Optional[int]:
    try:
        participant = Participant.query.filter_by(name=name).first()
        return participant.id if participant else None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch participant ID", e)

def get_participant_by_id(person_id: int) -> Optional[Dict[str, Any]]:
    try:
        participant = Participant.query.get(person_id)
        if participant:
            return {'id': participant.id, 'name': participant.name, 'admin': participant.admin}
        return None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch participant", e)

def update_participant(participant_id: int, name: str, password: str):
    try:
        participant = Participant.query.get(participant_id)
        if participant:
            participant.name = name
            participant.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to update participant", e)

def admin_exists() -> bool:
    try:
        return db.session.query(exists().where(Participant.admin == True)).scalar()
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to check for admin", e)

def update_participant_name(participant_id: int, name: str):
    try:
        participant = Participant.query.get(participant_id)
        if participant:
            participant.name = name
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to update participant name", e)

def get_message_by_id(message_id: int, participant_id: int) -> Optional[Dict[str, Any]]:
    try:
        message = Message.query.filter_by(id=message_id, participant_id=participant_id).first()
        return {'id': message.id, 'message': message.message, 'year': message.year} if message else None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch message", e)

def update_message(message_id: int, new_message_text: str):
    try:
        message = Message.query.get(message_id)
        if message:
            message.message = new_message_text
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to update message", e)

def delete_message(message_id: int):
    try:
        message = Message.query.get(message_id)
        if message:
            db.session.delete(message)
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to delete message", e)

def get_message_for_year(participant_id: int, year: int) -> Optional[Dict[str, Any]]:
    try:
        message = Message.query.filter_by(participant_id=participant_id, year=year).first()
        if message:
            return {'id': message.id, 'message': message.message, 'year': message.year}
        return None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch message for year", e)

def get_wishlist(participant_id: int) -> Optional[str]:
    try:
        participant = Participant.query.get(participant_id)
        return participant.wishlist if participant else None
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to fetch wishlist", e)

def update_wishlist(participant_id: int, wishlist: str):
    try:
        participant = Participant.query.get(participant_id)
        if participant:
            participant.wishlist = wishlist
            db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError("Failed to update wishlist", e)
