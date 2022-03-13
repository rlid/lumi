from datetime import datetime

from app import db


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    type = db.Column(db.String(16))

    text = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(64))
