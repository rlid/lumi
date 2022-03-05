from flask import render_template, redirect, flash, Markup, url_for, session, request
from flask_login import login_required, current_user

from app.auth.forms import LogInForm, SignUpForm
from app.main import main


@main.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.email_verified \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static' \
                and request.endpoint != 'main.index' \
                and request.endpoint != 'main.browse' \
                and request.endpoint != 'main.account':
            flash('Your access is restricted because your email address is not verified. ' +
                  Markup(f'<a href={url_for("auth.resend_confirmation")}>Click here</a> ') +
                  'to request another confirmation email.', category='warning')
            return redirect(url_for('main.browse'))


@main.route('/')
def index():
    login_form = LogInForm()
    signup_form = SignUpForm()
    return render_template('landing.html', login_form=login_form, signup_form=signup_form)


@main.route('/csp-report', methods=['POST'])
def csp_report():
    return '', 200


@main.route('/allow_cookie/<int:choice>')
def allow_cookie(choice):
    session['allow_cookie'] = choice == 1
    return redirect(request.referrer)


@main.route('/reset_cookie')
def reset_cookie():
    session.pop('allow_cookie', None)
    return redirect(url_for('main.index'))


@main.route('/whatsapp')
def whatsapp():
    return redirect('https://api.whatsapp.com/send?phone=+447774523701', code=302)


@main.route('/how-it-works')
def how_it_works():
    return render_template('landing.html', title='How It Works')


@main.route('/privacy')
def privacy():
    return render_template('docs/privacy.html', title='Privacy Policy')


@main.route('/cookie')
def cookie():
    return render_template('docs/cookie.html', title='Cookie Policy')


@main.route('/engagements')
@login_required
def engagements():
    return render_template('landing.html', title='Active Engagements')


@main.route('/saved')
@login_required
def saved():
    return render_template('landing.html', title='Saved')


@main.route('/guidelines')
def guidelines():
    return render_template('landing.html', title='Community Guidelines')


@main.route('/about')
def about():
    return render_template('docs/about.html')
