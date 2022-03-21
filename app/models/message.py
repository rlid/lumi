import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Message(db.Model):
    TYPE_CHAT = 100
    TYPE_REQUEST = 200
    TYPE_ACCEPT = 300
    TYPE_RATE = 400
    TYPE_COMPLETE = 500
    TYPE_CANCEL = 600

    __tablename__ = 'messages'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    type = db.Column(db.Integer, default=TYPE_CHAT, nullable=False)

    text = db.Column(db.Text, nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('nodes.id'), nullable=False)

    engagement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('engagements.id'))

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<m{self.id}>creator={self.creator},node={self.node},engagement={self.engagement}</m{self.id}>'
