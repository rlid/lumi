from datetime import datetime
from app import db


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    text = db.Column(db.Text, nullable=False)

    engagement_id = db.Column(db.Integer, db.ForeignKey('engagements.id'), nullable=False)

    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
