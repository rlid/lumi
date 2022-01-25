from flask import render_template, redirect, request, url_for, flash, Markup, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db, oauth
from app.auth import auth
from app.models import User, InviteCode
from app.auth.forms import LogInForm, SignUpForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm
from config import Config
from utils import security_utils


@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.email_verified \
            and request.blueprint != 'auth' \
            and request.endpoint != 'static':
        flash('Your access is restricted because your email address is not verified. ' +
              Markup(f'<a href={url_for("auth.resend_confirmation")}>Click here</a> ') +
              'to request another confirmation email.', category='warning')


# intended user: is_authenticated no | signup_method email | email_verified all
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You have already logged in.', category='warning')
        return redirect(url_for('main.index'))

    form = LogInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None:
            if user.signup_method == "email":
                if user.verify_password(form.password.data):
                    login_user(user, form.remember_me.data)
                    next_url = request.args.get('next')
                    if next_url is None or not next_url.startswith('/') or '/auth/' in next_url:
                        next_url = url_for('main.index')
                    return redirect(next_url)
                flash('Invalid username or password', category='danger')
            else:
                flash(f'The account associated with {form.email.data} does not support login via email and password. '
                      'Please use an alternative login method.',
                      category='danger')
        else:
            flash('Invalid username or password', category='danger')
    return render_template('auth/login.html', form=form)


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
    flash('You have been logged out on all devices.', category='success')
    return redirect(url_for('main.index'))


# intended user: all | signup_method all | email_verified all
@auth.route('/invite')
def invite():
    codes = [code for code, in db.session.query(InviteCode.code).all()]
    invite_code = InviteCode()
    while invite_code.code in codes:
        invite_code = InviteCode()
    db.session.add(invite_code)
    db.session.commit()
    return redirect(url_for("auth.signup", code=invite_code.code))


# intended user: is_authenticated no | signup_method email | email_verified n/a
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        flash("You have already signed up.", category="warning")
        return redirect(url_for("main.index"))

    form = SignUpForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(), password=form.password.data, signup_method='email')
        db.session.add(user)
        invite_code = InviteCode.query.filter_by(code=form.invite_code.data).first()
        db.session.delete(invite_code)
        db.session.commit()
        session.pop("invite_code")
        token = user.generate_token(action="confirm")
        print(url_for("auth.confirm", token=token, remember=1, _external=True))
        flash(f'A confirmation email has been sent to {form.email.data}.', category="info")
        login_user(user, remember=False)
        return redirect(url_for("main.index"))

    code = request.args.get('code')
    if code is not None:
        invite_code, error_message = InviteCode.validate(code=code)
        if invite_code is None:
            flash(error_message, category="danger")
            return redirect(url_for("auth.signup"))
        session["invite_code"] = code
        form.invite_code.data = code
        form.invite_code.render_kw = {'readonly': ''}

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
        db.session.commit()
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
    print(url_for("auth.confirm", token=token, _external=True))
    flash(f'A new confirmation email has been sent to {current_user.email}.', category="info")
    return redirect(url_for("main.index"))


# intended user: is_authenticated yes | signup_method email | email_verified n/a
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if current_user.signup_method != "email":
        flash(f"You cannot change password because your account does not support login via email and password.",
              category='danger')
        return redirect(url_for("main.index"))

    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
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

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user:
            if user.signup_method != "email":
                flash(f"Your account does not support password reset. Please use an alternative login method.",
                      category='danger')
                return redirect(url_for("auth.login"))
            # add client_nonce for extra safety - the nonce is stored as a cookie on the client side, which means
            # that if the login link is opened in a different browser environment (e.g. on a different PC / phone),
            # it will be invalid as the cookie does not exist, and only the hashed nonce is included in the token
            # for security reasons:
            client_nonce = security_utils.random_urlsafe(nbytes=Config.CLIENT_NONCE_NBYTES)
            session['client_nonce'] = client_nonce
            token = user.generate_token(
                action="reset",
                client_nonce_hash=security_utils.hash_string(client_nonce,
                                                             digest_size=Config.CLIENT_NONCE_HASH_DIGEST_SIZE))
            print(f"client_nonce is set to [{client_nonce}].")
            print(url_for("auth.password_reset", token=token, _external=True))
            flash(f'An email with instructions to reset your password has been sent to {form.email.data}.',
                  category='info')
            return redirect(url_for('main.index'))
        flash(f'{form.email.data} is not associated with any account in our system.', category='danger')
    return render_template('auth/reset_password.html', form=form)


