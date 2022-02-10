from datetime import datetime

from app import db


class Message(db.Model):
    TYPE_CHAT = 0
    TYPE_REQUEST = 1
    TYPE_ACCEPT = 2
    TYPE_RATE = 3

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
