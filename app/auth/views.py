from datetime import timedelta

from authlib.integrations.base_client import MismatchingStateError
from flask import render_template, redirect, request, url_for, flash, Markup, session, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app import db, oauth
from app.auth import auth
from app.auth.forms import LogInForm, SignUpForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm
from app.models.invite_code import InviteCode
from app.models.user import User
from config import Config
from utils import security_utils


# intended user: is_authenticated no | signup_method email | email_verified all
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LogInForm(prefix='login')
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None:
            if user.signup_method == "email":
                if user.verify_password(form.password.data):
                    login_user(user, form.remember_me.data)
                    next_url = request.args.get('next')
                    if next_url is None or not next_url.startswith('/'):
                        return redirect(url_for('main.index'))
                    return redirect(next_url)
                flash('Invalid username or password', category='danger')
            else:
                flash(f'The account associated with {form.email.data} does not support login via email and password. '
                      'Please use an alternative login method.',
                      category='danger')
        else:
            flash('Invalid username or password', category='danger')
    return render_template('auth/login.html', form=form, is_continue=request.args.get('next') is not None)


@auth.route('/login/<uuid:user_id>')
def force_login(user_id):
    user = User.query.filter_by(id=user_id).first_or_404()
    user.email_verified = True
    db.session.add(user)
    db.session.commit()  # OK
    login_user(user, False)
    flash('You have logged in.', category='success')
    redirect_url = request.referrer
    if redirect_url is None or not redirect_url.startswith(request.root_url):
        return redirect(url_for('main.index'))
    return redirect(redirect_url)


# intended user: is_authenticated yes | signup_method all | email_verified all
@auth.route('/remember')
@login_required
def remember():
    login_user(current_user, remember=True)
    # flash('You will stay logged in on this device until you log out.', category='warning')
    redirect_url = request.referrer
    if redirect_url is None or not redirect_url.startswith(request.root_url):
        return redirect(url_for('main.index'))
    return redirect(redirect_url)


# intended user: is_authenticated yes | signup_method all | email_verified all
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', category='success')
    return redirect(url_for('main.index'))


# intended user: is_authenticated yes | signup_method all | email_verified all
@auth.route('/logout-everywhere')
@login_required
def logout_all():
    current_user.reset_remember_id()
    logout_user()
    flash('You have been logged out on all devices.', category='success')
    return redirect(url_for('main.index'))


# intended user: all | signup_method all | email_verified all
@auth.route('/signup/<int:code_length>')
def invite_code(code_length):
    ic = InviteCode.generate(
        length=code_length,
        expiry_timedelta=timedelta(days=30)
    )
    db.session.commit()  # OK
    return redirect(url_for("auth.signup", code=ic.code))


# intended user: is_authenticated no | signup_method email | email_verified n/a
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        flash("You have already signed up.", category="warning")
        return redirect(url_for("main.index"))

    form = SignUpForm(prefix='signup')
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(), password=form.password.data, signup_method='email')
        db.session.add(user)
        session.pop("invite_code")
        InviteCode.delete(form.invite_code.data)
        token = user.generate_token(action="confirm")
        db.session.commit()  # OK
        send_email = current_app.config["EMAIL_SENDER"]
        send_email(
            sender='LumiAsk <welcome@lumiask.com>', recipient=user.email, subject='Confirm your LumiAsk account',
            body_text=render_template('email/confirm.txt', token=token),
            body_html=render_template('email/confirm.html', token=token)
        )
        flash(f'A confirmation email has been sent to {form.email.data}.',
              category="info")
        login_user(user, remember=False)
        return redirect(url_for("main.index"))

    code = request.args.get('code') or session.get('invite_code')
    if code is not None:
        is_valid, invite_code, error_message = InviteCode.validate(code=code)
        form.invite_code.data = code
        if is_valid:
            session['invite_code'] = code
            if invite_code:
                form.invite_code.render_kw = {'readonly': ''}
            else:
                form.hide_invite_code = True
        else:
            form.invite_code.errors = ['The invite code is invalid.']

    return render_template("auth/signup.html", form=form, has_invite_code=code is not None)


