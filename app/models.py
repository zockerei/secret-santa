from app import db

class Participant(db.Model):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    wishlist = db.Column(db.String)
    admin = db.Column(db.Boolean, default=False)

class PastReceiver(db.Model):
    __tablename__ = 'past_receivers'
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    message = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    giver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    year = db.Column(db.Integer, nullable=False)
