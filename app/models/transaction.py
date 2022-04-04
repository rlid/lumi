from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Transaction(db.Model):
    TYPE_PLATFORM_FEE = 100
    TYPE_TOP_UP = 200
    TYPE_ASKER_REWARD_PAYMENT = 300
    TYPE_ASKER_TIP_PAYMENT = 400
    TYPE_REFERRER_REWARD = 500
    TYPE_ANSWERER_REWARD = 600
    TYPE_ANSWERER_TIP = 700

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    type = db.Column(db.Integer, nullable=False)
    amount_cent = db.Column(db.Integer, nullable=False)

    payment_intent_id = db.Column(db.Integer, db.ForeignKey('payment_intents.id'), unique=True)

    engagement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('engagements.id'))

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))

    @property
    def amount(self):
        return 0.01 * self.amount_cent

    @staticmethod
    def add(transaction_type, amount_cent, user=None, payment_intent=None, engagement=None):
        if user:
            user.total_balance_cent += amount_cent
            db.session.add(user)
        db.session.add(
            Transaction(
                type=transaction_type,
                amount_cent=amount_cent,
                user=user,
                payment_intent=payment_intent,
                engagement=engagement
            )
        )
