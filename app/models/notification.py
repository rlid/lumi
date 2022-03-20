from datetime import datetime, timedelta

from flask import render_template, current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app import db

EMAIL_GAP_IN_HOURS = 1
TIME_OUT_IN_MINUTES = 10


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    email_timestamp = db.Column(db.DateTime)

    is_read = db.Column(db.Boolean, default=False, nullable=False)

    target_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey("nodes.id"))

    message = db.Column(db.String(256), nullable=False)

    def read(self):
        self.is_read = True
        db.session.add(self)
        db.session.commit()
        return self.message

    @staticmethod
    def push(target, message, node=None, email=False):
        notification = Notification(
            target=target,
            node=node,
            message=message
        )

        current_time = datetime.utcnow()
        user_inactive = current_time > target.last_seen + timedelta(minutes=TIME_OUT_IN_MINUTES)

        # send email only if:
        # - explicitly want to send:
        email = email
        if user_inactive:  # or user is inactive and
            if not email:
                # there are no unread notifications:
                email = target.notifications.filter_by(is_read=False).first() is None
            if not email:
                # the last notification email was sent more than [x] hours ago
                last_email_timestamp = db.session.query(
                    func.max(Notification.email_timestamp).label('max_email_timestamp')
                ).filter(Notification.target_id == target.id).first().max_email_timestamp
                email = last_email_timestamp is None or \
                    (current_time > last_email_timestamp + timedelta(hours=EMAIL_GAP_IN_HOURS))

        if email:
            body_text = ''
            body_html = None
            try:
                body_text = render_template('email/notification.txt', notification=notification)
                body_html = render_template('email/notification.html', notification=notification)
            except RuntimeError as e:
                current_app.logger.warning(e)
            send_email = current_app.config["EMAIL_SENDER"]
            send_email(
                sender='LumiAsk <notification@lumiask.com>',
                recipient=target.email,
                subject=message,
                body_text=body_text,
                body_html=body_html)
            notification.email_timestamp = current_time

        db.session.add(notification)
        db.session.commit()
        return notification
