import secrets
from flask import render_template, redirect, request, url_for, flash, Markup
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.auth import auth
from app.models import User
from app.auth.forms import LogInForm, SignUpForm


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LogInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None:
            if user.password_hash and user.verify_password(form.password.data):
                login_user(user, form.remember_me.data)
                next_url = request.args.get("next")
                if next_url is None or not next_url.startwith("/"):
                    next_url = url_for("main.index")
                return redirect(next_url)
            elif not form.password.data:
                cookie_key = secrets.token_urlsafe()
                token = user.generate_token(action="login", cookie_key=cookie_key)
                response = redirect(url_for("main.index"))
                response.set_cookie("login_key", cookie_key)
                print(url_for("auth.login_by_token", token=token, remember=1, _external=True))
                flash("An email with login link has been sent to your email address.", category="info")
                return response
        flash("Invalid username or password", category="danger")
    return render_template("auth/login.html", form=form)


@auth.route("/login/<token>/<int:remember>")
def login_by_token(token, remember):
    cookie_key = request.cookies.get("login_key")
    token_user_id, token_cookie_key = User.decode_token(token, "login")
    if cookie_key is not None and cookie_key == token_cookie_key:
        user = User.query.get(int(token_user_id))
        login_user(user, remember=remember)
        response = redirect(url_for("main.index"))
        response.delete_cookie("login_key")
        flash("You have logged in.", category="success")
        return response
    else:
        flash("The login link is invalid or has expired.", category="danger")
        return redirect(url_for("main.index"))


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", category="success")
    return redirect(url_for("main.index"))


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = SignUpForm()
    if form.validate_on_submit():
        if form.password.data:
            user = User(email=form.email.data, password=form.password.data)
        else:  # do not generate password hash if no password given:
            user = User(email=form.email.data)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=False)
        token = user.generate_token(action="confirm")
        print(url_for("auth.confirm", token=token, remember=1, _external=True))
        flash("An email with confirmation link has been sent to the email address you provided.", category="info")
        return redirect(url_for("main.index"))
    return render_template("auth/signup.html", form=form)


@auth.route("/confirm/<token>/<int:remember>")
def confirm(token, remember):
    user_id, cookie_key = User.decode_token(token, "confirm")
    user = User.query.get(int(user_id))
    if not user.confirmed:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=remember)
        flash("Your email address has been verified.", category="success")
    else:
        flash("The confirmation link is invalid or has expired.", category="danger")
    return redirect(url_for("main.index"))


@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.blueprint != "auth" \
            and request.endpoint != "static":
        flash("Your email address has not been verified. " +
              Markup(f"<a href='{url_for('auth.resend_confirmation')}'>Click here</a> ") +
              "to request another confirmation email.", category="warning")


@auth.route("/confirm")
@login_required
def resend_confirmation():
    token = current_user.generate_token(action="confirm")
    print(url_for("auth.confirm", token=token, remember=1, _external=True))
    flash("A new email with confirmation link has been sent to the email address you provided.", category="info")
    return redirect(url_for("main.index"))
