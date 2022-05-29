import math

from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_user, login_required

from app import db
from app.models import User, TemporaryRequest, Post, Node
from app.v2.forms import GenerateLinkForm, PostForm, SignUpForm

from app.v2 import v2


@v2.route('/open2chat')
def open2chat():
    form = GenerateLinkForm()
    form.username.data = User.generate_short_code()
    return render_template('v2/open2chat.html', form=form)


@v2.route('/', methods=['GET', 'POST'])
def landing():
    form = PostForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            post = current_user.create_post(
                is_asking=True,
                is_private=True,
                price_cent=100 * int(form.reward.data[1:]),
                topic=form.topic.data,
                title=form.details.data)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('v2.ack_request', post_id=post.id))
        else:
            temporary_request = TemporaryRequest(
                topic=form.topic.data,
                details=form.details.data,
                reward_cent=100 * int(form.reward.data[1:]))
            db.session.add(temporary_request)
            db.session.commit()
            return redirect(url_for('v2.save_email', temporary_request_id=temporary_request.id))

    return render_template(
        "v2/landing.html",
        form=form,
        max_reward=math.floor(current_user.value_limit) if current_user.is_authenticated else User.DEFAULT_VALUE_LIMIT
    )


@v2.route('/ack-request/<uuid:post_id>')
@login_required
def ack_request(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('v2/ack_request.html', node=post.root_node)


def _save_request(user, temporary_request, price_cent=500):
    post = user.create_post(
        is_asking=True,
        is_private=True,
        price_cent=temporary_request.reward_cent,
        topic=temporary_request.topic,
        title=temporary_request.details)
    db.session.add(post)
    db.session.delete(temporary_request)
    session.pop('temporary_request_id', None)
    return post


@v2.route('/save-request/<uuid:temporary_request_id>')
@login_required
def save_request(temporary_request_id):
    temporary_request = TemporaryRequest.query.get_or_404(temporary_request_id)
    post = _save_request(current_user, temporary_request)
    db.session.commit()
    return redirect(url_for('v2.ack_request', post_id=post.id))


@v2.route('/save-email/<uuid:temporary_request_id>', methods=['GET', 'POST'])
def save_email(temporary_request_id):
    temporary_request = TemporaryRequest.query.get_or_404(temporary_request_id)
    session['temporary_request_id'] = temporary_request_id

    form = SignUpForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None:
            if user.signup_method == 'email' and user.password_hash is None:
                flash('You have used this email address before. '
                      'Please finish setting up your account by resetting your password before continuing.',
                      category='warning')
                return redirect(url_for('auth.password_reset_request', email=user.email))
            else:
                flash('You have used this email address before. Please log in to continue.', category='warning')
                return redirect(url_for('auth.login', email=user.email))

        user = User(email=form.email.data)
        db.session.add(user)
        post = _save_request(user, temporary_request)
        db.session.commit()
        login_user(user, remember=False)
        return redirect(url_for('v2.ack_request', post_id=post.id))
    return render_template('v2/save_email.html', form=form)