# intended user: is_authenticated yes | signup_method implied | email_verified no (implying signup_method is email)
@auth.route("/confirm/<token>")
@login_required
def confirm(token):
    if current_user.email_verified:
        flash("Your email address is already verified.", category="warning")
        return redirect(url_for("main.index"))

    if current_user.verify_token(token, action='confirm'):
        current_user.email_verified = True
        db.session.add(current_user)
        db.session.commit()  # OK
        flash("Your email address has been verified.", category="success")
    else:
        flash("The confirmation link is invalid or has expired.", category="danger")
    return redirect(url_for("main.index"))


# intended user: is_authenticated yes | signup_method implied | email_verified no (implying signup_method is email)
# which signup method is relevant: email
@auth.route("/confirm")
@login_required
def resend_confirmation():
    if current_user.email_verified:
        flash("Your email address is already verified.", category="warning")
        return redirect(url_for("main.index"))

    token = current_user.generate_token(action="confirm")
    db.session.commit()  # OK
    send_email = current_app.config["EMAIL_SENDER"]
    send_email(
        sender='LumiAsk <welcome@lumiask.com>', recipient=current_user.email, subject='Confirm your LumiAsk account',
        body_text=render_template('email/confirm.txt', token=token),
        body_html=render_template('email/confirm.html', token=token)
    )
    flash(f'A new confirmation email has been sent to {current_user.email}.',
          category="info")
    return redirect(url_for("main.index"))


# intended user: is_authenticated yes | signup_method email | email_verified n/a
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if current_user.signup_method != "email":
        flash(f"You cannot change password because your account does not support login via email and password.",
              category='danger')
        return redirect(url_for("main.index"))

    form = ChangePasswordForm(prefix='change')
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()  # OK
            flash('Your password has been updated.', category='success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password', category='danger')
    return render_template("auth/change_password.html", form=form)


# intended user: is_authenticated no | signup_method email | email_verified n/a
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if current_user.is_authenticated:
        flash("You have already logged in. Please log out first to initiate password reset.", category="warning")
        return redirect(url_for('main.index'))

    form = PasswordResetRequestForm(prefix='reset-request')
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user:
            if user.signup_method != "email":
                flash(f"Your account does not support password reset. Please use an alternative login method.",
                      category='danger')
                return redirect(url_for("auth.login"))
            # add a random site_rid for extra safety - the id is stored as a cookie on the client side, which means
            # that if the login link is opened on a different site (e.g. on a different PC / phone), it will be invalid
            # as the cookie does not exist, and only the hashed id is included in the token for security reasons:
            site_rid = security_utils.random_urlsafe(nbytes=Config.SITE_RID_NBYTES)
            session['auth_reset'] = site_rid
            current_app.logger.info(f"site_rid is set to [{site_rid}].")
            token = user.generate_token(
                action="reset",
                site_rid_hash=security_utils.hash_string(
                    site_rid,
                    digest_size=Config.SITE_RID_HASH_DIGEST_SIZE
                ))
            db.session.commit()  # OK
            send_email = current_app.config["EMAIL_SENDER"]
            send_email(
                sender='LumiAsk <support@lumiask.com>', recipient=user.email, subject='Reset your password',
                body_text=render_template('email/reset.txt', token=token),
                body_html=render_template('email/reset.html', token=token)
            )
            flash(f'An email with instructions to reset your password has been sent to {form.email.data}.',
                  category='info')
            return redirect(url_for('main.index'))
        flash(f'{form.email.data} is not associated with any account in our system.', category='danger')
    return render_template('auth/reset_password_request.html', form=form)


# intended user: is_authenticated no | signup_method email | email_verified n/a
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if current_user.is_authenticated:
        flash("You have already logged in. Please log out first to initiate password reset.", category="warning")
        return redirect(url_for('main.index'))

    form = PasswordResetForm(prefix='reset')
    if form.validate_on_submit():
        site_rid_hash = session.get('auth_reset')
        # site_rid_hash is just site_rid at this point, hash it if it is not None:
        if site_rid_hash is not None:
            site_rid_hash = security_utils.hash_string(site_rid_hash,
                                                       digest_size=Config.SITE_RID_HASH_DIGEST_SIZE)

        is_verified, user = User.verify_token_static(token=token,
                                                     action="reset",
                                                     site_rid_hash=site_rid_hash)
        if is_verified:
            user.password = form.password.data
            db.session.add(user)
            db.session.commit()  # OK
            flash('Your password has been updated.', category='success')
            current_app.logger.info(f"site_rid [{session.get('auth_reset')}] is deleted.")
            session.pop('auth_reset')
            login_user(user, remember=False)
            return redirect(url_for('main.index'))
        else:
            db.session.commit()  # OK
            flash('The password reset link is invalid or has expired.', category='danger')
            return redirect(url_for('auth.password_reset_request'))
    return render_template('auth/reset_password.html', form=form)


