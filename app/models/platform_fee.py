from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class PlatformFee(db.Model):
    __tablename__ = "platform_fees"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    amount_cent = db.Column(db.Integer, nullable=False)

    engagement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('engagements.id'), unique=True)

    @property
    def amount(self):
        return 0.01 * self.amount_cent
