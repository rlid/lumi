from flask import render_template, url_for
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, disconnect
from simple_websocket import ConnectionClosed
from sqlalchemy import func, and_, event

from app import db, socketio, sock
from app.models.user import Node, Message


@socketio.on('connect')
def connect():
    if not current_user.is_authenticated:
        return False


@socketio.on('join')
def on_join(data):
    node_id = data['node_id']
    node = Node.query.get(node_id)
    if current_user == node.creator or current_user == node.post.creator:
        join_room(node_id)
        print(f'{current_user} has joined the chat.')
        # emit('notify_node', {'html': f'{current_user} has joined the chat.'}, to=node_id)
    else:
        disconnect()


@socketio.on('message_sent')
def handle_message_sent(message):
    node = Node.query.get(message['node_id'])

    if current_user != node.creator and current_user != node.post.creator:
        disconnect()
        return
    if node.post.is_archived and message['engagement_id'] is None:
        emit('notify_node', {'html': 'Cannot send message because the post is now archived.'}, to=message['node_id'])
        disconnect()
        return

    # last_timestamp = db.session.query(
    #     func.max(Message.timestamp).label('max_timestamp')
    # ).filter(Message.node_id == node.id).first().max_timestamp
    # last_message = node.messages.filter(Node.timestamp == last_timestamp).first()

    sub_query = db.session.query(
        func.max(Message.timestamp).label('max_timestamp')
    ).filter(Message.node_id == node.id).subquery()
    last_message = node.messages.join(
        sub_query, Message.timestamp == sub_query.c.max_timestamp
    ).first()

    message = current_user.create_message(node, message['text'])

    new_section = message.engagement_id != last_message.engagement_id
    html = render_template('message.html',
                           message=message,
                           viewer=current_user,
                           last_timestamp=last_message.timestamp,
                           gap_in_seconds=60,  # this is from the last message SENT, not rendered, as that info is not
                           # available here. TODO: try to match the logic for existing messages
                           Message=Message)
    emit('processed_message_sent',
         {
             'id': str(message.id),
             'html': html,
             'new_section': new_section
         },
         to=str(node.id))


@socketio.on('engagement_rated')
def handle_engagement_rated(message):
    emit('notify_node', {
        'html': 'The other user has rated this engagement - please '
                '<a href="{node_url}" onclick="location.reload()">refresh</a> to see the updates.'.format(
            node_url=url_for('main.view_node', node_id=message['node_id'], _anchor='form')
        )},
         to=message['node_id'])


# Disabled for now because they cannot handle account balance checks
# TODO: implement these as toast notification using flask-sock and SQLAlchemy after_insert event
# @socketio.on('engagement_requested')
# def handle_engagement_requested(message):
#     emit('processed_engagement_requested', {
#         'html': 'Your received a request for engagement - please <a href="{node_url}">refresh</a> this page.'.format(
#             node_url=url_for('main.view_node', node_id=message['node_id'])
#         )},
#          to=message['node_id'])

# @socketio.on('engagement_accepted')
# def handle_engagement_accepted(message):
#     emit('processed_engagement_accepted', {
#         'html': 'Your request for engagement is accepted - please <a href="{node_url}">refresh</a> this page.'.format(
#             node_url=url_for('main.view_node', node_id=message['node_id'])
#         )},
#          to=message['node_id'])


@sock.route('/sock/node/<node_id>')
@login_required
def sock_to_node(ws, node_id):
    node = Node.query.get(node_id)
    if current_user == node.creator or current_user == node.post.creator:
        Message.message_listeners.append((current_user.id, ws))
        print(f'{current_user} connected to node {node_id}')
        while True:
            text = ws.receive()
            current_user.create_message(node, text)
    else:
        ws.close()


@event.listens_for(Message, 'after_insert')
def emit_after_insert(mapper, connection, message):
    closed_connections = []
    for user_id, user_sock in Message.message_listeners:
        # TODO: remove closed sockets
        if user_id == message.node.creator_id or user_id == message.node.post.creator_id:
            last_timestamp = db.session.query(
                func.max(Message.timestamp).label('max_timestamp')
            ).filter(
                and_(
                    Message.node_id == message.node_id,
                    Message.timestamp < message.timestamp
                )
            ).first().max_timestamp
            html = render_template('message.html',
                                   message=message,
                                   viewer=current_user,
                                   last_timestamp=last_timestamp,
                                   gap_in_seconds=60,
                                   # this is from the last message SENT, not rendered, as that info is not
                                   # available here. TODO: try to match the logic for existing messages
                                   Message=Message)
            print(f'Pushing message to user {user_id}')
            try:
                user_sock.send(html)
            except ConnectionClosed as e:
                print(f'A Connection for user {user_id} is closed')
                closed_connections.append((user_id, user_sock))

    for c in closed_connections:
        try:
            Message.message_listeners.remove(c)
            print(f'A listener for user {c[0]} is removed')
        except ValueError as e:
            print(e)
