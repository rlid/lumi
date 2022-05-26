from flask import render_template, session, redirect, url_for
from flask_login import current_user, login_user

from app import db
from app.models import User
from app.open2chat.forms import GenerateLinkForm, PostForm, SignUpForm

from app.open2chat import open2chat


@open2chat.route('/generate')
def generate():
    form = GenerateLinkForm()
    form.username.data = User.generate_short_code()
    return render_template('open2chat/generate_link.html', form=form)


@open2chat.route('/')
def landing():
    form = PostForm()
    return render_template("open2chat/landing.html", form=form)


@open2chat.route('/save-request', methods=['GET', 'POST'])
def save_request():
    form = PostForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            post = current_user.create_post(is_asking=True, price_cent=500, title=form.details.data)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('open2chat.save_request'))
        else:
            session['details'] = form.details.data
            return redirect(url_for('open2chat.save_email'))

    return render_template('open2chat/save_post.html', form=form)


@open2chat.route('/save-email', methods=['GET', 'POST'])
def save_email():
    form = SignUpForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        db.session.add(user)
        post = user.create_post(is_asking=True, price_cent=500, title=session.get('details'))
        db.session.add(post)
        db.session.commit()
        login_user(user, remember=False)
        return redirect(url_for('open2chat.save_request'))
    return render_template('open2chat/save_post.html', form=form)
