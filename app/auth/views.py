import jwt
import json
import requests
import time
from flask import render_template, redirect, request, url_for, flash, Markup, abort, session, Response
from flask_login import login_user, logout_user, login_required, current_user
from oauthlib.oauth2 import WebApplicationClient

from app import db
from app.auth import auth
from app.models import User
from app.auth.forms import LogInForm, SignUpForm
from config import Config
from utils import security_utils

google_oauth_client = WebApplicationClient(Config.OAUTH_GOOGLE_CLIENT_ID)
apple_oauth_client = WebApplicationClient(Config.OAUTH_APPLE_CLIENT_ID)


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


@auth.route("/google")
def google():
    provider_config = requests.get(Config.OAUTH_GOOGLE_URL).json()
    authorization_endpoint = provider_config["authorization_endpoint"]

    state = security_utils.random_urlsafe(nbytes=Config.OAUTH_STATE_NBYTES)
    session["oauth_state"] = state
    request_uri = google_oauth_client.prepare_request_uri(
        uri=authorization_endpoint,
        redirect_uri=f"{request.base_url}/callback",
        scope=["openid", "email", "profile"],
        state=state)
    print(f"request_uri = {request_uri}")
    return redirect(request_uri)


@auth.route("/google/callback")
def google_callback():
    authorization_code = request.args.get("code")
    print(f"request.args = {json.dumps(request.args, indent=4)}")
    if session.get("oauth_state") != request.args.get("state"):
        abort(500)

    provider_config = requests.get(Config.OAUTH_GOOGLE_URL).json()
    token_endpoint = provider_config["token_endpoint"]

    token_url, headers, body = google_oauth_client.prepare_token_request(
        token_url=token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=authorization_code)
    print(f"token_url = {token_url}")
    print(f"headers = {headers}")
    print(f"body = {body}")
    token_response = requests.post(
        url=token_url,
        headers=headers,
        data=body,
        auth=(Config.OAUTH_GOOGLE_CLIENT_ID, Config.OAUTH_GOOGLE_CLIENT_SECRET))

    # parse the token and raise OAuth2Error if response is invalid
    parsed_token = google_oauth_client.parse_request_body_response(json.dumps(token_response.json()))
    print(f"parsed_token = {json.dumps(parsed_token, indent=4)}")

    userinfo_endpoint = provider_config["userinfo_endpoint"]
    userinfo_url, headers, body = google_oauth_client.add_token(userinfo_endpoint)
    print(f"userinfo_url = {userinfo_url}")
    print(f"headers = {headers}")
    print(f"body = {body}")
    userinfo_response = requests.get(userinfo_url, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        email = userinfo_response.json()["email"]

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


@auth.route("/apple")
def apple():
    provider_config = requests.get(Config.OAUTH_APPLE_URL).json()
    authorization_endpoint = provider_config["authorization_endpoint"]

    state = security_utils.random_urlsafe(nbytes=Config.OAUTH_STATE_NBYTES)
    session["oauth_state"] = state
    request_uri = apple_oauth_client.prepare_request_uri(
        uri=authorization_endpoint,
        redirect_uri=f"{request.base_url}/callback",
        scope=["openid", "email", "name"],
        response_mode="form_post",
        state=state)
    print(f"request_uri = {request_uri}")
    return redirect(request_uri)


def _apple_secret():
    headers = {"kid": Config.OAUTH_APPLE_KEY_ID}

    payload = {
        "iss": Config.OAUTH_APPLE_TEAM_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 15777000,  # 6 months in seconds
        "aud": "https://appleid.apple.com",
        "sub": Config.OAUTH_APPLE_CLIENT_ID}

    return jwt.encode(
        payload=payload,
        key=Config.OAUTH_APPLE_PRIVATE_KEY,
        algorithm='ES256',
        headers=headers)


@auth.route("/apple/callback", methods=["GET", "POST"])
def apple_callback():
    authorization_code = request.form.get("code")
    print(f"request.form = {json.dumps(request.form, indent=4)}")

    if session.get("oauth_state") != request.form.get("state"):
        abort(Response("Authorization server returned an invalid state parameter.", 500))

    provider_config = requests.get(Config.OAUTH_APPLE_URL).json()
    token_endpoint = provider_config["token_endpoint"]

    client_secret = _apple_secret()
    token_url, headers, body = apple_oauth_client.prepare_token_request(
        token_url=token_endpoint,
        # authorization_response=request.url,
        redirect_url=request.base_url,
        client_id=Config.OAUTH_APPLE_CLIENT_ID,
        client_secret=client_secret,
        code=authorization_code)
    print(f"token_url = {token_url}")
    print(f"headers = {headers}")
    print(f"body = {body}")
    token_response = requests.post(
        url=token_url,
        headers=headers,
        data=body)

    # parse the token and raise OAuth2Error if response is invalid
    parsed_token = apple_oauth_client.parse_request_body_response(json.dumps(token_response.json()))
    print(f"parsed_token = {json.dumps(parsed_token, indent=4)}")

    id_token = parsed_token.get("id_token")
    id_token_data = jwt.decode(id_token, options={"verify_signature": False})
    print(f"id_token_data = {json.dumps(id_token_data, indent=4)}")

    # userinfo_endpoint = provider_config["userinfo_endpoint"]
    # userinfo_url, headers, body = apple_oauth_client.add_token(userinfo_endpoint)
    # print(f"userinfo_url = {userinfo_url}")
    # print(f"headers = {headers}")
    # print(f"body = {body}")
    # userinfo_response = requests.get(url=userinfo_url, headers=headers, data=body)

    if id_token_data.get("email_verified"):
        email = id_token_data["email"]

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
