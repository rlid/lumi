import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class TemporaryRequest(db.Model):
    __tablename__ = 'temporary_requests'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    details = db.Column(db.String(100), nullable=False)
    reward_cent = db.Column(db.Integer, nullable=False)
