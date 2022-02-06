from datetime import datetime
from app import db


class EngagementMessage(db.Model):
    __tablename__ = 'engagement_messages'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    text = db.Column(db.Text, nullable=False)

    engagement_id = db.Column(db.Integer, db.ForeignKey('engagements.id'), nullable=False)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
