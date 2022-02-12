import re

from flask import render_template, redirect, flash, url_for, Markup, request
from flask_login import login_required, current_user
from sqlalchemy import func, desc, distinct, not_
from flask_socketio import emit, join_room, disconnect

from app import db, socketio
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


@main.route('/user/<int:user_id>')
def user(user_id):
    u = User.query.filter_by(id=user_id).first_or_404()
    return render_template("user.html", user=u)


@main.route('/account')
@login_required
def account():
    return render_template("user.html", user=current_user)


@main.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    # TODO: don't group_by, process the Cartesian products in Python into a dict of node:messages so the database is
    # queried only once
    nodes = db.session.query(
        Node,
        func.max(Message.timestamp).label('max_timestamp')
    ).join(
        Post, Node.post_id == post_id
    ).join(
        Message, Message.node_id == Node.id
    ).group_by(
        Node
    ).order_by(
        desc('max_timestamp')
    ).all()

    return render_template("view_post.html", post=post, nodes=nodes, Engagement=Engagement, Message=Message)


@main.route('/node/<int:node_id>')
def view_node(node_id):
    form = MessageForm()
    node = Node.query.filter_by(id=node_id).first_or_404()
    engagement = node.engagements.filter(Engagement.state != Engagement.STATE_COMPLETED).first()
    messages_asc = node.messages.order_by(Message.timestamp.asc()).all()
    return render_template(
        "view_node.html",
        node=node,
        engagement=engagement,
        messages_asc=messages_asc,
        form=form,
        Engagement=Engagement,
        Message=Message)


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


@socketio.on('message sent')
def handle_message(message):
    node = Node.query.get(message['node_id'])
    if current_user != node.creator and current_user != node.post.creator:
        disconnect()
        return

    last_timestamp = db.session.query(
        func.max(Message.timestamp).label('max_timestamp')
    ).filter(Message.node_id == node.id).first().max_timestamp
    message = current_user.create_message(node, message['text'])
    html = render_template('message.html',
                           message=message,
                           viewer=current_user,
                           last_timestamp=last_timestamp,
                           gap_in_seconds=60,  # this is from the last message SENT, not rendered, as that info is not
                                               # available here. TODO: try to match the logic for existing messages
                           Message=Message)
    emit('message processed', html, to=node.id)


@socketio.on('join')
def on_join(data):
    node_id = data['node_id']
    node = Node.query.get(data['node_id'])
    if current_user == node.creator or current_user == node.post.creator:
        print(f'{current_user} joined room {node_id}')
        join_room(node_id)
    else:
        disconnect()


# @sock.route('/sock/message')
# def echo(ws):
#     while True:
#         data = ws.receive()
#         ws.send(data)
