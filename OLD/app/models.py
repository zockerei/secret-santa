from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class Participant(db.Model, UserMixin):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    messages = db.relationship('Message', backref='participant', lazy='dynamic')
    giver_assignments = db.relationship('Assignment', foreign_keys='Assignment.giver_id', backref='giver', lazy='dynamic')
    receiver_assignments = db.relationship('Assignment', foreign_keys='Assignment.receiver_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)

    __table_args__ = (UniqueConstraint('participant_id', 'year', name='uq_participant_year_message'),)


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    giver_id = db.Column(db.Integer, db.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)

    __table_args__ = (UniqueConstraint('giver_id', 'year', name='uq_giver_year_assignment'),)
