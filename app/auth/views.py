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
            elif not form.password.data:  # passwordless login:
                response = redirect(url_for("main.index"))
                # add login_key for extra safety - the key is stored as a cookie on the client side, which means that
                # if the login link is opened in a different browser environment (e.g. on a different PC / phone), it
                # will be invalid as the cookie does not exist:
                # login_key = secrets.token_urlsafe()
                token = user.generate_token(action="login")  # , client_key=login_key
                # response.set_cookie("login_key", login_key)
                print(url_for("auth.login_by_token", token=token, remember=1, _external=True))
                flash("An email with login link has been sent to your email address.", category="info")
                return response
        flash("Invalid username or password", category="danger")
    return render_template("auth/login.html", form=form)


@auth.route("/login/<token>/<int:remember>")
def login_by_token(token, remember):
    data = User.decode_token(token)
    user = User.query.get(int(data.get("login")))
    # client_key = request.cookies.get("login_key")
    if user.verify_token_data(data, action="login"):  # , client_key=client_key
        login_user(user, remember=remember)
        response = redirect(url_for("main.index"))
        flash("You have logged in using a login link.", category="success")
    else:
        response = redirect(url_for("main.index"))
        flash("The login link is invalid or has expired.", category="danger")
    # if client_key == data.get("client_key"):
    #     response.delete_cookie("login_key")
    return response


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
        else:  # do not generate password hash if no password given (passwordless account):
            user = User(email=form.email.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_token(action="confirm")
        print(url_for("auth.confirm", token=token, remember=1, _external=True))
        flash("An email with confirmation link has been sent to the email address you provided.", category="info")
        return redirect(url_for("main.index"))
    return render_template("auth/signup.html", form=form)


@auth.route("/confirm/<token>/<int:remember>")
def confirm(token, remember):
    data = User.decode_token(token)
    user = User.query.get(int(data.get("confirm")))
    if user.verify_token_data(data, action="confirm"):
        if not user.confirmed:
            user.confirmed = True
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=remember)
            flash("Your email address has been verified.", category="success")
        else:
            flash("Your email address has already been verified.", category="warning")  # TODO: should never reach here
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