def make_oauth_routes(oauth_provider, callback_methods=None):
    if callback_methods is None:
        callback_methods = ["GET"]
    name_capitalized = oauth_provider.name.capitalize()
    callback_endpoint = f"{oauth_provider.name}_callback"

    # intended user: is_authenticated no | signup_method oauth | email_verified n/a
    def entry():
        if current_user.is_authenticated:
            flash('You have already logged in.', category='warning')
            return redirect(url_for("main.index"))

        redirect_uri = url_for(f"auth.{callback_endpoint}", _external=True)
        response = oauth_provider.authorize_redirect(redirect_uri)
        # current_app.logger.info(f"response.response = {response.response}")
        return response

    # intended user: is_authenticated no | signup_method email | email_verified n/a
    def callback():
        # current_app.logger.debug('=====DEBUG BEGIN=====')
        # state = request.form.get('state') or request.args.get('state')
        # current_app.logger.debug(state, session.get(f'_state_{oauth_provider.name}_{state}'))
        # current_app.logger.debug(type(session))
        # current_app.logger.debug(session)
        # current_app.logger.debug(session.keys())
        # current_app.logger.debug('=====DEBUG END=====')
        try:
            token = oauth_provider.authorize_access_token()
        except MismatchingStateError as e:
            current_app.logger.exception(e)
            flash('Internal error - please contact support.', category='danger')
            return redirect(url_for("auth.signup"))
        # current_app.logger.debug(f"token = {token}")
        userinfo = token.get("userinfo")
        # current_app.logger.debug(f"userinfo = {userinfo}")

        if not userinfo or not userinfo.get("email_verified"):
            flash(f"Your {name_capitalized} account does not have a verified email address.", category="danger")
            if session.get("invite_code"):
                return redirect(url_for("auth.signup", code=session.get("invite_code")))
            return redirect(url_for("auth.signup"))

        email = userinfo["email"].lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            if session.get("invite_code") is None:
                # new user and no invite_code in session
                # user must have clicked Signing in with Provider before signing up with the provider (as it is
                # impossible to click Sign up with Provider without a valid invite code at the time of writing)
                # TODO: review once invite code restriction is removed
                flash(f'{userinfo["email"]} is not associated with any account. Please sign up first.',
                      category='danger')
                return redirect(url_for("auth.signup"))
            is_valid, invite_code, error_message = InviteCode.validate(code=session.get("invite_code"))
            if not is_valid:
                flash(error_message, category="danger")
                return redirect(url_for("auth.signup"))
            user = User(email=email, email_verified=True, signup_method=oauth_provider.name)
            db.session.add(user)
            if invite_code:
                db.session.delete(invite_code)
            db.session.commit()  # OK
            session.pop("invite_code")

        if user.signup_method != oauth_provider.name:
            flash(
                f'The account associated with {userinfo["email"]} does not support'
                f'Sign in with {name_capitalized}. Please use an alternative login method.',
                category="danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=False)
        # for OAuth log in, this is the only place for the user to turn on Remember Me
        flash(f"You have logged in with {name_capitalized}. " +
              Markup(f'<a href={url_for("auth.remember")}>Click here</a>') + " to turn on Remember Me.",
              category="success")
        return redirect(url_for("main.index"))

    auth.add_url_rule(f"/{oauth_provider.name}",
                      endpoint=oauth_provider.name,
                      view_func=entry)
    auth.add_url_rule(f"/{oauth_provider.name}/callback",
                      endpoint=callback_endpoint,
                      view_func=callback,
                      methods=callback_methods)


make_oauth_routes(oauth.google)

make_oauth_routes(oauth.apple, callback_methods=["POST"])
