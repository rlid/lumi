from datetime import datetime

from app import db


class Engagement(db.Model):
    STATE_REQUESTED = 2 ** 10
    STATE_ENGAGED = 2 * STATE_REQUESTED
    STATE_COMPLETED = 2 * STATE_ENGAGED

    DEFAULT_REWARD_SHARE = 0.1

    __tablename__ = 'engagements'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'), nullable=False)

    asker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    answerer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    state = db.Column(db.Integer, default=STATE_REQUESTED, nullable=False)

    rating_by_asker = db.Column(db.Integer, default=0, nullable=False)
    rating_by_answerer = db.Column(db.Integer, default=0, nullable=False)

    reward_share = db.Column(db.Float, default=DEFAULT_REWARD_SHARE, nullable=False)

    messages = db.relationship('Message',
                               backref=db.backref('engagement'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    def __str__(self):
        return f'<e{self.id}>state={self.state},sender={self.sender},node={self.node}</e{self.id}>'
