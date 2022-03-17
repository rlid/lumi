import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Engagement(db.Model):
    STATE_REQUESTED = 100
    STATE_ENGAGED = 200
    STATE_COMPLETED = 300
    STATE_CANCELLED = 400

    DISPUTE_STATUS_NONE = 100
    DISPUTE_STATUS_ASKER_LOST = 200
    DISPUTE_STATUS_ANSWERER_LOST = 300
    DISPUTE_STATUS_BOTH_LOST = 400

    __tablename__ = 'engagements'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    last_updated = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    tip_cent = db.Column(db.Integer, default=0, nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('nodes.id'), nullable=False)

    asker_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    answerer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    state = db.Column(db.Integer, default=STATE_REQUESTED, nullable=False)
    dispute_status = db.Column(db.Integer, default=DISPUTE_STATUS_NONE, nullable=False)

    rating_by_asker = db.Column(db.Integer, default=0, nullable=False)
    rating_by_answerer = db.Column(db.Integer, default=0, nullable=False)

    messages = db.relationship('Message',
                               backref=db.backref('engagement'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    platform_fee = db.relationship('PlatformFee',
                                   backref=db.backref('engagement'),
                                   uselist=False)

    def ping(self, utcnow):
        self.last_updated = utcnow
        db.session.add(self)
        self.node.ping(utcnow)

    def __str__(self):
        return f'<e{self.id}>state={self.state},sender={self.sender},node={self.node}</e{self.id}>'
