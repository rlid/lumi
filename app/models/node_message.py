from datetime import datetime

from app import db


class NodeMessage(db.Model):
    __tablename__ = 'node_messages'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    text = db.Column(db.Text, nullable=False)

    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'), nullable=False)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
