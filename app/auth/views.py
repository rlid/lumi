from flask import render_template, redirect, request, url_for, flash, Markup
from flask_login import login_user, logout_user, login_required, current_user

from app import db, oauth
from app.auth import auth
from app.models import User
from app.auth.forms import LogInForm, SignUpForm
from config import Config
from utils import security_utils


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
                if next_url is None or not next_url.startswith("/"):
                    next_url = url_for("main.index")
                return redirect(next_url)
            elif not form.password.data:  # passwordless login:
                response = redirect(url_for("main.index"))
                # add client_nonce for extra safety - the nonce is stored as a cookie on the client side, which means
                # that if the login link is opened in a different browser environment (e.g. on a different PC / phone),
                # it will be invalid as the cookie does not exist, and only the hashed nonce is included in the token
                # for security reasons:
                client_nonce = security_utils.random_urlsafe(nbytes=Config.CLIENT_NONCE_NBYTES)
                token = user.generate_token(
                    action="login",
                    client_nonce_hash=security_utils.hash_string(client_nonce,
                                                                 digest_size=Config.CLIENT_NONCE_HASH_DIGEST_SIZE))
                response.set_cookie("client_nonce", client_nonce, httponly=True)
                print(f"client_nonce is set to [{client_nonce}].")
                print(url_for("auth.login_by_token", token=token, remember=1, _external=True))
                flash("An email with login link has been sent to your email address.", category="info")
                return response
        flash("Invalid username or password", category="danger")
    return render_template("auth/login.html", form=form)


@auth.route("/login/<token>/<int:remember>")
def login_by_token(token, remember):
    client_nonce_hash = request.cookies.get("client_nonce")
    # client_nonce_hash is just client_nonce at this point, hash it if it is not None:
    if client_nonce_hash is not None:
        client_nonce_hash = security_utils.hash_string(client_nonce_hash,
                                                       digest_size=Config.CLIENT_NONCE_HASH_DIGEST_SIZE)

    token_data = User.decode_token(token)
    token_user = User.query.get(int(token_data.get("login")))

    response = redirect(url_for("main.index"))
    if token_user.verify_token_data(token_data, action="login", client_nonce_hash=client_nonce_hash):
        login_user(token_user, remember=remember)
        flash("You have logged in using a login link.", category="success")
    else:
        flash("The login link is invalid or has expired.", category="danger")
    if client_nonce_hash == token_data.get("client_nonce_hash") and client_nonce_hash is not None:
        response.delete_cookie("client_nonce")
        print(f"client_nonce [{request.cookies.get('client_nonce')}] is deleted.")
    return response


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", category="success")
    return redirect(url_for("main.index"))


@auth.route("/logout-everywhere")
@login_required
def logout_all():
    current_user.reset_remember_id()
    flash("You have been logged out on all devices.", category="success")
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
            flash("Your email address has already been verified.",
                  category="warning")  # TODO: should never reach here
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


@auth.route('/google')
def google():
    redirect_uri = url_for("auth.google_callback", _external=True)
    response = oauth.google.authorize_redirect(redirect_uri)
    print(f"response.response = {response.response}")
    return response


@auth.route('/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    print(f"token = {token}")
    userinfo = token.get("userinfo")
    print(f"userinfo = {userinfo}")

    if userinfo and userinfo.get("email_verified"):
        email = userinfo["email"]

        user = User.query.filter_by(email=email).first()
        if user is not None:
            login_user(user, remember=True)
            flash("You have logged in with Google.", category="success")
        else:
            user = User(email=email, confirmed=True)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("You have signed up with Google.", category="success")
        return redirect(url_for("main.index"))
    else:
        flash("User email not available or not verified by Google.", category="danger")
    return redirect(url_for("auth.login"))


@auth.route('/apple')
def apple():
    redirect_uri = url_for("auth.apple_callback", _external=True)
    response = oauth.apple.authorize_redirect(redirect_uri)
    print(f"response.response = {response.response}")
    return response


@auth.route('/apple/callback', methods=["POST"])
def apple_callback():
    token = oauth.apple.authorize_access_token()
    print(f"token = {token}")
    userinfo = token.get("userinfo")
    print(f"userinfo = {userinfo}")

    if userinfo and userinfo.get("email_verified"):
        email = userinfo["email"]

        user = User.query.filter_by(email=email).first()
        if user is not None:
            login_user(user, remember=True)
            flash("You have logged in with Apple.", category="success")
        else:
            user = User(email=email, confirmed=True)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("You have signed up with Apple.", category="success")
        return redirect(url_for("main.index"))
    else:
        flash("User email not available or not verified by Apple.", category="danger")
    return redirect(url_for("auth.login"))
