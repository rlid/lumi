import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Message(db.Model):
    message_listeners = []

    TYPE_CHAT = 2 ** 10
    TYPE_REQUEST = 2 * TYPE_CHAT
    TYPE_ACCEPT = 2 * TYPE_REQUEST
    TYPE_RATE = 2 * TYPE_ACCEPT
    TYPE_COMPLETE = 2 * TYPE_RATE
    TYPE_CANCEL = 2 * TYPE_COMPLETE

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
