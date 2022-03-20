from flask import render_template, redirect, flash, url_for, Markup, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from app import db
from app.main import main
from app.main.forms import PostForm, ShareForm, ReportForm, FeedbackForm, RatingForm, ConfirmForm
from app.models import Notification
from app.models.user import Post, Node, Engagement
from utils.math import round_js


@main.route('/post-options')
@login_required
def post_options():
    return render_template("post_options.html", feedback_form=FeedbackForm(prefix='feedback'))


@main.route('/post/<int:is_private>', methods=['GET', 'POST'])
@login_required
def new_post(is_private):
    form = PostForm(prefix='post')
    if is_private == 1:
        form.referral_budget = 0.4  # Default for private mode

    if form.validate_on_submit():
        post_type = form.type.data
        price_cent = round(100 * form.price.data)
        post = current_user.create_post(post_type=post_type, price_cent=price_cent,
                                        title=form.title.data, body=form.body.data,
                                        is_private=(is_private == 1))
        return redirect(url_for('main.view_node', node_id=post.root_node.id))

    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template("post_create_edit.html", form=form, title="Create Post", feedback_form=FeedbackForm(prefix='feedback'))


@main.route('/post/<uuid:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.creator:
        flash('Cannot edit post that does not belong to you.', category='danger')
        abort(403)

    form = PostForm(prefix='post')
    form.edit_mode = True
    if form.validate_on_submit():
        current_user.edit_post(post, title=form.title.data, body=form.body.data)
        return redirect(url_for('main.view_node', node_id=post.root_node.id))

    form.type.default = post.type
    form.type.choices = [form.type.choices[0 if post.type == Post.TYPE_BUY else 1]]
    form.process()

    form.price.data = 0.01 * post.price_cent
    form.price.render_kw = {"readonly": None}

    form.title.data = post.title
    form.body.data = post.body[1:].replace('\\#', '#')
    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template('post_create_edit.html', form=form, title="Edit Post", feedback_form=FeedbackForm(prefix='feedback'))


@main.route('/toggle-editor', methods=['GET', 'POST'])
@login_required
def toggle_editor():
    current_user.use_markdown = not current_user.use_markdown
    db.session.add(current_user)
    db.session.commit()

    redirect_url = request.referrer
    if redirect_url is None or not redirect_url.startswith(request.root_url):
        redirect_url = url_for('main.index')
    return redirect(redirect_url)


@main.route('/post/<uuid:post_id>/archive-toggle')
@login_required
def toggle_archive_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    if current_user != post.creator:
        flash('Only the original poster can change the archive status of the post.', category='danger')
    elif post.is_reported:
        flash('Cannot change the archive status of the post because the post is reported. '
              'Please contact support for more information.', category='danger')
    else:
        current_user.toggle_archive(post)

    node = post.nodes.filter(Node.creator == current_user).first()
    return redirect(url_for('main.view_node', node_id=node.id))


@main.route('/post/<uuid:post_id>/report', methods=['POST'])
@login_required
def report_post(post_id):
    form = ReportForm()

    if form.validate_on_submit():
        post = Post.query.filter_by(id=post_id).first_or_404()
        current_user.report(post, form.text.data)
        send_email = current_app.config["EMAIL_SENDER"]
        send_email(
            sender='report@lumiask.com',
            recipient='support@lumiask.com',
            subject='Report received',
            body_text=f'{current_user}\n{post}\n{form.text.data}'
        )
        flash(
            'The post has been reported for investigation - it will not be visible until the investigation concludes.',
            category='warning')
    return redirect(url_for('main.index'))


@main.route('/node/<uuid:node_id>/share', methods=['GET', 'POST'])
@login_required
def share_node(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()
    if current_user != node.creator:
        user_node = node.post.nodes.filter(Node.creator == current_user).first()
        if user_node is None:
            user_node = current_user.create_node(node)
    else:
        user_node = node

    form = ShareForm(prefix='share')
    if form.validate_on_submit():
        if user_node.post.is_private and user_node.nodes_after_inc().count() == 1:
            user_node.referrer_reward_cent = round_js(
                0.01 * form.percentage.data * user_node.parent.remaining_referral_budget_cent)
            db.session.add(user_node)
            db.session.commit()
            flash(f'Your referral reward claim is adjusted to ${0.01 * user_node.referrer_reward_cent:.2f}',
                  category='info')
        else:
            flash('You cannot adjust your referral reward claim once someone has joined using your referrer\'s link.',
                  category='warning')
        return redirect(url_for('main.share_node', node_id=node_id))
    return render_template('node_share.html', node=user_node, form=form, Post=Post, feedback_form=FeedbackForm(prefix='feedback'))


@main.route('/node/<uuid:node_id>/request-engagement', methods=['POST'])
@login_required
def request_engagement(node_id):
    form = ConfirmForm(prefix='request')
    if form.validate_on_submit():
        node = Node.query.filter_by(id=node_id).first_or_404()
        post = node.post

        if post.is_archived:
            flash('Cannot request engagement because the post is archived.', category='danger')
            return redirect(url_for('main.view_node', node_id=node_id))
        if current_user == post.creator:
            flash('Cannot request engagement on your own post.', category='danger')
            return redirect(url_for('main.view_node', node_id=node_id))
        if current_user.value_limit_cent < (
                # value limit checks
                # post.price_cent
                node.value_cent
        ):
            flash('You currently cannot request engagement on posts worth more than $' +
                  f'{current_user.reward_limit:.2f}.', category='warning')
            return redirect(url_for('main.view_node', node_id=node_id))
        if post.type == Post.TYPE_SELL and \
                current_user.total_balance_cent - current_user.reserved_balance_cent < node.value_cent:
            flash('Insufficient funds, please ' +
                  Markup(f'<a href={url_for("main.account")}>top up</a> before you proceed.'), category='warning')
            return redirect(url_for('main.view_node', node_id=node_id))

        # the user must have his own node, and the request must be made on that node:
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
    return redirect(url_for('main.view_node', node_id=engagement.node_id))


@main.route('/engagement/<uuid:engagement_id>/cancel', methods=['POST'])
@login_required
def cancel_engagement(engagement_id):
    form = ConfirmForm(prefix='cancel')
    if form.validate_on_submit():
        engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()
        node = engagement.node
        post = node.post
        if post.is_archived:
            flash('Cannot cancel engagement because the post is archived.', category='danger')
        elif current_user != node.creator:
            flash('Cannot cancel engagement requested by someone else.', category='danger')
        elif engagement.state != Engagement.STATE_REQUESTED:
            flash('Cannot cancel engagement because it has been accepted.', category='warning')
        else:
            current_user.cancel_engagement(engagement)
    return redirect(url_for('main.view_node', node_id=engagement.node_id))


@main.route('/engagement/<uuid:engagement_id>/accept', methods=['POST'])
@login_required
def accept_engagement(engagement_id):
    form = ConfirmForm(prefix='accept')
    if form.validate_on_submit():
        engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()
        node = engagement.node
        post = engagement.node.post

        if post.is_archived:
            flash('Cannot accept engagement because the post is archived.', category='danger')
        elif engagement.state != Engagement.STATE_REQUESTED:
            flash('The engagement request is already accepted.', category='danger')
        elif current_user != post.creator:
            flash('Only the original poster can accept the engagement.', category='danger')
        elif current_user.value_limit_cent < (
                # value limit checks
                # post.price_cent
                node.value_cent
        ):
            flash('You currently cannot accept engagement on posts worth more than $' +
                  f'{current_user.reward_limit:.2f}.',
                  category='danger')
        elif post.type == Post.TYPE_BUY and \
                current_user.total_balance_cent - current_user.reserved_balance_cent < node.value_cent:
            flash('Insufficient funds, please ' +
                  Markup(f'<a href={url_for("main.account")}>top up</a> before you proceed.'), category='warning')
            return redirect(url_for('main.view_node', node_id=engagement.node_id))
        else:
            current_user.accept_engagement(engagement)
    return redirect(url_for('main.view_node', node_id=engagement.node_id))


@main.route('/engagement/<uuid:engagement_id>/<int:is_success>', methods=['POST'])
@login_required
def rate_engagement(engagement_id, is_success):
    form = RatingForm()
    if form.validate_on_submit():
        engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()
        # if engagement.node.value_cent > current_user.value_limit_cent:
        #     flash('You currently cannot rate engagement on posts worth more than $' +
        #           f'{current_user.reward_limit:.2f}.', category='warning')

        if current_user == engagement.asker:
            tip_cent = form.tip_cent.data
            if tip_cent > current_user.balance_available_cent:
                flash('The tip value exceeds your available account balance.', category='danger')
                return redirect(url_for('main.view_node', node_id=engagement.node_id))
            if tip_cent > round(engagement.node.answerer_reward_cent * (1 if is_success else 0.4)):
                flash('The tip value exceeds the maximum allowed', category='danger')
            current_user.rate_engagement(engagement, is_success, tip_cent=form.tip_cent.data)
        elif current_user == engagement.answerer:
            current_user.rate_engagement(engagement, is_success)
        else:
            flash('You cannot rate this engagement.', category='danger')

    return redirect(url_for('main.view_node', node_id=engagement.node_id))


@main.route('/account')
@login_required
def account():
    uncompleted_engagements = Engagement.query.filter(
        or_(Engagement.sender_id == current_user.id, Engagement.receiver_id == current_user.id),
        or_(
            Engagement.state == Engagement.STATE_ENGAGED,
            and_(Engagement.state == Engagement.STATE_REQUESTED, Post.is_archived.is_not(True))
        ),
        Post.is_reported.is_not(True)
    ).join(
        Node, Node.id == Engagement.node_id
    ).join(
        Post, Post.id == Node.post_id
    ).order_by(
        Engagement.last_updated.desc()
    ).all()

    post_ids_seen = set()
    node_ids_seen = set()
    for engagement in uncompleted_engagements:
        if engagement.node.post_id not in post_ids_seen:
            post_ids_seen.add(engagement.node.post_id)
        if engagement.node_id not in node_ids_seen:
            node_ids_seen.add(engagement.node_id)

    # other_root_nodes = current_user.nodes.filter(
    #     Post.id.not_in(post_ids_seen),
    #     Node.parent_id.is_(None)
    # ).order_by(
    #     Node.last_updated.desc()
    # ).all()
    # other_child_nodes = current_user.nodes.filter(
    #     Node.id.not_in(node_ids_seen),
    #     Node.parent_id.is_not(None)
    # ).order_by(
    #     Node.last_updated.desc()
    # ).all()

    nodes = current_user.nodes.order_by(
        Node.last_updated.desc()
    ).all()
    return render_template(
        "account.html",
        user=current_user,
        uncompleted_engagements=uncompleted_engagements,
        nodes=nodes,
        Post=Post,
        Node=Node,
        Engagement=Engagement,
        title='Account',
        feedback_form=FeedbackForm(prefix='feedback')
    )


@main.route('/alerts')
@login_required
def alerts():
    notifications = current_user.notifications.order_by(Notification.timestamp.desc())
    return render_template('alerts.html', notifications=notifications, title='Alerts', feedback_form=FeedbackForm(prefix='feedback'))