# intended user: is_authenticated no | signup_method email | email_verified n/a
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if current_user.is_authenticated:
        flash("You have already logged in. Please log out first to initiate password reset.", category="warning")
        return redirect(url_for('main.index'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        client_nonce_hash = session.get('client_nonce')
        # client_nonce_hash is just client_nonce at this point, hash it if it is not None:
        if client_nonce_hash is not None:
            client_nonce_hash = security_utils.hash_string(client_nonce_hash,
                                                           digest_size=Config.CLIENT_NONCE_HASH_DIGEST_SIZE)
        token_data = User.decode_token(token)
        token_user = User.query.get(int(token_data.get("reset")))
        if token_user.verify_token_data(token_data, action="reset", client_nonce_hash=client_nonce_hash):
            token_user.password = form.password.data
            db.session.add(token_user)
            db.session.commit()
            flash('Your password has been updated.', category='success')
            if client_nonce_hash is not None and client_nonce_hash == token_data.get("client_nonce_hash"):
                print(f"client_nonce [{session.get('client_nonce')}] is deleted.")
                session.pop('client_nonce')
            login_user(token_user, remember=False)
        return redirect(url_for('main.index'))
    return render_template('auth/change_password.html', form=form)


def make_oauth_routes(oauth_provider, callback_methods=["GET"]):
    name_capitalized = oauth_provider.name.capitalize()
    callback_endpoint = f"{oauth_provider.name}_callback"

    # intended user: is_authenticated no | signup_method oauth | email_verified n/a
    def entry():
        if current_user.is_authenticated:
            flash('You have already logged in.', category='warning')
            return redirect(url_for("main.index"))

        redirect_uri = url_for(f"auth.{callback_endpoint}", _external=True)
        response = oauth_provider.authorize_redirect(redirect_uri)
        print(f"response.response = {response.response}")
        return response

    # intended user: is_authenticated no | signup_method email | email_verified n/a
    def callback():
        token = oauth_provider.authorize_access_token()
        print(f"token = {token}")
        userinfo = token.get("userinfo")
        print(f"userinfo = {userinfo}")

        if userinfo and userinfo.get("email_verified"):
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
                invite_code, error_message = InviteCode.validate(code=session.get("invite_code"))
                if invite_code is None:
                    flash(error_message, category="danger")
                    return redirect(url_for("auth.signup"))
                user = User(email=email, email_verified=True, signup_method=oauth_provider.name)
                db.session.add(user)
                db.session.delete(invite_code)
                db.session.commit()
                session.pop("invite_code")
                login_user(user, remember=False)
                flash(f"You have signed up with {name_capitalized}.", category="success")
            else:
                if user.signup_method == oauth_provider.name:
                    login_user(user, remember=False)
                    flash(f"You have logged in with {name_capitalized}.", category="success")
                else:
                    flash(
                        f'The account associated with {userinfo["email"]} does not support Sign in with {name_capitalized}. '
                        'Please use an alternative login method.',
                        category="danger")
                    return redirect(url_for("auth.login"))
        else:
            flash(f"Your {name_capitalized} account does not have a verified email address.", category="danger")
            if session.get("invite_code"):
                return redirect(url_for("auth.signup", code=session.get("invite_code")))
            else:
                return redirect(url_for("auth.signup"))
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
