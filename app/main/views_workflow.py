from flask import render_template, redirect, flash, url_for, Markup, request, abort
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from app import db
from app.main import main
from app.main.forms import PostForm, MarkdownPostForm
from app.models.user import Post, Node, Engagement


@main.route('/post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = MarkdownPostForm() if current_user.use_markdown else PostForm()
    if form.validate_on_submit():
        current_user.create_post(type=form.type.data, reward_cent=round(100 * form.reward.data),
                                 title=form.title.data, body=form.body.data)
        return redirect(url_for('main.browse'))
    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template("edit_post.html", form=form, title="New Post")


@main.route('/post/<post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.creator:
        flash('Cannot edit post that does not belong to you.', category='danger')
        abort(403)

    form = MarkdownPostForm() if current_user.use_markdown else PostForm()
    if form.validate_on_submit():
        current_user.edit_post(post, title=form.title.data, body=form.body.data)
        return redirect(url_for('main.browse'))

    form.type.default = post.type
    form.type.choices = [form.type.choices[0 if post.type == Post.TYPE_BUY else 1]]
    form.process()

    form.reward.data = post.reward
    form.reward.render_kw = {"readonly": None}

    form.title.data = post.title
    form.body.data = post.body[1:].replace('\\#', '#')
    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template('edit_post.html', form=form, title="Edit Post")


@main.route('/toggle-editor', methods=['GET', 'POST'])
@login_required
def toggle_editor():
    current_user.use_markdown = not current_user.use_markdown
    db.session.add(current_user)
    db.session.commit()

    redirect_url = request.referrer
    if not redirect_url.startswith(request.root_url):
        redirect_url = url_for('main.index')
    return redirect(redirect_url)


@main.route('/post/<post_id>/archive-toggle')
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


@main.route('/post/<post_id>/report', methods=['POST'])
@login_required
def report_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    reason = request.form.get('reason')
    current_user.report(post, reason)
    flash('The post has been reported for investigation and it will not be visible in the meantime.',
          category='warning')
    return redirect(url_for('main.index'))


@main.route('/node/<node_id>/share')
@login_required
def share_node(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()
    if current_user != node.creator:
        user_node = node.post.nodes.filter(Node.creator == current_user).first()
        if user_node is None:
            user_node = current_user.create_node(node)
    else:
        user_node = node
    return render_template('share_node.html', node=user_node)


@main.route('/node/<node_id>/request-engagement')
@login_required
def request_engagement(node_id):
    node = Node.query.filter_by(id=node_id).first_or_404()
    post = node.post

    if post.is_archived:
        flash('Cannot request for engagement because the post is archived.', category='danger')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))
    if current_user == post.creator:
        flash('Cannot request for engagement on your own post.', category='danger')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))
    if post.reward_cent > current_user.reward_limit_cent:
        flash('You currently cannot request for engagement on posts worth more than $' +
              f'{current_user.reward_limit:.2f}.', category='warning')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))
    if post.type == Post.TYPE_SELL and \
            current_user.total_balance_cent - current_user.reserved_balance_cent < post.reward_cent:
        flash('Insufficient funds, please top up before you proceed.', category='warning')
        return redirect(url_for('main.view_node', node_id=node_id, _anchor='form'))

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
    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<engagement_id>/cancel')
@login_required
def cancel_engagement(engagement_id):
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

    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<engagement_id>/accept')
@login_required
def accept_engagement(engagement_id):
    engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()
    post = engagement.node.post

    if post.is_archived:
        flash('Cannot accept engagement because the post is archived.', category='danger')
    elif engagement.state != Engagement.STATE_REQUESTED:
        flash('The request for engagement can no longer be accepted.', category='danger')
    elif current_user != post.creator:
        flash('Only the original poster can accept the engagement.', category='danger')
    elif post.reward_cent > current_user.reward_limit_cent:
        flash('You currently cannot accept engagement on posts worth more than $' +
              f'{current_user.reward_limit:.2f}.',
              category='danger')
    elif post.type == Post.TYPE_BUY and \
            current_user.total_balance_cent - current_user.reserved_balance_cent < post.reward_cent:
        flash('Insufficient funds, please top up before you proceed.', category='warning')
        return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))
    else:
        current_user.accept_engagement(engagement)
    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/engagement/<engagement_id>/<int:is_success>')
@login_required
def rate_engagement(engagement_id, is_success):
    engagement = Engagement.query.filter_by(id=engagement_id).first_or_404()

    # if engagement.node.reward_cent > current_user.reward_limit_cent:
    #     flash('You currently cannot rate engagement on posts worth more than $' +
    #           f'{current_user.reward_limit:.2f}.', category='warning')

    if current_user == engagement.node.creator or current_user == engagement.node.post.creator:
        current_user.rate_engagement(engagement, is_success)
    else:
        flash('Only the original poster can accept the engagement.', category='danger')

    return redirect(url_for('main.view_node', node_id=engagement.node_id, _anchor='form'))


@main.route('/account')
@login_required
def account():
    uncompleted_engagements = Engagement.query.filter(
        or_(Engagement.sender_id == current_user.id, Engagement.receiver_id == current_user.id),
        or_(
            Engagement.state == Engagement.STATE_ENGAGED,
            and_(Engagement.state == Engagement.STATE_REQUESTED, Post.is_archived.is_not(True))
        )
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

    other_posts = current_user.posts.filter(
        Post.id.not_in(post_ids_seen)
    ).order_by(
        Post.last_updated.desc()
    ).all()
    other_nodes = current_user.nodes.filter(
        Node.parent_id.is_not(None),
        Node.id.not_in(node_ids_seen)
    ).join(
        Post, Post.id == Node.post_id
    ).order_by(
        Node.last_updated.desc()
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
