import re

from flask import render_template, redirect, flash, url_for, Markup, request
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, disconnect
from simple_websocket import ConnectionClosed
from sqlalchemy import func, desc, distinct, and_, or_, not_, event

from app import db, socketio, sock
from app.main import main
from app.main.forms import PostForm, MarkdownPostForm, MessageForm
from app.models.user import User, Post, PostTag, Tag, Node, Message, Engagement


@main.route('/')
def index():
    return render_template("landing.html")


@main.route('/post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = MarkdownPostForm() if current_user.use_markdown else PostForm()
    if form.validate_on_submit():
        title = form.title.data.strip()
        body = form.body.data.replace('<br>', '')
        body = body.replace('\r\n', '\n')
        body = body.strip()
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        current_user.create_post(is_request=(form.is_request.data == '1'), reward=100 * int(form.reward.data),
                                 title=title, body=body, tag_names=tag_names)
        return redirect(url_for('main.browse'))
    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template("new_post.html", form=form, use_markdown=current_user.use_markdown)


@main.route('/toggle-editor', methods=['GET', 'POST'])
@login_required
def toggle_editor():
    current_user.use_markdown = not current_user.use_markdown
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for('main.new_post'))


@main.route('/browse')
def browse():
    tags = re.findall(r'\w+', request.args.get("tags", ""))
    seen = set()
    tag_ids_to_filter = [tag.lower() for tag in tags if not (tag.lower() in seen or seen.add(tag.lower()))]

    if tag_ids_to_filter:
        post_query = Post.query.join(
            PostTag, PostTag.post_id == Post.id
        ).filter(
            PostTag.tag_id.in_(tag_ids_to_filter),
            Post.type.in_([Post.TYPE_BUY, Post.TYPE_SELL])
        ).group_by(
            Post
        ).having(
            func.count(distinct(PostTag.tag_id)) == len(tag_ids_to_filter)
        )
        tags_in_filter = Tag.query.filter(Tag.id.in_(tag_ids_to_filter)).all()
    else:
        post_query = Post.query.filter(
            Post.type.in_([Post.TYPE_BUY, Post.TYPE_SELL])
        )
        tags_in_filter = []

    post_query_sq = post_query.subquery()
    tags_not_in_filter_query = db.session.query(
        Tag,
        func.count(PostTag.post_id).label('freq')
    ).join(
        PostTag,
        PostTag.tag_id == Tag.id
    ).join(
        post_query_sq,
        post_query_sq.c.id == PostTag.post_id
    ).filter(
        not_(Tag.id.in_(tag_ids_to_filter))
    ).group_by(
        Tag
    ).order_by(
        desc('freq')
    )

    posts = post_query.order_by(Post.timestamp.desc()).all()
    sticky_posts = []
    if not tag_ids_to_filter:
        sticky_posts = Post.query.filter_by(type=Post.TYPE_ANNOUNCEMENT).order_by(Post.timestamp.desc()).all()
    tags_not_in_filter_with_freq = tags_not_in_filter_query.all()
    return render_template(
        "index.html",
        sticky_posts=sticky_posts,
        posts=posts,
        tags_in_filter=tags_in_filter,
        tags_not_in_filter_with_freq=tags_not_in_filter_with_freq)


@main.route('/user/<user_id>')
def user(user_id):
    u = User.query.filter_by(id=user_id).first_or_404()
    completed_engagements = Engagement.query.filter(
        and_(
            or_(Engagement.asker_id == user_id, Engagement.answerer_id == user_id),
            Engagement.state == Engagement.STATE_COMPLETED
        )
    ).order_by(
        Engagement.timestamp.desc()
    ).all()
    return render_template("user.html", user=u, completed_engagements=completed_engagements)


