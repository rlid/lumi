import re

from flask import render_template, redirect, flash, url_for, request, session
from flask_login import current_user
from sqlalchemy import distinct, not_
from sqlalchemy import func, desc, and_, or_

from app import db
from app.auth.forms import LogInForm, SignUpForm
from app.main import main
from app.main.forms import MessageForm, ReportForm, FeedbackForm, RatingForm, ConfirmForm
from app.models.user import Message
from app.models.user import Post, Node, Engagement
from app.models.user import User, PostTag, Tag


@main.route("/initdb")
def initdb():
    db.session.remove()
    db.drop_all()
    db.create_all()
    return {"success": True}, 200


@main.route('/user/<uuid:user_id>')
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
    nodes = u.nodes.join(
        Post, Post.id == Node.post_id
    ).filter(
        Node.parent_id.is_(None),
        Post.is_private.is_not(True),
        Post.is_archived.is_not(True)
    ).order_by(
        Node.timestamp.desc()
    ).all()
    return render_template(
        'user.html',
        user=u,
        nodes=nodes,
        completed_engagements=completed_engagements,
        title='User Profile',
        feedback_form=FeedbackForm(prefix='feedback'),
        Post=Post,
        Engagement=Engagement
    )


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
            Post.is_private.is_not(True),
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
            Post.is_private.is_not(True),
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
    return render_template(
        "index.html",
        root_nodes=root_nodes,
        tags_in_filter=tags_in_filter,
        tags_not_in_filter_with_freq=tags_not_in_filter_query.all(),
        login_form=LogInForm(prefix='login'),
        feedback_form=FeedbackForm(prefix='feedback')
    )


@main.route('/node/<uuid:node_id>', methods=['GET', 'POST'])
def view_node(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()
    post = node.post

    if post.is_reported:
        flash("The post is currently not available for viewing.", category='warning')
        return redirect(url_for('main.index'))

    message_form = MessageForm(prefix='message')
    if message_form.validate_on_submit():
        # the Send button is disabled if current user is not authenticated, so either:
        #  - the current_user is a valid and logged in, but has no nodes, or
        #  - the current user is a valid and logged in, but created a node on another device, then send the message
        #    before refreshing the page on this device
        if not node.post.is_archived:
            user_node = current_user.create_node(node)
            current_user.create_message(user_node, message_form.text.data)
        else:
            flash("Cannot send message because the post is now archived.", category='danger')
        return redirect(url_for('main.view_node', node_id=user_node.id))

    if current_user.is_authenticated and (current_user != node.creator and current_user != post.creator):
        user_node = post.nodes.filter(Node.creator == current_user).first()
        if user_node is not None:
            # flash('You have already created your own unique referral link for this post. ' +
            #       'You are redirected to your own contribution page instead.', category='info')
            return redirect(url_for('main.view_node', node_id=user_node.id))

    feedback_form = FeedbackForm(prefix='feedback')
    if current_user == node.creator and current_user == post.creator:
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
            "node_view_as_post_creator.html",
            node=node,
            user_node=node,
            nodes=nodes,
            Post=Post,
            Engagement=Engagement,
            Message=Message,
            feedback_form=feedback_form)

    report_form = ReportForm(prefix='report')
    confirm_request_form = ConfirmForm(prefix='request')
    if current_user == node.creator or current_user == post.creator:
        engagement = node.engagements.filter(Engagement.state == Engagement.STATE_ENGAGED).first()
        engagement_request = node.engagements.filter(Engagement.state == Engagement.STATE_REQUESTED).first()
        if current_user.value_limit_cent < node.value_cent:
            flash('The value of the post exceeds your current limit. '
                  f'You are not be able to {"request" if current_user == node.creator else "accept"} engagements.',
                  category='warning')
        post = node.post
        # value limit checks
        # transaction_value_cent = post.price_cent
        transaction_value_cent = node.value_cent
        if (engagement is not None or engagement_request is not None) and \
                ((current_user == node.creator and post.creator.value_limit_cent < transaction_value_cent) or
                 (current_user == post.creator and node.creator.value_limit_cent < transaction_value_cent)):
            flash('The post value exceeds the current limit of the other user. This could be because a '
                  'dispute involving the user occurred after the current engagement was requested / accepted.',
                  category='warning')
        messages_asc = node.messages.order_by(Message.timestamp.asc()).all()
        return render_template(
            "node_view.html",
            node=node,
            engagement=engagement,
            engagement_request=engagement_request,
            messages_asc=messages_asc,
            message_form=message_form,
            report_form=report_form,
            rating_form=RatingForm(prefix='rate'),
            confirm_request_form=confirm_request_form,
            confirm_cancel_form=ConfirmForm(prefix='cancel'),
            confirm_accept_form=ConfirmForm(prefix='accept'),
            Post=Post,
            Engagement=Engagement,
            Message=Message,
            feedback_form=feedback_form)

    session['invite_code'] = str(node_id)
    return render_template(
        "node_view_as_other.html",
        node=node,
        message_form=message_form,
        confirm_request_form=confirm_request_form,
        report_form=report_form,
        Post=Post,
        feedback_form=feedback_form)
