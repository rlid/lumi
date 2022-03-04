from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    is_read = db.Column(db.Boolean, default=False, nullable=False)

    target_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey("nodes.id"), nullable=False)

    message = db.Column(db.String(256), nullable=False)

    def read(self):
        self.is_read = True
        db.session.add(self)
        db.session.commit()
        return self.message

    @staticmethod
    def push(target, node, message):
        notification = Notification(
            target=target,
            node=node,
            message=message
        )
        db.session.add(notification)
        db.session.commit()
        return notification