@main.route('/account')
@login_required
def account():
    completed_engagements = Engagement.query.filter(
        and_(
            or_(Engagement.asker_id == current_user.id, Engagement.answerer_id == current_user.id),
            Engagement.state == Engagement.STATE_COMPLETED
        )
    ).order_by(
        Engagement.timestamp.desc()
    ).all()

    uncompleted_engagements = Engagement.query.filter(
        or_(Engagement.sender_id == current_user.id, Engagement.receiver_id == current_user.id),
        or_(
            Engagement.state == Engagement.STATE_ENGAGED,
            and_(Engagement.state == Engagement.STATE_REQUESTED, Post.is_open.is_(True))
        )
    ).join(
        Node, Node.id == Engagement.node_id
    ).join(
        Post, Post.id == Node.post_id
    ).order_by(
        Engagement.timestamp.desc()
    ).all()

    post_ids_seen = set()
    node_ids_seen = set()
    for engagement in uncompleted_engagements:
        if engagement.node.post_id not in post_ids_seen:
            post_ids_seen.add(engagement.node.post_id)
        if engagement.node_id not in node_ids_seen:
            node_ids_seen.add(engagement.node_id)

    other_posts = current_user.posts.filter(
        Post.id.not_in(post_ids_seen)
    ).order_by(
        Post.timestamp.desc()
    ).all()
    other_nodes = current_user.nodes.filter(
        Node.parent_id.is_not(None),
        Node.id.not_in(node_ids_seen)
    ).join(
        Post, Post.id == Node.post_id
    ).order_by(
        Node.timestamp.desc()
    ).all()
    return render_template(
        "account.html",
        user=current_user,
        uncompleted_engagements=uncompleted_engagements,
        other_posts=other_posts,
        other_nodes=other_nodes,
        Post=Post,
        Node=Node,
        Engagement=Engagement)


@main.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    node = None
    if current_user.is_authenticated:
        node = post.nodes.filter(Node.creator == current_user).first()
    if node is None:
        node = post.nodes.filter(Node.creator == post.creator).first()
    return redirect(url_for('main.view_node', node_id=node.id))


@main.route('/post/<int:post_id>/close')
@login_required
def close_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    if current_user != post.creator:
        flash('Only the original poster can close the post for new chats.', category='danger')
    else:
        post.is_open = False
        db.session.add(post)
        db.session.commit()
        # flash('Your post is no longer open for new contributions', category='warning')

    node = post.nodes.filter(Node.creator == current_user).first()
    return redirect(url_for('main.view_node', node_id=node.id))


@main.route('/node/<int:node_id>', methods=['GET', 'POST'])
def view_node(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()

    if current_user.is_authenticated and (current_user != node.creator and current_user != node.post.creator):
        user_node = node.post.nodes.filter(Node.creator == current_user).first()
        if user_node is not None:
            return redirect(url_for('main.view_node', node_id=user_node.id))

    if current_user == node.creator and current_user == node.post.creator:
        # TODO: experiment with not using group_by, process the Cartesian products in Python into a dict of
        #  node:message so the database is queried only once
        nodes = db.session.query(
            Node,
            func.max(Message.timestamp).label('max_timestamp')
        ).join(
            Post, Node.post_id == node.post_id
        ).join(
            Message, Message.node_id == Node.id
        ).group_by(
            Node
        ).order_by(
            desc('max_timestamp')
        ).all()
        return render_template(
            "view_node_as_post_creator.html",
            post=node.post,
            nodes=nodes,
            Engagement=Engagement,
            Message=Message)

    if current_user == node.creator or current_user == node.post.creator:
        engagement = node.engagements.filter(Engagement.state == Engagement.STATE_ENGAGED).first()
        engagement_request = node.engagements.filter(Engagement.state == Engagement.STATE_REQUESTED).first()
        messages_asc = node.messages.order_by(Message.timestamp.asc()).all()
        form = MessageForm()
        return render_template(
            "view_node.html",
            node=node,
            engagement=engagement,
            engagement_request=engagement_request,
            messages_asc=messages_asc,
            form=form,
            Engagement=Engagement,
            Message=Message)

    form = MessageForm()
    if form.validate_on_submit():
        # the Send button is disabled, so current_user is a valid and logged in, but has no nodes
        user_node = current_user.create_node(node)
        current_user.create_message(user_node, form.text.data)
        return redirect(url_for('main.view_node', node_id=user_node.id))

    return render_template("view_node_as_other_user.html", node=node, form=form)


@main.route('/node/<int:node_id>/request-engagement')
@login_required
def request_engagement(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()
    post = node.post

    if not post.is_open:
        flash('Cannot request for engagement because the post is not open to new interactions.', category='danger')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))

    if current_user == post.creator:
        flash('Cannot request for engagement on your own post.', category='danger')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))

    if post.type == Post.TYPE_SELL and current_user.account_balance - current_user.committed_amount < post.reward:
        flash('Insufficient funds, please top up before you proceed.', category='warning')
        return redirect(url_for('main.index'))

    user_node = node
    if current_user != node.creator:
        user_node = post.nodes.filter(Node.creator == current_user).first()
        if user_node is None:
            user_node = current_user.create_node(node)

    engagement = user_node.engagements.filter(Engagement.state < Engagement.STATE_COMPLETED).first()
    if engagement is None:
        engagement = current_user.create_engagement(user_node)
    else:
        flash('You have already requested for engagement, please let the other user know.', category='warning')
    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<int:engagement_id>/cancel')
