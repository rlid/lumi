from datetime import datetime, timedelta

from flask import render_template, current_app, Markup, url_for
from flask_socketio import emit
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

    target_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey("nodes.id"))

    message = db.Column(db.String(256), nullable=False)

    @staticmethod
    def push(target_user, message, node=None, email=False):
        notification = Notification(
            target_user=target_user,
            node=node,
            message=message
        )

        html = ''
        try:
            html = Markup('<a class="text-decoration-none" href=' + (
                url_for("main.account") if node is None else
                url_for("main.view_node", node_id=node.id)) + f'>{message}</a>')
        except RuntimeError as e:
            current_app.logger.debug(e)
        emit('render_notification',
             {
                 'html': html,
                 'count': target_user.num_unread_notifications
             },
             to=str(target_user.id),
             namespace='/user')

        current_time = datetime.utcnow()
        user_inactive = current_time > target_user.last_seen + timedelta(minutes=TIME_OUT_IN_MINUTES)
        # send email only if:
        # - explicitly want to send:
        email = email
        if user_inactive:  # or user is inactive and
            if not email:
                # there are no unread notifications:
                email = target_user.notifications.filter_by(is_read=False).first() is None
            if not email:
                # the last notification email was sent more than [x] hours ago
                last_email_timestamp = db.session.query(
                    func.max(Notification.email_timestamp).label('max_email_timestamp')
                ).filter(Notification.target_user_id == target_user.id).first().max_email_timestamp
                email = last_email_timestamp is None or \
                        (current_time > last_email_timestamp + timedelta(hours=EMAIL_GAP_IN_HOURS))

        if email:
            body_text = ''
            body_html = None
            try:
                body_text = render_template('email/notification.txt', notification=notification)
                body_html = render_template('email/notification.html', notification=notification)
            except RuntimeError as e:
                current_app.logger.debug(e)
            send_email = current_app.config["EMAIL_SENDER"]
            send_email(
                sender='LumiAsk <notification@lumiask.com>',
                recipient=target_user.email,
                subject=message,
                body_text=body_text,
                body_html=body_html)
            notification.email_timestamp = current_time

        db.session.add(notification)
        return notification
