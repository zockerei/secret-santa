from app.extensions import db
from flask_login import UserMixin

class Participant(db.Model, UserMixin):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    wishlist = db.Column(db.String)
    admin = db.Column(db.Boolean, default=False)

    # Relationships
    messages = db.relationship('Message', back_populates='participant', cascade='all, delete-orphan')
    given_assignments = db.relationship('Assignment', foreign_keys='Assignment.giver_id', back_populates='giver', cascade='all, delete-orphan')
    received_assignments = db.relationship('Assignment', foreign_keys='Assignment.receiver_id', back_populates='receiver', cascade='all, delete-orphan')
    past_receivers = db.relationship('PastReceiver', foreign_keys='PastReceiver.participant_id', back_populates='participant', cascade='all, delete-orphan')
    past_received = db.relationship('PastReceiver', foreign_keys='PastReceiver.receiver_id', back_populates='receiver', cascade='all, delete-orphan')

class PastReceiver(db.Model):
    __tablename__ = 'past_receivers'
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), primary_key=True, nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), primary_key=True, nullable=False)
    year = db.Column(db.Integer, primary_key=True, nullable=False)

    # Relationships
    participant = db.relationship('Participant', foreign_keys=[participant_id], back_populates='past_receivers')
    receiver = db.relationship('Participant', foreign_keys=[receiver_id], back_populates='past_received')

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    message = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    # Relationships
    participant = db.relationship('Participant', back_populates='messages')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    giver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    year = db.Column(db.Integer, nullable=False)

    # Relationships
    giver = db.relationship('Participant', foreign_keys=[giver_id], back_populates='given_assignments')
    receiver = db.relationship('Participant', foreign_keys=[receiver_id], back_populates='received_assignments')
    message = db.relationship('Message')