@login_required
def cancel_engagement(engagement_id):
    engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()

    if not engagement.node.post.is_open:
        flash('Cannot cancel engagement because the post is not open to new interactions.', category='danger')
    elif current_user != engagement.sender:
        flash('Cannot cancel engagement requested by someone else.', category='danger')
    elif engagement.state != Engagement.STATE_REQUESTED:
        flash('Cannot cancel engagement because it has been accepted.', category='warning')
    else:
        current_user.cancel_engagement(engagement)

    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<int:engagement_id>/accept')
@login_required
def accept_engagement(engagement_id):
    engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()
    post = engagement.node.post

    if not post.is_open:
        flash('Cannot accept engagement because the post is not open to new interactions.', category='danger')
    elif engagement.state != Engagement.STATE_REQUESTED:
        flash('The request for engagement can no longer be accepted.', category='danger')
    elif current_user != post.creator:
        flash('Only the original poster can accept the engagement.', category='danger')
    elif post.type == Post.TYPE_BUY and current_user.account_balance - current_user.committed_amount < post.reward:
        flash('Insufficient funds, please top up before you proceed.', category='warning')
        return redirect(url_for('main.index'))
    else:
        current_user.accept_engagement(engagement)
    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<int:engagement_id>/<int:is_success>')
@login_required
def rate_engagement(engagement_id, is_success):
    engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()

    if current_user == engagement.node.creator or current_user == engagement.node.post.creator:
        current_user.rate_engagement(engagement, is_success)
    else:
        flash('Only the original poster can accept the engagement.', category='danger')

    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/how-it-works')
def how_it_works():
    return render_template("landing.html", title="How It Works")


@main.route('/alerts')
@login_required
def alerts():
    return render_template("landing.html", title="Alerts")


@main.route('/engagements')
@login_required
def engagements():
    return render_template("landing.html", title="Active Engagements")


@main.route('/saved')
@login_required
def saved():
    return render_template("landing.html", title="Saved")


@main.route('/guidelines')
def guidelines():
    return render_template("landing.html", title="Community Guidelines")


@main.route("/initdb")
def initdb():
    db.session.remove()
    db.drop_all()
    db.create_all()
    return {"success": True}, 200


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
        # emit('notify_node', {'html': f'{current_user} has joined the chat.'}, to=node_id)
    else:
        disconnect()


@socketio.on('message_sent')
def handle_message_sent(message):
    node = Node.query.get(message['node_id'])
    if (current_user != node.creator and current_user != node.post.creator) or \
            not (node.post.is_open or message['engagement_id'] is not None):
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
             'id': message.id,
             'html': html,
             'new_section': new_section
         },
         to=node.id)


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

@sock.route('/sock/node/<int:node_id>')
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


@main.route('/about')
def about():
    return render_template('about.html')
