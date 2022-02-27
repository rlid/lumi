import re

from flask import render_template, redirect, flash, url_for, request, abort
from flask_login import current_user
from sqlalchemy import distinct, not_
from sqlalchemy import func, desc, and_, or_

from app import db
from app.main import main
from app.main.forms import MessageForm
from app.models.user import Message
from app.models.user import Post, Node, Engagement
from app.models.user import User, PostTag, Tag


@main.route("/initdb")
def initdb():
    db.session.remove()
    db.drop_all()
    db.create_all()
    return {"success": True}, 200


@main.route('/user/<user_id>')
def user(user_id):
    u = User.query.filter_by(id=user_id).first_or_404()
    completed_engagements = Engagement.query.filter(
        and_(
            or_(Engagement.asker_id == user_id, Engagement.answerer_id == user_id),
            Engagement.state == Engagement.STATE_COMPLETED
        )
    ).order_by(
        Engagement.last_updated.desc()
    ).all()
    return render_template("user.html", user=u, completed_engagements=completed_engagements)


@main.route('/browse')
def browse():
    tags = re.findall(r'\w+', request.args.get("tags", ""))
    seen = set()
    tag_ids_to_filter = [tag.lower() for tag in tags if not (tag.lower() in seen or seen.add(tag.lower()))]

    if tag_ids_to_filter:
        post_query = Node.query.join(
            Post, Post.id == Node.post_id
        ).join(
            PostTag, PostTag.post_id == Post.id
        ).filter(
            Node.parent_id.is_(None),
            PostTag.tag_id.in_(tag_ids_to_filter),
            Post.type.in_([Post.TYPE_BUY, Post.TYPE_SELL]),
            Post.social_media_mode.is_not(True),
            Post.is_archived.is_not(True)
        ).group_by(
            Node
        ).having(
            func.count(distinct(PostTag.tag_id)) == len(tag_ids_to_filter)
        )
        tags_in_filter = Tag.query.filter(Tag.id.in_(tag_ids_to_filter)).all()
    else:
        post_query = Node.query.join(
            Post, Post.id == Node.post_id
        ).filter(
            Node.parent_id.is_(None),
            Post.type.in_([Post.TYPE_BUY, Post.TYPE_SELL]),
            Post.social_media_mode.is_not(True),
            Post.is_archived.is_not(True)
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
        post_query_sq.c.post_id == PostTag.post_id
    ).filter(
        not_(Tag.id.in_(tag_ids_to_filter))
    ).group_by(
        Tag
    ).order_by(
        desc('freq')
    )

    root_nodes = post_query.order_by(Node.last_updated.desc()).all()
    sticky_posts = []
    if not tag_ids_to_filter:
        sticky_posts = Post.query.filter_by(type=Post.TYPE_ANNOUNCEMENT).order_by(Post.last_updated.desc()).all()
    tags_not_in_filter_with_freq = tags_not_in_filter_query.all()
    return render_template(
        "index.html",
        sticky_posts=sticky_posts,
        root_nodes=root_nodes,
        tags_in_filter=tags_in_filter,
        tags_not_in_filter_with_freq=tags_not_in_filter_with_freq)


@main.route('/post/<post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    if post.is_reported:
        flash("The post is currently not available for viewing.", category='warning')
        return redirect(url_for('main.index'))

    if post.social_media_mode:
        abort(404)

    node = None
    if current_user.is_authenticated:
        node = post.nodes.filter(Node.creator == current_user).first()
    if node is None:
        node = post.nodes.filter(Node.creator == post.creator).first()
    return redirect(url_for('main.view_node', node_id=node.id))


@main.route('/node/<node_id>', methods=['GET', 'POST'])
def view_node(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()

    if node.post.is_reported:
        flash("The post is currently not available for viewing.", category='warning')
        return redirect(url_for('main.index'))

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
            "view_root_node_as_post_creator.html",
            node=node,
            user_node=node,
            nodes=nodes,
            Engagement=Engagement,
            Message=Message)

    if current_user == node.creator or current_user == node.post.creator:
        engagement = node.engagements.filter(Engagement.state == Engagement.STATE_ENGAGED).first()
        engagement_request = node.engagements.filter(Engagement.state == Engagement.STATE_REQUESTED).first()
        # if node.post.reward_cent > current_user.reward_limit_cent:
        #     flash('The reward of the post exceeds your current reward limit. '
        #           'You are not be able to rate engagements on this post until the limit is increased.',
        #           category='warning')
        if (engagement is not None or engagement_request is not None) and \
                ((current_user == node.creator and node.post.reward_cent > node.post.creator.reward_limit_cent) or \
                 (current_user == node.post.creator and node.post.reward_cent > node.creator.reward_limit_cent)):
            flash('The reward of the post exceeds the current reward limit of the other user. This could be because a '
                  'dispute involving the user occurred after this engagement was requested or entered into.',
                  category='warning')
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
        if not node.post.is_archived:
            user_node = current_user.create_node(node)
            current_user.create_message(user_node, form.text.data)
            return redirect(url_for('main.view_node', node_id=user_node.id))
        else:
            flash("Cannot send message because the post is now archived.", category='danger')
    return render_template("view_node_as_other_user.html", node=node, form=form)
