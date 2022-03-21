import uuid

from flask import render_template, current_app
from flask_login import current_user
from flask_socketio import emit, join_room, disconnect, Namespace
from sqlalchemy import func

from app import db, socketio
from app.models import Notification, Engagement
from app.models.user import Node, Message, User


class NodeNamespace(Namespace):
    def on_connect(self):
        if not current_user.is_authenticated:
            disconnect()

    def on_join(self, data):
        node_id_str = data['node_id']
        try:
            node_id = uuid.UUID(node_id_str)
        except ValueError as e:
            current_app.logger.exception(e)
            return

        node = Node.query.get(node_id)
        if node is None or (current_user != node.creator and current_user != node.post.creator):
            return

        join_room(node_id_str)
        current_app.logger.info(f'{current_user} has joined Node room {node_id_str}.')

    def on_send_message(self, data):
        node_id_str = data['node_id']
        node = Node.query.get(node_id_str)
        post = node.post
        if post.is_archived and (
                node.current_engagement is None or node.current_engagement.state != Engagement.STATE_ENGAGED
        ):
            emit('render_notification',
                 {'html': 'Cannot send message because the post is now archived.'},
                 to=str(current_user.id),
                 namespace='/user')
            return

        last_timestamp = None
        sub_query = db.session.query(
            func.max(Message.timestamp).label('max_timestamp')
        ).filter(Message.node_id == node.id).subquery()
        last_message = node.messages.join(
            sub_query, Message.timestamp == sub_query.c.max_timestamp
        ).first()
        if last_message is not None:
            last_timestamp = last_message.timestamp

        message = current_user.create_message(node, data['text'])
        new_section = last_message is None or message.engagement_id != last_message.engagement_id
        html = render_template('message.html',
                               message=message,
                               viewer=current_user,
                               last_timestamp=last_timestamp,
                               gap_in_seconds=60,
                               # this is from the last message SENT, not rendered, as that info is not
                               # available here. TODO: try to match the logic for existing messages
                               Message=Message)
        emit('render_message',
             {
                 'id': str(message.id),
                 'html': html,
                 'new_section': new_section
             },
             to=str(node.id))


class UserNamespace(Namespace):
    def on_connect(self):
        if not current_user.is_authenticated:
            disconnect()

    def on_join(self, data):
        user_id_str = data['user_id']

        if str(current_user.id) != user_id_str:
            return

        join_room(user_id_str)
        current_app.logger.info(f'{current_user} has joined User room {user_id_str}.')


socketio.on_namespace(UserNamespace('/user'))
socketio.on_namespace(NodeNamespace('/node'))
