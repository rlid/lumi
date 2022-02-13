from datetime import datetime

from app import db


class Message(db.Model):
    message_listeners = []

    TYPE_CHAT = 2 ** 10
    TYPE_REQUEST = 2 * TYPE_CHAT
    TYPE_ACCEPT = 2 * TYPE_REQUEST
    TYPE_RATE = 2 * TYPE_ACCEPT
    TYPE_COMPLETE = 2 * TYPE_RATE

    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    type = db.Column(db.Integer, default=TYPE_CHAT, nullable=False)

    text = db.Column(db.Text, nullable=False)

    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'), nullable=False)

    engagement_id = db.Column(db.Integer, db.ForeignKey('engagements.id'))

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<m{self.id}>creator={self.creator},node={self.node},engagement={self.engagement}</m{self.id}>'
