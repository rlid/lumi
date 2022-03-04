from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    target_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey("nodes.id"), nullable=False)

    message = db.Column(db.String(256), nullable=False)
