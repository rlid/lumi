from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class PaymentIntent(db.Model):
    __tablename__ = "payment_intents"

    id = db.Column(db.Integer, primary_key=True)
    stripe_session_id = db.Column(db.String(128), index=True, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(64), index=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    succeeded = db.Column(db.Boolean, default=False, nullable=False)
