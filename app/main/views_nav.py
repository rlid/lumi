from flask import render_template, redirect, flash, Markup, url_for, session, request
from flask_login import login_required, current_user

from app import db
from app.auth.forms import LogInForm, SignUpForm
from app.main import main
from app.main.forms import FeedbackForm
from app.models import Feedback
from utils.email import send_email


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
    redirect_url = request.referrer
    if redirect_url is None or not redirect_url.startswith(request.root_url):
        redirect(url_for('main.index'))
    return redirect(redirect_url)


@main.route('/reset_cookie')
def reset_cookie():
    session.pop('allow_cookie', None)
    return redirect(url_for('main.index'))


@main.route('/whatsapp')
def whatsapp():
    return redirect('https://api.whatsapp.com/send?phone=+447774523701', code=302)


@main.route('/faq')
@login_required
def faq():
    return render_template('docs/faq.html', title='FAQs')


@main.route('/faq/<anchor_id>')
@login_required
def faq_anchor(anchor_id):
    return render_template('docs/faq.html', title='FAQs', anchor_id=anchor_id)


@main.route('/privacy')
def privacy():
    return render_template('docs/privacy.html', title='Privacy Policy')


@main.route('/cookie')
def cookie():
    return render_template('docs/cookie.html', title='Cookie Policy')


@main.route('/terms')
@login_required
def terms():
    return render_template('docs/terms.html', title='Terms & Conditions')


@main.route('/feedback')
def feedback():
    form = FeedbackForm()
    return render_template('contact.html', title="Questions & Feedback", form=form)


@main.route('/whatsnew')
def whatsnew():
    return render_template('whatsnew.html', title="What's New")


@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = FeedbackForm()
    if form.validate_on_submit():
        fb = Feedback(
            type='feedback',
            text=form.text.data,
            email=form.email.data or (current_user.email if current_user.is_authenticated else None))
        db.session.add(fb)
        db.session.commit()
        send_email(
            sender='feedback@lumiask.com',
            recipient='support@lumiask.com',
            subject='Feedback received',
            body_text=f'{fb.email}\n{fb.text}'
        )
        flash('Thank you so much for your feedback!', category='success')
        redirect_url = request.referrer
        if redirect_url and redirect_url.startswith(request.root_url):
            return redirect(redirect_url)
        else:
            return redirect('main.contact')

    return render_template('contact.html', title="Contact Us", form=form)


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
